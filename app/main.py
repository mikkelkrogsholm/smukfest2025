import os
import sys
from datetime import datetime, timezone, timedelta, time
import locale # Import locale module
import logging # Add logging import

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, Depends, Form, HTTPException, status, Response, Path, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from dateutil import parser # Added for date parsing
from typing import Optional, List

# Import SQLAlchemy Session for dependency injection
from sqlalchemy.orm import Session

# Import database and auth functions
from app import database, models, schemas, crud # Ensure all necessary modules are imported
from app.auth import ( # Import specific auth functions and dependencies
    create_access_token, 
    authenticate_user, 
    get_current_active_user, # ADD THIS BACK - Keep this dependency
    get_current_user_from_cookie, # Import for checks
    set_auth_cookie,
    delete_auth_cookie,
    ACCESS_TOKEN_EXPIRE_MINUTES
    # RoleChecker removed from this import
)
from app.users import User # Specifically import the User model for type hinting
from app.utils import format_datetime, datetime_now # Import utils
from app.database import SessionLocal, engine, create_db_tables # Import engine and table creation function

# --- Scheduler Imports & Setup ---
from apscheduler.schedulers.background import BackgroundScheduler
from scripts.sync_artists_db import run_sync as run_hourly_sync # Rename import to avoid clash if needed
import atexit # To ensure scheduler shutdown
# --- End Scheduler Setup ---

# --- Set Locale for Danish Weekday Names ---
try:
    # Sæt locale specifikt for tidsformatering til dansk
    locale.setlocale(locale.LC_TIME, 'da_DK.UTF-8')
    print("Locale for LC_TIME set to da_DK.UTF-8") # Til debugging
except locale.Error as e:
    print(f"Warning: Could not set locale to da_DK.UTF-8: {e}")
    # Overvej fallback eller yderligere fejlhåndtering her
# --- End Locale Setting ---

# Determine the base directory of the app
# This assumes main.py is in the app directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Create DB Tables on Startup (Optional) ---
# Uncomment the line below if you want tables to be created automatically
# when the application starts, based on your models.py definitions.
# Be cautious using this in production if you manage migrations separately.
# create_db_tables() # Commented out - Initialization moved to setup script

app = FastAPI(title="Smukfest Risk Tool")

# CORS Middleware (allow all for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods
    allow_headers=["*"], # Allow all headers
)

# Mount static files (like CSS if not using CDN)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# --- Custom Jinja2 Filter for Date Formatting --- 
# Removed definition from here, it's now in utils.py
# def format_datetime(value: str, format_str: str = "%a, %d %b %H:%M") -> str:
#     """Parses ISO string and formats it nicely."""
#     # ... function body removed ...

# Register the filter with Jinja2 environment (import from utils)
templates.env.filters['datetimeformat'] = format_datetime

# Add festival-aware datetime formatting filter
def datetimeformat_festival(value, format_str="%A %H:%M, %d/%m-%Y"):
    """Festival-aware datetime formatting that handles festival days correctly"""
    return format_datetime(value, format_str, use_festival_day=True)

templates.env.filters['datetimeformat_festival'] = datetimeformat_festival
templates.env.globals['now'] = datetime_now # Make now() available (import from utils)
# --- End Custom Filter ---

# --- Dependency for Authentication (REMOVED - Now imported from app/auth.py) ---
# async def get_current_active_user(request: Request) -> User: # Return User object or raise exception
#     """ Dependency that checks the cookie and returns the User object or redirects."""
#     user = auth.get_current_user_from_cookie(request)
#     if user is None:
#         # Store the originally requested path to redirect back after login
#         # Handle potential query params in original request url path
#         original_path = request.url.path
#         query_string = request.url.query
#         next_param = f"?next={original_path}" if not query_string else f"?next={original_path}?{query_string}"
#         # Basic url encoding might be needed for complex paths, but keep simple for now
#         redirect_url = f"/login{next_param}"
#         
#         raise HTTPException(
#             status_code=status.HTTP_307_TEMPORARY_REDIRECT,
#             detail="Not authenticated",
#             headers={"Location": redirect_url}
#         )
#     return user 

# --- Dependency for Admin-Only Access --- 
async def get_admin_user(current_user: models.User = Depends(get_current_active_user)) -> models.User:
    """ Dependency that ensures the logged-in user has the 'admin' role."""
    # Assuming UserRoleEnum is defined in models.py now
    if current_user.role != models.UserRoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Operation not permitted. Administrator access required."
        )
    return current_user

# --- Dependency for Database Session ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Routes --- 

@app.get("/login", response_class=HTMLResponse, tags=["Authentication"])
async def login_form(request: Request, error: Optional[str] = None, next: Optional[str] = None):
    """ Displays the login page. Includes error message if login failed."""
    # Check if user is already logged in, redirect to root if so
    if get_current_user_from_cookie(request):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("login.html", {"request": request, "error": error, "next_url": next})

@app.post("/login", tags=["Authentication"])
async def login_for_access_token(
    response: Response, # Inject Response object to set cookie
    request: Request, # Inject Request object to render template on failure
    db: Session = Depends(get_db), # Need DB session for authenticate_user
    username: str = Form(...),
    password: str = Form(...),
    next_url: Optional[str] = Form(None) # Capture potential 'next' param from form first
):
    # If next_url wasn't in the form, try getting it from query params
    if not next_url:
        query_params = request.query_params
        next_url = query_params.get('next')
    
    # Use the imported authenticate_user which should now use db
    user = authenticate_user(db, username, password)
    if not user:
        # Re-render login form with error
        return templates.TemplateResponse(
            "login.html", 
            {
                "request": request, 
                "error": "Incorrect username or password",
                "next_url": next_url # Pass back for hidden field
            },
            status_code=status.HTTP_401_UNAUTHORIZED # Use 401 for failed login attempt
        )
    
    # Create JWT including the user's role (use user.role.value for the enum)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value}, # Pass role value
        expires_delta=access_token_expires
    )
    
    # Set cookie in the response before returning it
    set_auth_cookie(response, access_token)
    
    # Redirect to the originally requested page or root
    redirect_target = next_url or "/" 
    # Use standard 303 See Other for redirect after successful POST
    # Setting headers directly on RedirectResponse is preferred
    return RedirectResponse(url=redirect_target, status_code=status.HTTP_303_SEE_OTHER, headers=response.headers)

@app.get("/logout", tags=["Authentication"])
async def logout_and_redirect():
    """ Clears the auth cookie and redirects to login page. """
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    delete_auth_cookie(response)
    return response

# --- Protected Main Route --- 
@app.get("/", response_class=HTMLResponse)
def read_root(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """ Fetches artists, events, and assessments, renders the main overview page. Requires login."""
    print(f"User '{current_user.username}' (Role: {current_user.role.value}) accessing root route...")
    events = crud.get_all_events_with_artists_stages(db, limit=500)
    assessments = crud.get_all_risk_assessments_dict(db)
    all_artists = crud.get_all_artists(db, limit=500)
    
    # --- Logic to prepare data for template --- 
    # (This logic might need adjustment based on how templates use the data)
    artist_events_map = {artist.slug: [] for artist in all_artists}
    for event in events:
        # Access related artist via ORM relationship if needed and available
        # Assuming events from get_all_events_with_artists_stages have artist loaded
        if event.artist and event.artist.slug in artist_events_map:
            artist_events_map[event.artist.slug].append(event)
        elif event.artist_slug in artist_events_map:
             artist_events_map[event.artist_slug].append(event)
        else:
             # Handle cases where event might not have artist linked correctly
             print(f"Warning: Event {event.id} artist slug '{event.artist_slug}' not found in artist map or event.artist is None.")
    
    # Create a combined list for the template
    artist_card_data = []
    for artist in all_artists:
        artist_card_data.append({
            'artist': artist, # Pass the ORM Artist object
            'events': artist_events_map.get(artist.slug, []) # Pass list of ORM Event objects
        })
        
    # Sort artist cards alphabetically by artist title
    artist_card_data.sort(key=lambda x: x['artist'].title)
    # --- End template data preparation --- 

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "artists": all_artists, # Pass artists directly for filtering/card generation
            "events": events, # Pass events directly for table/filtering
            "assessments": assessments, # Pass assessments dict keyed by slug
            "current_user_role": current_user.role.value, # Pass role value
            "current_user": current_user.username # ADDED: Pass username for base template
        }
    )

# Old basic root (can be removed or kept for API check)
@app.get("/api-status")
def api_status():
    return {"message": "Welcome to the Smukfest Artist Risk Assessment Tool API"}

# --- Add other protected routes below using Depends(get_current_active_user) --- 
# Example:
# @app.get("/some_other_page")
# def read_other_page(request: Request, current_user: str = Depends(get_current_active_user)):
#     return templates.TemplateResponse("other_page.html", {"request": request, "current_user": current_user})

# Placeholder for future routes or includes
# Example: from .routers import artists
# app.include_router(artists.router) 

# --- Admin Routes --- 

@app.get("/admin/assessments", response_class=HTMLResponse, tags=["Admin"])
async def read_assessments_page(
    request: Request, 
    db: Session = Depends(get_db), # Need DB session
    admin_user: models.User = Depends(get_admin_user) # Protects route, provides admin user object
):
    """ Serves the HTML page for viewing and editing risk assessments. Admin only."""
    print(f"Admin user '{admin_user.username}' accessing assessments page...")
    # Fetch artists and their assessments using CRUD functions
    # Use get_all_assessments_with_artists to get assessments with artist loaded
    assessments_with_artists = crud.get_all_assessments_with_artists(db, limit=500)
    # Fetch all artists separately in case some don't have assessments yet
    all_artists = crud.get_all_artists(db, limit=500)
    
    # Create a dictionary of assessments keyed by artist slug for quick lookup
    assessments_dict = {a.artist_slug: a for a in assessments_with_artists}
    
    # Prepare data for the template: list of dicts containing artist and their assessment (or None)
    artists_assessments_data = []
    for artist in all_artists:
        artists_assessments_data.append({
            "artist": artist, # Pass ORM Artist object
            "assessment": assessments_dict.get(artist.slug) # Pass ORM RiskAssessment or None
        })

    # Sort by artist title
    artists_assessments_data.sort(key=lambda x: x['artist'].title)

    return templates.TemplateResponse(
        "admin_assessments.html", 
        {
            "request": request, 
            "current_user": admin_user.username, # For base template display
            "current_user_role": admin_user.role.value, # Pass role value
            "artists_assessments": artists_assessments_data # Pass combined data
        }
    )

@app.post("/api/assessments/{artist_slug}", response_model=schemas.RiskAssessment, tags=["Admin API"])
async def save_artist_assessment(
    artist_slug: str,
    assessment_data: schemas.RiskAssessmentCreate, # Use the Create schema
    db: Session = Depends(get_db), # Need DB session
    admin_user: models.User = Depends(get_admin_user) # Protects route
):
    """ API endpoint to create or update a risk assessment for an artist. Admin only."""
    print(f"Admin user '{admin_user.username}' saving assessment for {artist_slug}...")
    # Check if artist actually exists using CRUD function
    artist = crud.get_artist_by_slug(db, artist_slug=artist_slug)
    if not artist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Artist with slug '{artist_slug}' not found")

    # Use the upsert CRUD function
    try:
        updated_assessment = crud.upsert_assessment(db, artist_slug, assessment_data)
        return updated_assessment # crud function returns the ORM model, FastAPI converts based on response_model
    except Exception as e:
        # Catch potential errors during upsert (e.g., DB constraints)
        print(f"Error upserting assessment for {artist_slug}: {e}")
        # Rollback might be needed if crud function doesn't handle it
        # db.rollback() # Depends on crud implementation
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save assessment: {e}")

# Artist Detail Page Route
@app.get("/artists/{artist_slug}", response_class=HTMLResponse)
def read_artist_detail(
    request: Request,
    artist_slug: str = Path(..., title="The slug of the artist to retrieve"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Use the specific CRUD function for detail view (loads relationships)
    artist_detail = crud.get_artist_detail_by_slug(db, artist_slug=artist_slug)
    if not artist_detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artist not found")

    # Events are already loaded by get_artist_detail_by_slug
    # Sort events by start time if needed (already done in crud? check)
    artist_events = sorted(artist_detail.events, key=lambda e: e.start_time)

    return templates.TemplateResponse(
        "artist_detail.html",
        {
            "request": request,
            "artist": artist_detail, # Pass the ORM object with loaded relations
            "assessment": artist_detail.assessment, # Access loaded assessment
            "events": artist_events, # Pass sorted loaded events
            "current_user_role": current_user.role.value, # Use .value for enum
            "current_user": current_user.username # ADDED: Pass username for base template
        }
    )

# --- Placeholder for API documentation or health check --- 
# ... (rest of the file) ... 

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Scheduler Definition & Job ---
scheduler = BackgroundScheduler(daemon=True, timezone="Europe/Copenhagen") # Set timezone

def hourly_sync_job():
    """Job function to run the hourly sync."""
    try:
        logger.info("APScheduler: Starting hourly artist sync job...")
        run_hourly_sync() # Call the imported sync function
        logger.info("APScheduler: Hourly artist sync job finished successfully.")
    except Exception as e:
        logger.error(f"APScheduler: Error during hourly sync job: {e}", exc_info=True)

# --- FastAPI Event Handlers for Scheduler ---
@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI startup: Initializing scheduler...")
    try:
        # Add the job to run every hour
        scheduler.add_job(
            hourly_sync_job, 
            'interval', 
            hours=1, 
            id='hourly_artist_sync',
            replace_existing=True,
            misfire_grace_time=600 # Allow 10 minutes grace period
        )
        scheduler.start()
        logger.info("APScheduler started and job added.")
        
        # Optional: Run the job once immediately on startup
        # logger.info("Running initial sync on startup...")
        # hourly_sync_job() 
        
    except Exception as e:
        logger.error(f"Error starting APScheduler: {e}", exc_info=True)

@app.on_event("shutdown")
def shutdown_event():
    logger.info("FastAPI shutdown: Shutting down APScheduler...")
    try:
        scheduler.shutdown()
        logger.info("APScheduler shut down successfully.")
    except Exception as e:
        logger.error(f"Error shutting down APScheduler: {e}", exc_info=True)

# Alternative using atexit (provides an extra layer of safety for shutdown)
# def shutdown_scheduler_on_exit():
#     if scheduler.running:
#         logger.info("atexit: Shutting down APScheduler...")
#         scheduler.shutdown()
# atexit.register(shutdown_scheduler_on_exit)
# --- End Scheduler Logic --- 

@app.get("/calendar", response_class=HTMLResponse)
def calendar_view(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    selected_date: Optional[str] = Query(None, alias="date")
):
    """Renders a calendar grid with stages as columns and 15-min increments as rows."""
    import datetime
    from datetime import time, timedelta
    from collections import defaultdict

    # Determine the date to show
    if selected_date:
        try:
            target_date = datetime.datetime.strptime(selected_date, "%Y-%m-%d")
        except Exception:
            target_date = datetime.datetime.now()
    else:
        target_date = datetime.datetime.now()

    # Fetch all stages
    stages = [stage for stage in crud.get_all_stages(db) if stage.name != 'TBA']
    SHORT_NAMES = {
        'Bøgescenerne': 'Bøge',
        'Stjernescenen': 'Stjerne',
        'Månescenen': 'Månen',
        'The Hood': 'Hood',
    }
    stage_dicts = []
    for stage in stages:
        stage_dicts.append({
            "name": stage.name,
            "short_name": SHORT_NAMES.get(stage.name, stage.name)
        })
    stage_names = [stage["name"] for stage in stage_dicts]

    # Fetch all events for the selected festival day
    events = crud.get_events_for_festival_day(db, target_date)
    # Fetch all risk assessments as a dict keyed by artist_slug
    assessments = crud.get_all_risk_assessments_dict(db)
    # Generate 15-min time slots for the day (08:00 to 03:00 next day)
    start_time = datetime.datetime.combine(target_date.date(), time(8, 0))
    end_time = start_time + timedelta(hours=19)

    # If there are events, trim the time range to first/last event
    if events:
        def round_down(dt):
            return dt - timedelta(minutes=dt.minute % 15, seconds=dt.second, microseconds=dt.microsecond)
        def round_up(dt):
            add = (15 - (dt.minute % 15)) % 15
            if add == 0 and (dt.second > 0 or dt.microsecond > 0):
                add = 15
            return (dt + timedelta(minutes=add)).replace(second=0, microsecond=0)
        first_event_start = min(e.start_time for e in events if e.start_time)
        last_event_end = max((e.end_time or (e.start_time + timedelta(hours=1))) for e in events if e.start_time)
        start_time = round_down(first_event_start)
        end_time = round_up(last_event_end)

    time_slots = []
    t = start_time
    while t <= end_time:
        time_slots.append(t)
        t += timedelta(minutes=15)

    # Build grid: events_by_stage_and_time[stage][slot] = {event_data, span} or placeholder
    events_by_stage_and_time = {stage: {} for stage in stage_names}
    event_id_to_event = {}
    for event in events:
        if not event.stage:
            continue
        stage = event.stage.name
        event_id_to_event[event.event_id] = event
        # Find the slot index for the event's start_time
        slot_idx = None
        for idx, slot in enumerate(time_slots):
            if slot <= event.start_time < slot + timedelta(minutes=15):
                slot_idx = idx
                break
        if slot_idx is None:
            continue  # Event not in visible range
        # Set span to 4 (1 hour)
        span = 4
        # Mark the main slot
        events_by_stage_and_time[stage][time_slots[slot_idx]] = {"event_data": event, "span": span}
        # Mark covered slots
        for i in range(1, span):
            if slot_idx + i < len(time_slots):
                events_by_stage_and_time[stage][time_slots[slot_idx + i]] = {"covered_by_event_id": event.event_id, "is_empty_placeholder": True}

    # Pass all events as JSON for modal
    from app.schemas import Event as EventSchema
    import json as _json
    def event_to_dict(ev):
        # Look up risk assessment for the artist
        risk_level = None
        intensity_level = None
        density_level = None
        artist_description = None # Initialize artist_description
        remarks = None
        crowd_profile = None
        notes = None

        if ev.artist and ev.artist.slug:
            assessment = assessments.get(ev.artist.slug)
            if assessment:
                risk_level = assessment.risk_level
                intensity_level = assessment.intensity_level
                density_level = assessment.density_level
                remarks = assessment.remarks
                crowd_profile = assessment.crowd_profile
                notes = assessment.notes
            # Get artist description
            artist_description = ev.artist.description # Access description from the related artist object
        
        return {
            "event_id": ev.event_id,
            "artist": {"title": ev.artist.title if ev.artist else None, "slug": ev.artist.slug if ev.artist else None},
            "stage": {"name": ev.stage.name if ev.stage else None},
            "start_time": ev.start_time.isoformat() if ev.start_time else None,
            "end_time": ev.end_time.isoformat() if ev.end_time else None,
            "risk_level": risk_level,
            "intensity_level": intensity_level,
            "density_level": density_level,
            "description": artist_description, # Add the artist's description here
            "remarks": remarks,
            "crowd_profile": crowd_profile,
            "notes": notes
        }
    all_events_raw = [event_to_dict(ev) for ev in events]

    return templates.TemplateResponse(
        "calendar_view_custom.html",
        {
            "request": request,
            "stages": stage_dicts,
            "stage_names": stage_names,
            "time_slots": [slot.isoformat() for slot in time_slots],
            "events_by_stage_and_time": events_by_stage_and_time,
            "all_events_raw": all_events_raw,
            "selected_date": target_date.strftime("%Y-%m-%d"),
            "current_user": current_user.username,
            "current_user_role": current_user.role.value,
        }
    )

@app.get("/calendar/print", response_class=HTMLResponse)
def calendar_print_view(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    selected_date: Optional[str] = Query(None, alias="date")
):
    """Renders a beautiful SVG-based print calendar."""
    import datetime
    from datetime import time, timedelta
    
    # Determine the date to show
    if selected_date:
        try:
            target_date = datetime.datetime.strptime(selected_date, "%Y-%m-%d")
        except Exception:
            target_date = datetime.datetime.now()
    else:
        target_date = datetime.datetime.now()

    # Fetch all stages (exclude TBA)
    stages = [stage for stage in crud.get_all_stages(db) if stage.name != 'TBA']
    SHORT_NAMES = {
        'Bøgescenerne': 'Bøge',
        'Stjernescenen': 'Stjerne',
        'Månescenen': 'Månen',
        'The Hood': 'Hood',
    }
    
    # Fetch all events for the selected festival day
    events = crud.get_events_for_festival_day(db, target_date)
    assessments = crud.get_all_risk_assessments_dict(db)

    # Calculate time bounds
    if events:
        event_starts = [e.start_time for e in events if e.start_time]
        event_ends = [(e.end_time or (e.start_time + timedelta(hours=1))) for e in events if e.start_time]
        
        if not event_starts or not event_ends: # Handle case with no valid event times
            start_time = datetime.datetime.combine(target_date.date(), time(12, 0)) # Default start
            end_time = datetime.datetime.combine(target_date.date(), time(23, 59))   # Default end
        else:
            actual_start = min(event_starts)
            actual_end = max(event_ends)
            
            # Round to hour boundaries
            start_time = actual_start.replace(minute=0, second=0, microsecond=0)
            end_time = actual_end.replace(minute=0, second=0, microsecond=0)
            if actual_end.minute > 0 or actual_end.second > 0 or actual_end.microsecond > 0 :
                end_time += timedelta(hours=1)
            if end_time <= start_time: # Ensure end_time is after start_time
                end_time = start_time + timedelta(hours=1)


    else: # No events, set a default time range
        start_time = datetime.datetime.combine(target_date.date(), time(12, 0)) # Default start 12:00
        end_time = datetime.datetime.combine(target_date.date() + timedelta(days=1), time(2, 0)) # Default end 02:00 next day


    # Generate SVG
    def generate_svg_calendar():
        # SVG dimensions - Further Adjusted for better A4 fit
        svg_width = 1080 # Reduced from 1100
        svg_height = 765 # Reduced from 780
        
        # Margins for layout - Further Adjusted
        margin_top = 55      # Reduced from 60
        margin_bottom = 45   # Reduced from 50 
        margin_left = 55     # Reduced from 60
        margin_right = 20    # Reduced from 25
        
        # Grid dimensions (where events are plotted)
        grid_x_start = margin_left
        grid_y_start = margin_top
        grid_width = svg_width - margin_left - margin_right
        grid_height = svg_height - margin_top - margin_bottom
        
        num_stages = len(stages)
        stage_column_width = grid_width / num_stages if num_stages > 0 else grid_width
        
        # Time calculations for vertical axis
        if end_time <= start_time:
            total_minutes = 60 
        else:
            total_minutes = (end_time - start_time).total_seconds() / 60
        
        if total_minutes == 0: total_minutes = 1
        height_per_minute = grid_height / total_minutes
        
        colors = {
            'riskHigh': '#ef4444',
            'riskMedium': '#fbbf24',
            'riskLow': '#10b981',
            'riskUnknown': '#6b7280',
            'stageBg': '#f9fafb',
            'textWhite': '#FFFFFF',
            'textMediumRisk': '#854d0e',
            'textDark': '#1f2937',
            'textLight': '#6b7280',
            'borderLight': '#e5e7eb',
            'borderMedium': '#cbd5e0'
        }

        svg_parts = [f'''<svg viewBox="0 0 {svg_width} {svg_height}" xmlns="http://www.w3.org/2000/svg" style="font-family: Arial, sans-serif;">
<defs>
  <!-- Defs section is intentionally empty for simplified style -->
</defs>''']

        svg_parts.append(f'<rect width="{svg_width}" height="{svg_height}" fill="{colors["textWhite"]}"/>')
        
        date_str = target_date.strftime("%d. %B %Y")
        svg_parts.append(f'''<text x="{svg_width/2}" y="28" text-anchor="middle" font-size="20" font-weight="bold" fill="{colors["textDark"]}">Smukfest Program: {date_str}</text>''') # Y reduced, font size reduced
        
        for i, stage in enumerate(stages):
            x_stage = grid_x_start + i * stage_column_width
            stage_name = SHORT_NAMES.get(stage.name, stage.name)
            svg_parts.append(f'<rect x="{x_stage}" y="{grid_y_start}" width="{stage_column_width}" height="{grid_height}" fill="{colors["stageBg"]}" stroke="{colors["borderLight"]}" stroke-width="0.4"/>') # Thinner stroke
            svg_parts.append(f'''<text x="{x_stage + stage_column_width/2}" y="{grid_y_start - 10}" text-anchor="middle" font-size="12" font-weight="bold" fill="{colors["textDark"]}">{stage_name}</text>''') # Y reduced, font size reduced

        current_t = start_time
        while current_t <= end_time:
            minutes_from_start_grid = (current_t - start_time).total_seconds() / 60
            y_pos = grid_y_start + minutes_from_start_grid * height_per_minute
            is_hour = current_t.minute == 0
            line_opacity = "0.5" if is_hour else "0.2"
            line_stroke_width = "0.5" if is_hour else "0.3"
            svg_parts.append(f'<line x1="{grid_x_start}" y1="{y_pos}" x2="{grid_x_start + grid_width}" y2="{y_pos}" stroke="{colors["borderMedium"]}" stroke-width="{line_stroke_width}" opacity="{line_opacity}"/>')
            if is_hour:
                time_str = current_t.strftime("%H:%M")
                svg_parts.append(f'''<text x="{grid_x_start - 7}" y="{y_pos + 3}" text-anchor="end" font-size="9" font-weight="medium" fill="{colors["textLight"]}">{time_str}</text>''') # X reduced, font size reduced
            current_t += timedelta(minutes=30) 

        for event in events:
            if not event.stage or not event.start_time or event.stage.name == 'TBA': continue
            stage_index = -1
            for i, s in enumerate(stages):
                if s.name == event.stage.name: stage_index = i; break
            if stage_index == -1: continue

            event_start_dt = event.start_time
            event_end_dt = event.end_time or (event_start_dt + timedelta(hours=1))
            event_start_dt_clipped = max(event_start_dt, start_time)
            event_end_dt_clipped = min(event_end_dt, end_time)
            if event_end_dt_clipped <= event_start_dt_clipped: continue

            minutes_from_start_event = (event_start_dt_clipped - start_time).total_seconds() / 60
            duration_minutes_event = (event_end_dt_clipped - event_start_dt_clipped).total_seconds() / 60
            if duration_minutes_event <= 0: continue

            event_x = grid_x_start + stage_index * stage_column_width + 1.5 # Padding reduced
            event_width_px = stage_column_width - 3      # Padding reduced
            event_y = grid_y_start + minutes_from_start_event * height_per_minute
            event_height_px = duration_minutes_event * height_per_minute
            event_height_px = max(event_height_px, 2) # Min height reduced

            risk_level = 'unknown'
            if event.artist and event.artist.slug:
                assessment = assessments.get(event.artist.slug)
                if assessment and assessment.risk_level: risk_level = assessment.risk_level.lower()
            
            risk_level_title = risk_level.title()
            risk_color_key = f'risk{risk_level_title}'
            event_fill_color = colors.get(risk_color_key, colors['riskUnknown'])
            text_color = colors['textWhite'] if risk_level != "medium" else colors['textMediumRisk']
            
            artist_name = event.artist.title if event.artist else 'Ukendt'
            start_time_str = event_start_dt.strftime("%H:%M")
            end_time_str = event_end_dt.strftime("%H:%M")
            
            font_size_artist = 9 # Base reduced
            font_size_time = 7   # Base reduced
            text_y_offset_artist = -3 # Adjusted
            text_y_offset_time = 5    # Adjusted

            if event_height_px < 25: 
                font_size_artist = 7
                font_size_time = 5
                text_y_offset_artist = -2
                text_y_offset_time = 3
            if event_height_px < 15: 
                 font_size_artist = 6 
                 text_y_offset_artist = 0 
                 font_size_time = 0 
            if event_width_px < 40: 
                font_size_artist = min(font_size_artist, 5)

            svg_parts.append(f'''<g transform="translate({event_x}, {event_y})">
                <rect width="{event_width_px}" height="{event_height_px}" rx="1.5" ry="1.5" fill="{event_fill_color}"/>
                <text x="{event_width_px/2}" y="{event_height_px/2 + text_y_offset_artist}" text-anchor="middle" font-size="{font_size_artist}" font-weight="bold" fill="{text_color}" dominant-baseline="middle">{artist_name}</text>
                {f'<text x="{event_width_px/2}" y="{event_height_px/2 + text_y_offset_time}" text-anchor="middle" font-size="{font_size_time}" fill="{text_color}" opacity="0.85" dominant-baseline="middle">{start_time_str}-{end_time_str}</text>' if font_size_time > 0 else ''}
            </g>''')
        
        legend_y_start = svg_height - margin_bottom + 18 # Adjusted for new margin
        legend_box_size = 8 
        legend_font_size = 8 
        legend_spacing = 50 
        legend_items = [
            ('Høj', colors['riskHigh']),
            ('Medium', colors['riskMedium']),
            ('Lav', colors['riskLow']),
            ('Ukendt', colors['riskUnknown'])
        ]
        total_legend_width = (len(legend_items) * legend_spacing) - (legend_spacing - (legend_box_size + 4 + 25)) 
        current_legend_x = margin_left + (grid_width - total_legend_width) / 2 
        for label, fill_color in legend_items:
            svg_parts.append(f'<rect x="{current_legend_x}" y="{legend_y_start - legend_box_size}" width="{legend_box_size}" height="{legend_box_size}" rx="1.5" fill="{fill_color}"/>')
            svg_parts.append(f'''<text x="{current_legend_x + legend_box_size + 3}" y="{legend_y_start - legend_box_size + (legend_box_size/2)}" font-size="{legend_font_size}" fill="{colors["textDark"]}" dominant-baseline="middle">{label}</text>''')
            current_legend_x += legend_spacing 
        
        svg_parts.append('</svg>')
        return ''.join(svg_parts)

    svg_calendar_str = generate_svg_calendar()
    
    return templates.TemplateResponse(
        "calendar_view_print.html",
        {
            "request": request,
            "svg_calendar": svg_calendar_str,
            "selected_date": target_date.strftime("%Y-%m-%d"),
            "selected_date_display": target_date.strftime("%d. %B %Y"),
            "current_user": current_user.username,
            "current_user_role": current_user.role.value,
        }
    )

# --- Contact Routes ---

@app.get("/contacts", response_class=HTMLResponse)
def contacts_view(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None)
):
    """Display contacts with search and filtering functionality."""
    contacts = crud.get_all_contacts(db, search=search, category=category)
    categories = crud.get_contact_categories(db)
    
    return templates.TemplateResponse(
        "contacts.html",
        {
            "request": request,
            "contacts": contacts,
            "categories": categories,
            "current_search": search or "",
            "current_category": category or "",
            "current_user": current_user.username,
            "current_user_role": current_user.role.value,
        }
    )

@app.get("/admin/contacts", response_class=HTMLResponse, tags=["Admin"])
def admin_contacts_view(
    request: Request,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_admin_user),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None)
):
    """Admin view for managing contacts."""
    contacts = crud.get_all_contacts(db, search=search, category=category)
    categories = crud.get_contact_categories(db)
    
    return templates.TemplateResponse(
        "admin_contacts.html",
        {
            "request": request,
            "contacts": contacts,
            "categories": categories,
            "current_search": search or "",
            "current_category": category or "",
            "current_user": admin_user.username,
            "current_user_role": admin_user.role.value,
        }
    )

@app.post("/api/contacts", response_model=schemas.Contact, tags=["Admin API"])
def create_contact_api(
    contact: schemas.ContactCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_admin_user)
):
    """Create a new contact (Admin only)."""
    return crud.create_contact(db, contact)

@app.put("/api/contacts/{contact_id}", response_model=schemas.Contact, tags=["Admin API"])
def update_contact_api(
    contact_id: int,
    contact: schemas.ContactCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_admin_user)
):
    """Update an existing contact (Admin only)."""
    updated_contact = crud.update_contact(db, contact_id, contact)
    if not updated_contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return updated_contact

@app.delete("/api/contacts/{contact_id}", tags=["Admin API"])
def delete_contact_api(
    contact_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_admin_user)
):
    """Delete a contact (Admin only)."""
    if not crud.delete_contact(db, contact_id):
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"message": "Contact deleted successfully"}
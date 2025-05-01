import os
import sys
from datetime import datetime, timezone, timedelta
import locale # Import locale module
import logging # Add logging import

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, Depends, Form, HTTPException, status, Response, Path
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
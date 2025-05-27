from sqlalchemy.orm import Session, joinedload, contains_eager
from sqlalchemy import select, update, delete, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

# Import ORM models from models.py
from . import models
# Import Pydantic schemas from schemas.py
from . import schemas

# --- Artist CRUD ---

def get_artist(db: Session, artist_id: int) -> Optional[models.Artist]:
    """Fetches an artist by primary key ID."""
    return db.get(models.Artist, artist_id)

def get_artist_by_slug(db: Session, artist_slug: str) -> Optional[models.Artist]:
    """Fetches an artist by slug."""
    return db.execute(select(models.Artist).filter(models.Artist.slug == artist_slug)).scalar_one_or_none()

def get_all_artists(db: Session, skip: int = 0, limit: int = 100) -> List[models.Artist]:
    """Fetches all artists with pagination."""
    return db.execute(
        select(models.Artist).order_by(models.Artist.title).offset(skip).limit(limit)
    ).scalars().all()

def create_artist(db: Session, artist: schemas.ArtistCreate) -> models.Artist:
    """Creates a new artist."""
    db_artist = models.Artist(**artist.model_dump())
    db.add(db_artist)
    db.commit()
    db.refresh(db_artist)
    return db_artist

def update_artist(db: Session, artist_slug: str, artist_update: schemas.ArtistCreate) -> Optional[models.Artist]:
    """Updates an existing artist by slug."""
    # Use .model_dump(exclude_unset=True) if you only want to update provided fields
    update_data = artist_update.model_dump()
    # Ensure slug is not updated if present in payload
    update_data.pop('slug', None) 
    
    result = db.execute(
        update(models.Artist)
        .where(models.Artist.slug == artist_slug)
        .values(**update_data)
        .returning(models.Artist) # Return the updated model
    )
    db.commit()
    updated_artist = result.scalar_one_or_none()
    return updated_artist

def delete_artist(db: Session, artist_slug: str) -> bool:
    """Deletes an artist by slug. Returns True if deleted, False otherwise."""
    result = db.execute(
        delete(models.Artist).where(models.Artist.slug == artist_slug)
    )
    db.commit()
    return result.rowcount > 0

# --- Artist Detail Function ---
def get_artist_detail_by_slug(db: Session, artist_slug: str) -> Optional[models.Artist]:
    """Fetches an artist by slug, eagerly loading related assessment and events with stages."""
    return db.execute(
        select(models.Artist)
        .options(
            joinedload(models.Artist.assessment), 
            joinedload(models.Artist.events).joinedload(models.Event.stage) 
        )
        .filter(models.Artist.slug == artist_slug)
    ).unique().scalar_one_or_none()

# --- Event CRUD --- 

def get_event(db: Session, event_id: int) -> Optional[models.Event]:
    return db.get(models.Event, event_id)

def get_all_events(db: Session, skip: int = 0, limit: int = 100) -> List[models.Event]:
    """Fetches all events with pagination."""
    return db.execute(
        select(models.Event).order_by(models.Event.start_time).offset(skip).limit(limit)
    ).scalars().all()

def get_all_events_with_artists_stages(db: Session, skip: int = 0, limit: int = 500) -> List[models.Event]:
    """Fetches all events, eagerly loading artist and stage info."""
    return db.execute(
        select(models.Event)
        .options(joinedload(models.Event.artist), joinedload(models.Event.stage))
        .order_by(models.Event.start_time)
        .offset(skip)
        .limit(limit) # Limit results for performance
    ).scalars().all()

def create_event(db: Session, event: schemas.EventCreate) -> models.Event:
    # Add validation? Check if artist_slug and stage_id exist?
    db_event = models.Event(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def get_events_for_festival_day(db: Session, date: datetime) -> list[models.Event]:
    """Fetches all events for a 'festivaldag' (06:00 to 05:59 next day)."""
    start_of_day = date.replace(hour=6, minute=0, second=0, microsecond=0)
    end_of_day = (start_of_day + timedelta(days=1))
    return db.execute(
        select(models.Event)
        .options(joinedload(models.Event.artist), joinedload(models.Event.stage))
        .where(
            models.Event.start_time >= start_of_day,
            models.Event.start_time < end_of_day
        )
        .order_by(models.Event.start_time)
    ).scalars().all()

# --- Stage CRUD ---

def get_stage(db: Session, stage_id: int) -> Optional[models.Stage]:
    return db.get(models.Stage, stage_id)

def get_stage_by_name(db: Session, name: str) -> Optional[models.Stage]:
    return db.execute(select(models.Stage).filter(models.Stage.name == name)).scalar_one_or_none()

def get_all_stages(db: Session, skip: int = 0, limit: int = 100) -> List[models.Stage]:
    return db.execute(select(models.Stage).order_by(models.Stage.name).offset(skip).limit(limit)).scalars().all()

def create_stage(db: Session, stage: schemas.StageCreate) -> models.Stage:
    db_stage = models.Stage(**stage.model_dump())
    db.add(db_stage)
    db.commit()
    db.refresh(db_stage)
    return db_stage

# --- Risk Assessment CRUD --- 

def get_assessment(db: Session, artist_slug: str) -> Optional[models.RiskAssessment]:
    """Fetches a risk assessment by artist slug."""
    return db.execute(
        select(models.RiskAssessment).filter(models.RiskAssessment.artist_slug == artist_slug)
    ).scalar_one_or_none()

def get_all_assessments(db: Session, skip: int = 0, limit: int = 100) -> List[models.RiskAssessment]:
    """Fetches all risk assessments."""
    return db.execute(
        select(models.RiskAssessment).order_by(models.RiskAssessment.artist_slug).offset(skip).limit(limit)
    ).scalars().all()

def get_all_assessments_with_artists(db: Session, skip: int = 0, limit: int = 500) -> List[models.RiskAssessment]:
    """ Fetches all risk assessments, eagerly loading the associated artist. """ 
    return db.execute(
        select(models.RiskAssessment)
        .options(joinedload(models.RiskAssessment.artist))
        .order_by(models.RiskAssessment.artist_slug)
        .offset(skip)
        .limit(limit)
    ).scalars().all()
    
def get_all_risk_assessments_dict(db: Session) -> Dict[str, models.RiskAssessment]:
    """ Fetches all assessments and returns them as a dict keyed by artist_slug. """
    assessments = get_all_assessments(db, limit=1000) # Fetch a large number
    return {a.artist_slug: a for a in assessments}

def upsert_assessment(db: Session, artist_slug: str, assessment_data: schemas.RiskAssessmentCreate) -> models.RiskAssessment:
    """Creates or updates a risk assessment for an artist."""
    existing_assessment = get_assessment(db, artist_slug)
    
    if existing_assessment:
        # Update existing
        update_values = assessment_data.model_dump(exclude_unset=True) # Only update provided fields
        update_values['updated_at'] = datetime.utcnow() # Manually update timestamp
        
        db.execute(
            update(models.RiskAssessment)
            .where(models.RiskAssessment.artist_slug == artist_slug)
            .values(**update_values)
        )
        db.commit()
        db.refresh(existing_assessment) # Refresh to get updated values
        return existing_assessment
    else:
        # Create new
        db_assessment = models.RiskAssessment(
            artist_slug=artist_slug,
            **assessment_data.model_dump()
        )
        db.add(db_assessment)
        db.commit()
        db.refresh(db_assessment)
        return db_assessment

# --- User CRUD --- 

def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.get(models.User, user_id)

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.execute(select(models.User).filter(models.User.username == username)).scalar_one_or_none()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.execute(select(models.User).filter(models.User.email == email)).scalar_one_or_none()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.execute(select(models.User).offset(skip).limit(limit)).scalars().all()

def create_user(db: Session, user: schemas.UserCreate, hashed_password: str) -> models.User:
    db_user = models.User(
        **user.model_dump(exclude={'password'}), # Exclude plain password
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Contact CRUD ---

def get_contact(db: Session, contact_id: int) -> Optional[models.Contact]:
    """Get a single contact by ID."""
    return db.get(models.Contact, contact_id)

def get_all_contacts(db: Session, skip: int = 0, limit: int = 1000, search: Optional[str] = None, category: Optional[str] = None) -> List[models.Contact]:
    """Get all active contacts with optional search and category filtering."""
    query = select(models.Contact).where(models.Contact.is_active == True)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (models.Contact.name.ilike(search_term)) |
            (models.Contact.phone.ilike(search_term)) |
            (models.Contact.role.ilike(search_term)) |
            (models.Contact.category.ilike(search_term))
        )
    
    if category:
        query = query.where(models.Contact.category == category)
    
    query = query.order_by(models.Contact.sort_order, models.Contact.category, models.Contact.role, models.Contact.name)
    return db.execute(query.offset(skip).limit(limit)).scalars().all()

def get_contact_categories(db: Session) -> List[str]:
    """Get all unique categories from active contacts."""
    return db.execute(
        select(models.Contact.category)
        .where(models.Contact.is_active == True)
        .distinct()
        .order_by(models.Contact.category)
    ).scalars().all()

def create_contact(db: Session, contact: schemas.ContactCreate) -> models.Contact:
    """Create a new contact."""
    db_contact = models.Contact(**contact.model_dump())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

def update_contact(db: Session, contact_id: int, contact_update: schemas.ContactCreate) -> Optional[models.Contact]:
    """Update an existing contact."""
    existing_contact = db.get(models.Contact, contact_id)
    if not existing_contact:
        return None
    
    update_data = contact_update.model_dump()
    update_data['updated_at'] = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(existing_contact, field, value)
    
    db.commit()
    db.refresh(existing_contact)
    return existing_contact

def delete_contact(db: Session, contact_id: int) -> bool:
    """Soft delete a contact by setting is_active to False."""
    existing_contact = db.get(models.Contact, contact_id)
    if not existing_contact:
        return False
    
    existing_contact.is_active = False
    existing_contact.updated_at = datetime.utcnow()
    db.commit()
    return True

# --- Deprecated Functions (Commented out) ---
# def create_or_update_artist(db: Session, artist_data: dict) -> models.Artist:
#     # ... (old implementation) ...

# def get_all_events_with_artists_stages(db: Session):
    # This function might need adjustment based on final schema/model needs
    # The ORM version is provided above.
    # pass 
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel
from .models import UserRoleEnum # Import UserRoleEnum

# --- Enums and Literals --- 
# Defined in models.py, using UserRoleEnum here.
RiskAssessmentLevelEnum = Literal['low', 'medium', 'high']

# --- Base Schemas ---
class RiskAssessmentBase(BaseModel):
    risk_level: Optional[RiskAssessmentLevelEnum] = None
    intensity_level: Optional[RiskAssessmentLevelEnum] = None
    density_level: Optional[RiskAssessmentLevelEnum] = None
    remarks: Optional[str] = None
    crowd_profile: Optional[str] = None
    notes: Optional[str] = None

class ArtistBase(BaseModel):
    slug: str
    title: str
    nationality: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None 
    spotify_link: Optional[str] = None

class StageBase(BaseModel):
    name: str

class EventBase(BaseModel):
    start_time: datetime
    end_time: Optional[datetime] = None
    artist_slug: str # Keep slug for creating/linking initially
    stage_id: int # Link by ID for creating/linking initially
    # Note: ORM will handle stage name/artist title population later

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    role: UserRoleEnum = UserRoleEnum.USER
    disabled: bool = False

# --- Create Schemas ---
class RiskAssessmentCreate(RiskAssessmentBase):
    pass

class ArtistCreate(ArtistBase):
    pass

class StageCreate(StageBase):
    pass

class EventCreate(EventBase):
    pass

class UserCreate(UserBase):
    password: str # Include password for creation

# --- Read/Update Schemas (Includes ID and potentially related data) ---
# Use model_config for Pydantic v2 compatibility with ORM

class RiskAssessment(RiskAssessmentBase):
    id: int
    artist_slug: str
    updated_at: Optional[datetime] = None
    # Note: Doesn't include nested Artist by default, query separately if needed

    model_config = {"from_attributes": True}

class Stage(StageBase):
    id: int
    # Note: Doesn't include list of Events by default
    model_config = {"from_attributes": True}

# Schema for reading an Artist, potentially nested in Event/Detail views
class Artist(ArtistBase):
    id: int # Keep as id for Artist
    created_at: datetime
    updated_at: datetime
    # Note: Doesn't include list of Events/Assessment by default
    model_config = {"from_attributes": True}

# Schema for reading an Event, including nested Artist/Stage info
class Event(EventBase):
    event_id: int # Changed from id
    artist: Optional[Artist] = None # Nested basic artist info
    stage: Optional[Stage] = None # Nested basic stage info
    
    # Overwrite fields from Base if they come from relations
    # We might not need artist_slug/stage_id if we always populate artist/stage
    artist_slug: Optional[str] = None
    stage_id: Optional[int] = None

    model_config = {"from_attributes": True}

# Schema for reading a User (excluding password)
class User(UserBase):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


# --- Schemas for Specific API Responses --- 

# Schema for the main artist detail page response
class ArtistDetail(Artist):
    assessment: Optional[RiskAssessment] = None # Include nested assessment
    events: List[Event] = [] # Include list of nested events (which now use event_id)

# Schema for item in the list on the admin assessments page
class ArtistAssessmentAdminItem(BaseModel):
    artist: Artist # Nested basic artist info
    assessment: RiskAssessment | None # Nested assessment info
    model_config = {"from_attributes": True} # Needed if created from ORM objects


# --- Update Schemas (Optional - Define if needed) ---
# Example:
# class RiskAssessmentUpdate(RiskAssessmentBase):
#     pass # Inherits fields allowed for update

# --- Token Schemas (Keep as is) ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None # Add role here


# --- Ensure forward references are resolved --- 
# Pydantic v2 handles this automatically in most cases, 
# but explicit calls can sometimes help or be needed in complex scenarios.
# ArtistDetail.model_rebuild()
# Event.model_rebuild()

# --- Deprecated/Old Schemas (Commented out from original file) ---
# from .models import UserRole, RiskAssessmentBase # Import UserRole and RiskAssessmentBase
# class RiskAssessmentRead(RiskAssessmentBase):
#     id: int
#     artist_slug: str
#     updated_at: datetime | None = None
# 
#     class Config:
#         orm_mode = True
# 
# class ArtistRead(ArtistBase):
#     id: int
#     image_url: str | None = None # Add image_url if missing
#     description: str | None = None # Add description if missing
# 
#     class Config:
#         orm_mode = True
# 
# class EventRead(EventBase):
#     id: int
#     artist_title: str | None = None
#     artist_slug: str | None = None
#     artist_image: str | None = None
#     stage_name: str | None = None
#     # Ensure start_time and end_time are datetimes
#     start_time: datetime
#     end_time: datetime | None = None
# 
#     class Config:
#         orm_mode = True
# class User(UserBase):
#     id: int
#     role: UserRole # Use the enum directly
# 
#     class Config:
#         orm_mode = True 
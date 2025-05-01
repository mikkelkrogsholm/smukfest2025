# app/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text, Boolean # Import SQLAlchemy components
from sqlalchemy.orm import relationship, declarative_base # Import relationship and base
# from pydantic import BaseModel, Field # No longer needed here
# from typing import Optional, Literal, List # No longer needed here
from typing import Optional, Literal # Keep Optional for relationships, ADD Literal back
from datetime import datetime
from enum import Enum

# --- SQLAlchemy Setup --- 
Base = declarative_base()
# --- End SQLAlchemy Setup ---

# Define UserRole enum (used by SQLAlchemy)
class UserRoleEnum(str, Enum):
    USER = "user"
    ADMIN = "admin"

# Define the allowed levels (used by both Pydantic and SQLAlchemy)
RiskAssessmentLevelEnum = Literal['low', 'medium', 'high']

# === SQLAlchemy ORM Models ===

class Artist(Base):
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, index=True, nullable=False)
    nationality = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    spotify_link = Column(String, nullable=True) # Assuming from database.py
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    events = relationship("Event", back_populates="artist")
    assessment = relationship("RiskAssessment", back_populates="artist", uselist=False) # One-to-one

class Stage(Base):
    __tablename__ = "stages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    # Add other stage details if needed (capacity, location, etc.)

    # Relationships
    events = relationship("Event", back_populates="stage")

class Event(Base):
    __tablename__ = "events"

    event_id = Column(Integer, primary_key=True, index=True)
    # Assuming event_id from database.py was meant to be the primary key?
    # Sticking with 'id' convention for now.
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    
    artist_slug = Column(String, ForeignKey("artists.slug"), nullable=False)
    stage_id = Column(Integer, ForeignKey("stages.id"), nullable=False)

    # Relationships
    artist = relationship("Artist", back_populates="events")
    stage = relationship("Stage", back_populates="events")

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    artist_slug = Column(String, ForeignKey("artists.slug", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    risk_level = Column(SQLEnum('low', 'medium', 'high', name="risk_level_enum"), nullable=True)
    intensity_level = Column(SQLEnum('low', 'medium', 'high', name="intensity_level_enum"), nullable=True)
    density_level = Column(SQLEnum('low', 'medium', 'high', name="density_level_enum"), nullable=True)
    remarks = Column(Text, nullable=True)
    crowd_profile = Column(Text, nullable=True)
    notes = Column(Text, nullable=True) # Internal notes
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    artist = relationship("Artist", back_populates="assessment")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(UserRoleEnum, name="user_role_enum"), default=UserRoleEnum.USER, nullable=False)
    disabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
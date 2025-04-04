import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base # Import the Base from models

# Determine the base directory of the project (one level up from app/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE_NAME = "smukfest_artists.db"
DATABASE_URL = f"sqlite:///{os.path.join(PROJECT_ROOT, DB_FILE_NAME)}"

# SQLAlchemy engine
# connect_args={"check_same_thread": False} is needed only for SQLite.
# It allows multiple threads to interact with the database (FastAPI uses threads).
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# SQLAlchemy session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Function to create database tables based on models
# This can be called explicitly when setting up the application or database
def create_db_tables():
    print(f"Attempting to create tables for database at: {DATABASE_URL}")
    try:
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully (if they didn't exist).")
    except Exception as e:
        print(f"Error creating tables: {e}")

# Dependency to get DB session (will be used in main.py/routers)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Old sqlite3 functions (To be removed or commented out) --- 
# Keep them here temporarily if needed for reference, but they are no longer used
# by the SQLAlchemy ORM approach.

# import sqlite3
# from typing import List, Dict, Any, Optional
# from datetime import datetime, timezone # Import datetime
# # Import models
# from . import models 
# 
# # Determine the base directory of the project (one level up from app/)
# # Assumes database.py is inside the app directory
# PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# DB_FILE = os.path.join(PROJECT_ROOT, "smukfest_artists.db")
# 
# def get_db_connection():
#     """Establishes a connection to the SQLite database."""
#     conn = None
#     try:
#         if not os.path.exists(DB_FILE):
#             print(f"Error: Database file not found at {DB_FILE}")
#             print("Please run the sync script first: python scripts/sync_artists_db.py")
#             return None
#         conn = sqlite3.connect(DB_FILE)
#         conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
#         # print(f"Database connection successful to {DB_FILE}") # Reduce verbosity
#     except sqlite3.Error as e:
#         print(f"Database connection error to {DB_FILE}: {e}")
#     except Exception as e:
#         print(f"An unexpected error occurred during DB connection: {e}")
#     return conn
# 
# def get_all_artists() -> List[Dict[str, Any]]:
#     """Fetches all artists from the database."""
#     conn = get_db_connection()
#     artists = []
#     if conn:
#         cursor = conn.cursor()
#         try:
#             cursor.execute("SELECT slug, title, image_url, nationality, spotify_link, created_at, updated_at FROM artists ORDER BY title ASC")
#             # Convert Row objects to dictionaries
#             artists = [dict(row) for row in cursor.fetchall()]
#             # print(f"Fetched {len(artists)} artists from the database.")
#         except sqlite3.Error as e:
#             print(f"Database error fetching artists: {e}")
#         finally:
#             conn.close()
#             # print("Database connection closed.")
#     return artists
# 
# def get_all_events() -> List[Dict[str, Any]]:
#     """Fetches all events from the database, including artist information."""
#     conn = get_db_connection()
#     events = []
#     if conn:
#         cursor = conn.cursor()
#         try:
#             cursor.execute("""
#                 SELECT e.event_id, e.stage_name, e.start_time, e.end_time,
#                        a.title as artist_title, a.slug as artist_slug, a.image_url as artist_image
#                 FROM events e
#                 JOIN artists a ON e.artist_slug = a.slug
#                 ORDER BY e.start_time ASC
#             """)
#             # Convert Row objects to dictionaries
#             events = [dict(row) for row in cursor.fetchall()]
#             # print(f"Fetched {len(events)} events from the database.")
#         except sqlite3.Error as e:
#             print(f"Database error fetching events: {e}")
#         finally:
#             conn.close()
#             # print("Database connection closed.")
#     return events
# 
# # --- Risk Assessment CRUD Functions --- 
# 
# def get_assessment(artist_slug: str) -> Optional[models.RiskAssessment]:
#     """Fetches a single risk assessment for a given artist slug."""
#     conn = get_db_connection()
#     assessment = None
#     if conn:
#         cursor = conn.cursor()
#         try:
#             cursor.execute("SELECT * FROM risk_assessments WHERE artist_slug = ?", (artist_slug,))
#             row = cursor.fetchone()
#             if row:
#                 # Convert row to RiskAssessment model
#                 assessment_data = dict(row)
#                 # Ensure updated_at is parsed to datetime if needed, or handle if stored differently
#                 if assessment_data.get('updated_at'):
#                      try:
#                          # Assume ISO format stored in DB
#                          assessment_data['updated_at'] = datetime.fromisoformat(assessment_data['updated_at'])
#                      except ValueError:
#                          print(f"Warning: Could not parse updated_at timestamp for {artist_slug}")
#                          assessment_data['updated_at'] = None # Set to None if parsing fails
#                 else:
#                      assessment_data['updated_at'] = None
#                      
#                 assessment = models.RiskAssessment(**assessment_data)
#         except sqlite3.Error as e:
#             print(f"Database error fetching assessment for {artist_slug}: {e}")
#         finally:
#             conn.close()
#     return assessment
# 
# def get_all_assessments() -> List[models.RiskAssessment]:
#     """Fetches all risk assessments from the database."""
#     conn = get_db_connection()
#     assessments = []
#     if conn:
#         cursor = conn.cursor()
#         try:
#             cursor.execute("SELECT * FROM risk_assessments ORDER BY artist_slug ASC")
#             rows = cursor.fetchall()
#             for row in rows:
#                 assessment_data = dict(row)
#                 if assessment_data.get('updated_at'):
#                      try:
#                          assessment_data['updated_at'] = datetime.fromisoformat(assessment_data['updated_at'])
#                      except ValueError:
#                          assessment_data['updated_at'] = None
#                 else:
#                      assessment_data['updated_at'] = None
#                      
#                 assessments.append(models.RiskAssessment(**assessment_data))
#             # print(f"Fetched {len(assessments)} risk assessments.")
#         except sqlite3.Error as e:
#             print(f"Database error fetching all assessments: {e}")
#         finally:
#             conn.close()
#     return assessments
# 
# def upsert_assessment(artist_slug: str, assessment: models.RiskAssessmentCreate) -> Optional[models.RiskAssessment]:
#     """Inserts or updates a risk assessment for a given artist slug."""
#     conn = get_db_connection()
#     if not conn:
#         return None
# 
#     cursor = conn.cursor()
#     now_iso = datetime.now(timezone.utc).isoformat() # Get current time in ISO format
#     
#     # Corrected data tuple with only 8 values for INSERT
#     data_tuple = (
#         artist_slug,
#         assessment.risk_level,
#         assessment.intensity_level,
#         assessment.density_level,
#         assessment.remarks,
#         assessment.crowd_profile,
#         assessment.notes,
#         now_iso # updated_at value
#     )
#     
#     sql = """
#     INSERT INTO risk_assessments (
#         artist_slug, risk_level, intensity_level, density_level, 
#         remarks, crowd_profile, notes, updated_at
#     )
#     VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#     ON CONFLICT(artist_slug) DO UPDATE SET
#         risk_level = excluded.risk_level,
#         intensity_level = excluded.intensity_level,
#         density_level = excluded.density_level,
#         remarks = excluded.remarks,
#         crowd_profile = excluded.crowd_profile,
#         notes = excluded.notes,
#         updated_at = excluded.updated_at;
#     """
#     
#     try:
#         cursor.execute(sql, data_tuple)
#         conn.commit()
#         print(f"Successfully upserted assessment for {artist_slug}")
#         # Fetch the newly inserted/updated record to return it
#         return get_assessment(artist_slug) 
#     except sqlite3.IntegrityError as e:
#         # This could happen if the artist_slug doesn't exist in the artists table
#         print(f"Database integrity error upserting assessment for {artist_slug} (likely invalid artist slug): {e}")
#         conn.rollback()
#         return None
#     except sqlite3.Error as e:
#         print(f"Database error upserting assessment for {artist_slug}: {e}")
#         conn.rollback()
#         return None
#     finally:
#         conn.close()

# Example usage (for testing this module directly)
if __name__ == "__main__":
    print("--- Testing database functions ---")
    # Example: Create/Update an assessment
    # test_slug = "shawn-mendes" # Replace with a valid slug from your DB
    # print(f"Attempting to upsert assessment for {test_slug}...")
    # test_data = models.RiskAssessmentCreate(
    #     risk_level='medium',
    #     intensity_level='high',
    #     density_level='medium',
    #     remarks="Testing remarks",
    #     crowd_profile="Mixed crowd expected.",
    #     notes="First test note."
    # )
    # updated = upsert_assessment(test_slug, test_data)
    # if updated:
    #     print(f"Upsert successful: {updated}")
    # else:
    #     print("Upsert failed.")
    
    # Example: Get the assessment
    # print(f"Fetching assessment for {test_slug}...")
    # fetched = get_assessment(test_slug)
    # if fetched:
    #     print(f"Fetched: {fetched}")
    # else:
    #     print("Assessment not found.")

    # Example: Get all assessments
    print("Fetching all assessments...")
    all_assess = get_all_assessments()
    print(f"Found {len(all_assess)} total assessments.")
    # if all_assess:
    #     print("First assessment:", all_assess[0])
    
    print("--- Test complete ---") 
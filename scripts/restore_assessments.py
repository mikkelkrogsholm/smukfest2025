import os
import sys
import logging
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

# Add project root to sys.path to allow importing 'app' modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from app.models import Base, Artist, RiskAssessment # Import necessary models
# Note: Importing SessionLocal from app.database might interfere if it uses env vars
# configured for the main app. We create fresh engines/sessions here.

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
# Adjust these paths if necessary. Assumes running from project root or container perspective.
NEW_DB_PATH = "data/database.db"
# IMPORTANT: Update this to the correct backup file name!
BACKUP_DB_PATH = "data/database.db.bak-20250501-183045"
# --- End Configuration ---

def get_db_session(db_path: str) -> Session:
    """Creates a new SQLAlchemy session for the given database path."""
    if not os.path.exists(db_path):
        logging.error(f"Database file not found: {db_path}")
        raise FileNotFoundError(f"Database file not found: {db_path}")
    
    database_url = f"sqlite:///{db_path}"
    engine = create_engine(database_url)
    # Optional: Check if tables exist, though we assume they do
    # Base.metadata.create_all(bind=engine, checkfirst=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def restore_assessments(backup_session: Session, new_session: Session):
    """Copies assessments from backup_session to new_session if artist exists."""
    logging.info("Starting assessment restoration...")
    
    # 1. Get all assessments from the backup database
    try:
        backup_assessments = backup_session.execute(select(RiskAssessment)).scalars().all()
        logging.info(f"Found {len(backup_assessments)} assessments in backup database.")
    except Exception as e:
        logging.error(f"Error querying assessments from backup DB: {e}")
        return 0, 0 # Indicate failure

    # 2. Get slugs of all artists currently in the new database
    try:
        new_artist_slugs_query = new_session.execute(select(Artist.slug))
        new_artist_slugs = {slug for slug, in new_artist_slugs_query}
        logging.info(f"Found {len(new_artist_slugs)} artists in the new database.")
    except Exception as e:
        logging.error(f"Error querying artists from new DB: {e}")
        return 0, 0 # Indicate failure

    # 3. Iterate and copy assessments if artist exists in new DB
    restored_count = 0
    skipped_count = 0
    now = datetime.utcnow()

    for backup_assessment in backup_assessments:
        if backup_assessment.artist_slug in new_artist_slugs:
            try:
                # Check if an assessment already exists (shouldn't if DB was fresh, but safer)
                existing_assessment = new_session.execute(
                    select(RiskAssessment).where(RiskAssessment.artist_slug == backup_assessment.artist_slug)
                ).scalar_one_or_none()

                if existing_assessment:
                    logging.warning(f"Assessment for artist '{backup_assessment.artist_slug}' already exists in new DB. Skipping.")
                    skipped_count += 1
                    continue

                # Create a new RiskAssessment object for the new session
                new_assessment = RiskAssessment(
                    artist_slug=backup_assessment.artist_slug,
                    risk_level=backup_assessment.risk_level,
                    intensity_level=backup_assessment.intensity_level,
                    density_level=backup_assessment.density_level,
                    remarks=backup_assessment.remarks,
                    crowd_profile=backup_assessment.crowd_profile,
                    notes=backup_assessment.notes,
                    # Set updated_at, use a consistent time for this run
                    updated_at=now
                )
                new_session.add(new_assessment)
                restored_count += 1
                logging.debug(f"Prepared assessment for '{backup_assessment.artist_slug}' for insertion.")
            except Exception as e:
                logging.error(f"Error preparing assessment for '{backup_assessment.artist_slug}': {e}")
                skipped_count += 1 # Count as skipped due to error
        else:
            logging.warning(f"Artist '{backup_assessment.artist_slug}' not found in new database. Skipping assessment restoration.")
            skipped_count += 1

    # 4. Commit changes to the new database
    try:
        new_session.commit()
        logging.info(f"Successfully committed {restored_count} restored assessments.")
    except Exception as e:
        logging.error(f"Error committing changes to new database: {e}")
        new_session.rollback()
        # Reset counts as the commit failed
        restored_count = 0
        # All non-skipped become skipped due to commit failure
        skipped_count = len(backup_assessments)
        
    return restored_count, skipped_count

if __name__ == "__main__":
    # Ensure the script is run from the project root or adjust paths accordingly
    # Example: python scripts/restore_assessments.py
    
    backup_db_session = None
    new_db_session = None
    
    try:
        logging.info(f"Attempting to restore assessments from '{BACKUP_DB_PATH}' to '{NEW_DB_PATH}'")
        backup_db_session = get_db_session(BACKUP_DB_PATH)
        new_db_session = get_db_session(NEW_DB_PATH)
        
        restored, skipped = restore_assessments(backup_db_session, new_db_session)
        
        logging.info("--- Restoration Summary ---")
        logging.info(f"Assessments Restored: {restored}")
        logging.info(f"Assessments Skipped (Artist Not Found or Error): {skipped}")
        logging.info("-------------------------")
        
    except FileNotFoundError:
        logging.error("One or both database files not found. Aborting.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        # Attempt rollback if session exists and commit failed earlier
        if new_db_session:
            try:
                new_db_session.rollback()
            except: # Ignore rollback errors
                pass
        sys.exit(1)
    finally:
        if backup_db_session:
            backup_db_session.close()
            logging.info("Backup database session closed.")
        if new_db_session:
            new_db_session.close()
            logging.info("New database session closed.")

    logging.info("Assessment restoration script finished.") 
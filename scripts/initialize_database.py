# scripts/initialize_database.py
import os
import sys
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add project root to Python path to find modules like 'app' and 'scripts'
# Assumes this script is run from the project root (/workspace in the container)
PROJECT_ROOT = os.getcwd() # or explicitly "/workspace" if guaranteed
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
    logging.info(f"Added {PROJECT_ROOT} to sys.path")

try:
    from alembic.config import Config
    from alembic import command
    from scripts.seed_users import seed_users
    from app.database import SessionLocal # Make sure this import works
except ImportError as e:
    logging.error(f"Failed to import required modules: {e}")
    logging.error(f"Current sys.path: {sys.path}")
    logging.error(f"Current working directory: {os.getcwd()}")
    sys.exit(1)

def run_migrations():
    """Applies Alembic migrations."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logging.error("DATABASE_URL environment variable not set.")
        sys.exit(1)
    logging.info(f"Setting up DB at: {db_url}")

    alembic_cfg_path = os.path.join(PROJECT_ROOT, "alembic.ini")
    if not os.path.exists(alembic_cfg_path):
         logging.error(f"Alembic config file not found at: {alembic_cfg_path}")
         sys.exit(1)

    alembic_cfg = Config(alembic_cfg_path)
    # Ensure Alembic uses the correct database URL from the environment
    # This might override the one in alembic.ini if necessary, or you can
    # configure alembic.ini to read from the environment variable.
    # Alternatively, ensure alembic.ini is configured correctly for the container path.
    # alembic_cfg.set_main_option('sqlalchemy.url', db_url) # Uncomment if needed

    logging.info("Applying Alembic migrations...")
    try:
        command.upgrade(alembic_cfg, "head")
        logging.info("Migrations applied successfully.")
    except Exception as e:
        logging.error(f"Error applying migrations: {e}")
        sys.exit(1)

def run_seeding():
    """Seeds initial data, like users."""
    logging.info("Attempting to seed users...")
    db = SessionLocal()
    try:
        seed_users(db)
        logging.info("User seeding finished successfully.")
    except Exception as e:
        logging.error(f"Error seeding users: {e}")
        # Decide if seeding failure should stop the whole process
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    logging.info("--- Starting Database Initialization Script ---")
    run_migrations()
    run_seeding()
    logging.info("--- Database Initialization Script Finished ---")
import requests
import json
# import sqlite3 # Removed
import sys
import os
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime # Add datetime for timestamps
from urllib.parse import urlparse # Import urlparse to handle the DATABASE_URL
from dateutil import parser # Import dateutil parser
import logging # Add logging import

# --- SQLAlchemy Imports ---
from sqlalchemy.orm import Session # Changed from sessionmaker
from sqlalchemy import select, delete, update

# Add project root to sys.path to allow importing 'app' modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

# Import necessary components from the app
from app.database import SessionLocal, engine # Import session factory and engine
from app.models import Base, Artist, Stage, Event # Import ORM models

# --- Constants ---
API_URL = "https://www.smukfest.dk/api/content?path=%2Fspilleplanen&simple=1&uid=mal85540"

# --- Get Database Path from Environment Variable ---
DEFAULT_DB_PATH = "/app/data/database.db" # Default path inside container
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

# Extract the path part from the URL (e.g., "sqlite:////app/data/database.db" -> "/app/data/database.db")
parsed_url = urlparse(DATABASE_URL)
if parsed_url.scheme == "sqlite":
    # The path includes the leading '/' after the scheme, so we remove 'sqlite:///'
    DB_PATH = DATABASE_URL.replace('sqlite:///', '/', 1)
else:
    print(f"Warning: Unexpected DATABASE_URL scheme '{parsed_url.scheme}'. Using default path: {DEFAULT_DB_PATH}")
    DB_PATH = DEFAULT_DB_PATH

print(f"Using database path: {DB_PATH}") # Add log to confirm path

# --- API Fetching & Parsing ---
def fetch_and_parse_api_data(url: str) -> Optional[Dict[str, Any]]:
    """Fetches and parses the latest artist and schedule data from the Smukfest API."""
    print(f"Fetching latest data from {url}...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        print("API data fetched successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching API data: {e}")
        return None

    try:
        raw_data = response.json()
        print("API JSON parsed successfully.")
    except json.JSONDecodeError as e:
        print(f"Error parsing API JSON: {e}")
        return None

    # --- Extract Content ---
    try:
        content = raw_data['data']['content']
        raw_artists = content.get('_artists', [])
        print(f"Found {len(raw_artists)} artist entries in API data. (Note: Stages/Schedule seem embedded)")
    except (KeyError, TypeError) as e:
        print(f"Error accessing core content ('data.content'): {e}")
        return None

    # --- Process Artists and Generate Events Simultaneously ---
    artists_list = []
    schedule_list = []
    artist_slugs_from_api = set()
    processed_artist_ids = set() # Use 'id' from API data to track processed artists

    print(f"Processing {len(raw_artists)} raw artist entries...")

    for artist_data in raw_artists:
        if not isinstance(artist_data, dict):
            print(f"Warning: Skipping non-dictionary item in API _artists list: {artist_data}")
            continue

        artist_id = artist_data.get('id')
        slug = artist_data.get('slug')
        title = artist_data.get('title')

        if not all([artist_id, slug, title]):
            missing_fields = [f for f, v in {'id': artist_id, 'slug': slug, 'title': title}.items() if not v]
            print(f"Warning: Skipping artist entry due to missing essential fields ({missing_fields}): ID {artist_id or 'N/A'}, Title '{title or 'N/A'}'")
            continue

        if artist_id in processed_artist_ids:
            # print(f"Warning: Duplicate artist ID '{artist_id}' found in API data. Skipping subsequent instance for '{title}'.") # Less verbose
            continue
        processed_artist_ids.add(artist_id)

        artist_slugs_from_api.add(slug)

        nationality_obj = artist_data.get('nationality')
        nationality = None
        if isinstance(nationality_obj, dict):
            nationality = nationality_obj.get('nationality')

        image_url = None
        if 'thumbnail' in artist_data and isinstance(artist_data['thumbnail'], dict):
            image_url = artist_data['thumbnail'].get('url')
        if not image_url and 'images' in artist_data and isinstance(artist_data['images'], list) and len(artist_data['images']) > 0:
             if isinstance(artist_data['images'][0], dict):
                 image_url = artist_data['images'][0].get('url')
        if not image_url and 'previewImage' in artist_data and isinstance(artist_data['previewImage'], dict):
             image_url = artist_data['previewImage'].get('url')

        artist_info = {
            # Map API fields to ORM model fields (ensure names match models.Artist)
            'slug': slug,
            'title': title,
            'image_url': image_url,
            'nationality': nationality,
            'description': artist_data.get('previewText'), # Map previewText to description
            'spotify_link': artist_data.get('spotifyLink'),
            # We'll handle created_at/updated_at during insert/update
            # 'created_at': artist_data.get('createdAt'),
            # 'updated_at': artist_data.get('updatedAt')
        }
        artists_list.append(artist_info)

        start_time = artist_data.get('startTime')
        if start_time:
            location_obj = artist_data.get('location')
            stage_name = None
            if isinstance(location_obj, dict):
                # Always prefer 'name' for stage name, fallback to 'title' if needed
                stage_name = location_obj.get('name') or location_obj.get('title')
                if not stage_name:
                    print(f"Warning: Event for artist '{slug}' is missing stage name in location object: {location_obj}")
            else:
                print(f"Warning: Event for artist '{slug}' has no location object.")

            event_info = {
                # Map API fields to ORM model fields (ensure names match models.Event)
                'artist_slug': slug,
                'stage_name': stage_name or "TBA", # Use default if missing, will be mapped to stage_id later
                'start_time': start_time,
                'end_time': artist_data.get('endTime')
            }
            schedule_list.append(event_info)

    print(f"Processed {len(artists_list)} unique artists.")
    print(f"Generated {len(schedule_list)} events from artist entries with start times.")

    return {
        "artists": artists_list,
        "schedule": schedule_list,
        "artist_slugs_from_api": artist_slugs_from_api
    }


# --- Database Operations (Refactored for SQLAlchemy) ---

# Removed setup_database function as Base.metadata.create_all handles it

def sync_database(db: Session, parsed_data: Dict[str, Any]):
    """Syncs the database with the parsed artist and schedule data using SQLAlchemy ORM."""

    artists_to_sync = parsed_data.get("artists")
    schedule_to_sync = parsed_data.get("schedule")
    api_artist_slugs = parsed_data.get("artist_slugs_from_api")

    if not artists_to_sync or api_artist_slugs is None:
        print("Warning: Artist list or set of API slugs is missing from parsed data. Cannot sync artists.")
        return # Exit if essential artist data is missing

    # --- Sync Artists ---
    print(f"Syncing {len(artists_to_sync)} artists...")
    inserted_artists = 0
    updated_artists = 0

    # Fetch existing artists into a dictionary {slug: id} for quick lookup
    existing_artists_query = db.execute(select(Artist.slug, Artist.id))
    existing_artists_map = {slug: id for slug, id in existing_artists_query}
    print(f"Found {len(existing_artists_map)} existing artists in DB.")

    artists_to_insert = []
    artists_to_update = []
    now = datetime.utcnow()

    for artist_data in artists_to_sync:
        slug = artist_data['slug']
        # Prepare data, ensuring keys match the model fields
        artist_fields = {
            'title': artist_data.get('title'),
            'image_url': artist_data.get('image_url'),
            'nationality': artist_data.get('nationality'),
            'description': artist_data.get('previewText'), # Map previewText to description
            'spotify_link': artist_data.get('spotify_link'),
            'updated_at': now # Set updated_at for both inserts and updates
        }

        if slug in existing_artists_map:
            # Prepare for bulk update: needs primary key identifier (id) and changed fields
            update_data = artist_fields.copy()
            update_data['id'] = existing_artists_map[slug] # Add the id for matching
            artists_to_update.append(update_data)
            updated_artists += 1
        else:
            # Prepare for bulk insert: add slug and created_at
            insert_data = artist_fields.copy()
            insert_data['slug'] = slug
            insert_data['created_at'] = now # Set created_at only for new artists
            artists_to_insert.append(insert_data)
            inserted_artists += 1

    # Perform bulk operations
    if artists_to_insert:
        print(f"Bulk inserting {len(artists_to_insert)} new artists...")
        db.bulk_insert_mappings(Artist, artists_to_insert)
        print("Bulk insert artists finished.")
    if artists_to_update:
        print(f"Bulk updating {len(artists_to_update)} existing artists...")
        # Note: bulk_update_mappings requires dictionaries containing the primary key
        db.bulk_update_mappings(Artist, artists_to_update)
        print("Bulk update artists finished.")

    print(f"Artist sync complete. Inserted: {inserted_artists}, Updated: {updated_artists}")

    # --- Delete Stale Artists (artists in DB but not in API) ---
    stale_slugs = set(existing_artists_map.keys()) - api_artist_slugs
    if stale_slugs:
        print(f"Found {len(stale_slugs)} stale artists to delete: {stale_slugs}")
        delete_stmt = delete(Artist).where(Artist.slug.in_(stale_slugs))
        result = db.execute(delete_stmt)
        print(f"Deleted {result.rowcount} stale artists.")
    else:
        print("No stale artists found to delete.")

    # --- Sync Stages ---
    print("Syncing stages...")
    # Get unique stage names from the schedule, defaulting to 'TBA'
    api_stage_names = {event.get('stage_name', 'TBA') for event in schedule_to_sync}
    print(f"Found unique stage names in API data: {api_stage_names}")

    # Fetch existing stages into a dictionary {name: id}
    existing_stages_query = db.execute(select(Stage.name, Stage.id))
    stages_map = {name: id for name, id in existing_stages_query}
    print(f"Found {len(stages_map)} existing stages in DB.")

    # Determine new stages
    new_stage_names = api_stage_names - set(stages_map.keys())
    stages_to_insert = [{'name': name} for name in new_stage_names]

    if stages_to_insert:
        print(f"Bulk inserting {len(stages_to_insert)} new stages: {new_stage_names}")
        db.bulk_insert_mappings(Stage, stages_to_insert)
        print("Bulk insert stages finished.")
        # Refresh the stages map to include the newly inserted stages
        # Re-querying is the simplest way to get the new IDs
        refreshed_stages_query = db.execute(select(Stage.name, Stage.id))
        stages_map = {name: id for name, id in refreshed_stages_query}
        print(f"Refreshed stages map size: {len(stages_map)}")
    else:
        print("No new stages to insert.")

    # --- Sync Events ---
    if not schedule_to_sync:
        print("Warning: Event schedule list is missing or empty. Cannot sync events.")
    else:
        print(f"Syncing {len(schedule_to_sync)} events...")

        # Clear existing events first
        deleted_rows = db.execute(delete(Event))
        print(f"Cleared {deleted_rows.rowcount} existing events from the table.")

        events_to_insert = []
        skipped_events = 0
        parse_errors = 0
        for event_data in schedule_to_sync:
            stage_name = event_data.get('stage_name', 'TBA')
            artist_slug = event_data.get('artist_slug')
            stage_id = stages_map.get(stage_name) # Look up ID from the potentially refreshed map

            if stage_id is None:
                 print(f"ERROR: Could not find stage_id for stage name '{stage_name}' even after insert attempt. Skipping event for artist '{artist_slug}'.")
                 skipped_events += 1
                 continue

            # Parse date strings into datetime objects
            start_time_obj = None
            end_time_obj = None
            start_time_str = event_data.get('start_time')
            end_time_str = event_data.get('end_time')

            try:
                if start_time_str:
                    start_time_obj = parser.isoparse(start_time_str)
                if end_time_str:
                    end_time_obj = parser.isoparse(end_time_str)
            except ValueError as e:
                print(f"ERROR parsing date for event (Artist: {artist_slug}, Start: {start_time_str}, End: {end_time_str}): {e}")
                parse_errors += 1
                continue # Skip event if dates can't be parsed
            
            # Ensure start_time is present (essential for an event)
            if start_time_obj is None:
                print(f"Warning: Skipping event for artist '{artist_slug}' due to missing start_time.")
                skipped_events += 1
                continue

            event_insert_data = {
                'artist_slug': artist_slug,
                'stage_id': stage_id,
                'start_time': start_time_obj, # Use datetime object
                'end_time': end_time_obj      # Use datetime object (or None)
            }
            events_to_insert.append(event_insert_data)

        if events_to_insert:
            print(f"Bulk inserting {len(events_to_insert)} events...")
            db.bulk_insert_mappings(Event, events_to_insert)
            print("Bulk insert events finished.")
        print(f"Event insertion complete. Inserted: {len(events_to_insert)}, Skipped: {skipped_events}, Parse Errors: {parse_errors}")

# --- Main Execution Logic ---

def run_sync(): # Renamed from main
    """Fetches data, parses it, and syncs it with the database."""
    parsed_data = fetch_and_parse_api_data(API_URL)

    if parsed_data:
        try:
            # Use a session context manager
            with SessionLocal() as db:
                sync_database(db, parsed_data)
                db.commit() # Commit the transaction
            print("Database sync completed successfully.")
            logging.info("Database sync completed successfully.")
        except Exception as e:
            # Session automatically rolls back on exception with context manager
            print(f"Error during database sync: {e}")
            logging.error(f"Error during database sync: {e}", exc_info=True)
            # Re-raise the exception if needed, or handle appropriately
            # raise # Uncomment if the caller needs to know about the failure
    else:
        print("Database sync skipped due to API fetch/parse errors.")
        logging.warning("Database sync skipped due to API fetch/parse errors.")

# Add the main execution block back so the script can be run directly
if __name__ == "__main__":
    print("Starting manual Smukfest Artist & Schedule DB Sync...")
    run_sync()
    print("Manual sync process finished.") 
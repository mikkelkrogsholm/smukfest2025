import requests
import json
import sqlite3
import sys
import os
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime # Add datetime for timestamps

# --- Constants ---
API_URL = "https://www.smukfest.dk/api/content?path=%2Fprogram"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(PROJECT_ROOT, "smukfest_artists.db")

# --- API Fetching & Parsing ---
def fetch_and_parse_api_data(url: str) -> Optional[Dict[str, Any]]:
    """Fetches and parses the latest artist and schedule data from the Smukfest API.
    Note: Based on debugging, stage and schedule info seem embedded within _artists list.
    """
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
        # --- Debugging: Print content structure ---
        # print("--- Debug: Keys in content ---")
        # print(content.keys())
        # --- End Debugging ---

        raw_artists = content.get('_artists', [])
        # raw_stages = content.get('_stages', []) # No longer seems available
        # raw_schedule = content.get('_schedule', []) # No longer seems available

        # --- Debugging: Print sample items ---
        # print("--- Debug: Sample _artists item (first one if exists) ---")
        # if raw_artists:
        #     print(json.dumps(raw_artists[0], indent=2))
        # else:
        #     print("_artists list is empty or not found.")
        #
        # print("--- Debug: Sample _stages item (first one if exists) ---")
        # # if raw_stages: ...
        # print("_stages list is empty or not found.") # Assume empty based on previous debug
        #
        # print("--- Debug: Sample _schedule item (first one if exists) ---")
        # # if raw_schedule: ...
        # print("_schedule list is empty or not found.") # Assume empty based on previous debug
        # print("--- End Debugging ---\n")

        print(f"Found {len(raw_artists)} artist entries in API data. (Note: Stages/Schedule seem embedded)")
    except (KeyError, TypeError) as e:
        print(f"Error accessing core content ('data.content'): {e}")
        # print("--- Debug: Raw Data Structure ---") # Keep debug for error case
        # try:
        #     print(json.dumps(raw_data.get('data', {}), indent=2))
        # except Exception as dump_e:
        #     print(f"Could not dump raw_data for debugging: {dump_e}")
        # print("--- End Debugging ---")
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

        # Check for essential artist fields (using 'id' instead of '_id')
        artist_id = artist_data.get('id')
        slug = artist_data.get('slug')
        title = artist_data.get('title')

        if not all([artist_id, slug, title]):
            missing_fields = [f for f, v in {'id': artist_id, 'slug': slug, 'title': title}.items() if not v]
            print(f"Warning: Skipping artist entry due to missing essential fields ({missing_fields}): ID {artist_id or 'N/A'}, Title '{title or 'N/A'}'")
            continue

        # Prevent processing duplicate artist entries based on API 'id'
        if artist_id in processed_artist_ids:
            print(f"Warning: Duplicate artist ID '{artist_id}' found in API data. Skipping subsequent instance for '{title}'.")
            continue
        processed_artist_ids.add(artist_id)

        # Add slug to set for detecting stale entries later
        if slug in artist_slugs_from_api:
             print(f"Warning: Duplicate slug '{slug}' detected for different artist IDs ('{artist_id}' vs previous). This might indicate data issues.")
             # Decide how to handle: skip this one, overwrite, or store both if DB allows?
             # Current approach: Add to set anyway, DB upsert will handle based on slug PK.
        artist_slugs_from_api.add(slug)

        # Extract nationality safely
        nationality_obj = artist_data.get('nationality')
        nationality = None
        if isinstance(nationality_obj, dict):
            nationality = nationality_obj.get('nationality') # Field inside the object

        # Extract image URL safely (check multiple fields)
        image_url = None
        if 'thumbnail' in artist_data and isinstance(artist_data['thumbnail'], dict):
            image_url = artist_data['thumbnail'].get('url')
        if not image_url and 'images' in artist_data and isinstance(artist_data['images'], list) and len(artist_data['images']) > 0:
             if isinstance(artist_data['images'][0], dict):
                 image_url = artist_data['images'][0].get('url')
        if not image_url and 'previewImage' in artist_data and isinstance(artist_data['previewImage'], dict):
             image_url = artist_data['previewImage'].get('url')

        # Create artist info for the artists table
        artist_info = {
            'slug': slug,
            'title': title,
            'image_url': image_url,
            'nationality': nationality,
            'spotify_link': artist_data.get('spotifyLink'),
            'created_at': artist_data.get('createdAt'),
            'updated_at': artist_data.get('updatedAt')
        }
        artists_list.append(artist_info)

        # --- Generate Event if startTime exists ---
        start_time = artist_data.get('startTime')
        if start_time:
            # Extract stage name from location object (safely)
            location_obj = artist_data.get('location')
            stage_name = None
            stage_id = None # Add stage_id variable
            if isinstance(location_obj, dict):
                # Try common keys for stage name within the location object
                stage_name = location_obj.get('title') or location_obj.get('name')
                if not stage_name:
                     print(f"Warning: Found location object for artist '{slug}' but couldn't determine stage name from keys: {location_obj.keys()}")
            # else: # Handle case where location_obj might not be a dict (or is missing)
            #     print(f"Warning: No valid location object found for artist '{slug}' to determine stage.")

            # Create a unique event ID - NO LONGER NEEDED - Use AutoIncrement PK
            # event_id = f"{slug}-{start_time}"

            event_info = {
                # 'event_id': event_id, # REMOVED
                'artist_slug': slug,
                'stage_name': stage_name, # Keep stage_name for lookup later
                'start_time': start_time,
                'end_time': artist_data.get('endTime') # Extract endTime if available
            }
            schedule_list.append(event_info)
        # else:
            # print(f"Debug: Artist '{slug}' has no startTime, not creating event.") # Optional debug log

    print(f"Processed {len(artists_list)} unique artists.")
    print(f"Generated {len(schedule_list)} events from artist entries with start times.")

    return {
        "artists": artists_list,
        "schedule": schedule_list,
        "artist_slugs_from_api": artist_slugs_from_api # Needed for deleting stale artists
    }

# --- Database Operations ---
def setup_database(db_filename: str) -> Tuple[Optional[sqlite3.Connection], Optional[sqlite3.Cursor]]:
    """Connects to SQLite DB, ensures artists, events, and risk_assessments tables exist."""
    conn = None
    try:
        conn = sqlite3.connect(db_filename)
        # Enable foreign key constraint enforcement
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        print(f"Successfully connected to database {db_filename}")

        # Ensure artists table exists
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS artists (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- Align with models.py (optional but good practice)
            slug TEXT UNIQUE NOT NULL,
            title TEXT,
            image_url TEXT,
            nationality TEXT,
            spotify_link TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """)
        print("Table 'artists' checked/created successfully.")

        # Ensure stages table exists (NEW)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        """)
        print("Table 'stages' checked/created successfully.")

        # Ensure events table exists (MODIFIED)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Align with models.py
            artist_slug TEXT NOT NULL,
            stage_id INTEGER NOT NULL, -- Changed from stage_name TEXT
            start_time TEXT,
            end_time TEXT,
            FOREIGN KEY(artist_slug) REFERENCES artists(slug) ON DELETE CASCADE,
            FOREIGN KEY(stage_id) REFERENCES stages(id) -- Added FK constraint
        )
        """)
        print("Table 'events' checked/created successfully.")

        # Ensure risk_assessments table exists
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_assessments (
            artist_slug TEXT PRIMARY KEY,
            risk_level TEXT CHECK(risk_level IN ('low', 'medium', 'high')),
            intensity_level TEXT CHECK(intensity_level IN ('low', 'medium', 'high')),
            density_level TEXT CHECK(density_level IN ('low', 'medium', 'high')),
            remarks TEXT,
            crowd_profile TEXT,
            notes TEXT,
            updated_at TEXT,
            FOREIGN KEY(artist_slug) REFERENCES artists(slug) ON DELETE CASCADE
        )
        """)
        print("Table 'risk_assessments' checked/created successfully.")

        return conn, cursor
    except sqlite3.Error as e:
        print(f"Database setup error: {e}")
        if conn:
            conn.close()
        return None, None

def sync_database(db_filename: str, parsed_data: Dict[str, Any]):
    """Syncs the database with the parsed artist and schedule data."""
    conn, cursor = setup_database(db_filename)
    if not conn or not cursor:
        print("Failed to setup database connection. Aborting sync.")
        return

    artists_to_sync = parsed_data.get("artists")
    schedule_to_sync = parsed_data.get("schedule")
    api_artist_slugs = parsed_data.get("artist_slugs_from_api")

    if not artists_to_sync or api_artist_slugs is None:
        # Schedule might be empty if no artists have start times, which is okay.
        print("Warning: Artist list or set of API slugs is missing from parsed data. Cannot sync artists.")
    else:
        # --- Sync Artists ---
        print(f"Syncing {len(artists_to_sync)} artists...")
        inserted_artists = 0
        updated_artists = 0
        error_artists = 0

        # Get existing slugs for comparison
        cursor.execute("SELECT slug FROM artists")
        existing_slugs = {row[0] for row in cursor.fetchall()}

        for artist in artists_to_sync:
            try:
                if artist['slug'] in existing_slugs:
                    # Update existing artist
                    cursor.execute("""
                        UPDATE artists 
                        SET title = ?, image_url = ?, nationality = ?, spotify_link = ?, created_at = ?, updated_at = ?
                        WHERE slug = ?
                    """, (
                        artist['title'], artist['image_url'], artist['nationality'], 
                        artist['spotify_link'], artist['created_at'], datetime.utcnow().isoformat(), # Use current time for update
                        artist['slug']
                    ))
                    if cursor.rowcount > 0:
                         updated_artists += 1
                else:
                    # Insert new artist
                    cursor.execute("""
                        INSERT INTO artists (slug, title, image_url, nationality, spotify_link, created_at, updated_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        artist['slug'], artist['title'], artist['image_url'], artist['nationality'], 
                        artist['spotify_link'], artist.get('created_at', datetime.utcnow().isoformat()), datetime.utcnow().isoformat()
                    ))
                    inserted_artists += 1
            except sqlite3.Error as e:
                print(f"Database error syncing artist '{artist.get('slug', 'N/A')}': {e}")
                error_artists += 1
        
        print(f"Artist sync complete. Inserted: {inserted_artists}, Updated: {updated_artists}, Errors/Skipped: {error_artists}")
        
        # --- Delete Stale Artists (artists in DB but not in API) ---
        stale_slugs = existing_slugs - api_artist_slugs
        if stale_slugs:
            print(f"Found {len(stale_slugs)} stale artists to delete: {stale_slugs}")
            try:
                # Create placeholders for the slugs
                placeholders = ','.join('?' * len(stale_slugs))
                cursor.execute(f"DELETE FROM artists WHERE slug IN ({placeholders})", tuple(stale_slugs))
                print(f"Deleted {cursor.rowcount} stale artists.")
            except sqlite3.Error as e:
                print(f"Database error deleting stale artists: {e}")
        else:
            print("No stale artists found to delete.")

    # --- Sync Events (Major Changes Here) ---
    if not schedule_to_sync:
        print("Warning: Event schedule list is missing or empty. Cannot sync events.")
    else:
        print(f"Syncing {len(schedule_to_sync)} events...")
        inserted_events = 0
        error_events = 0

        try:
            # Clear existing events first (optional, depends on desired sync behavior)
            # If API is source of truth, clearing ensures removed events are gone.
            cursor.execute("DELETE FROM events")
            print(f"Cleared {cursor.rowcount} existing events from the table.")

            for event in schedule_to_sync:
                stage_id = None
                stage_name = event.get('stage_name')

                if stage_name:
                    try:
                        # 1. Ensure stage exists in 'stages' table
                        cursor.execute("INSERT OR IGNORE INTO stages (name) VALUES (?)", (stage_name,))
                        
                        # 2. Get the stage_id
                        cursor.execute("SELECT id FROM stages WHERE name = ?", (stage_name,))
                        result = cursor.fetchone()
                        if result:
                            stage_id = result[0]
                        else:
                             print(f"Error: Failed to retrieve stage_id for stage '{stage_name}' after INSERT OR IGNORE.")
                             error_events += 1
                             continue # Skip this event if stage lookup fails
                    except sqlite3.Error as e:
                         print(f"Database error handling stage '{stage_name}' for event '{event.get('artist_slug', 'N/A')}': {e}")
                         error_events += 1
                         continue # Skip this event
                else:
                    # Handle events with no stage? Options:
                    # a) Skip the event
                    # b) Create a default 'Unknown' stage and use its ID
                    # c) Allow NULL stage_id if the schema permits (currently NOT NULL)
                    print(f"Warning: Event for artist '{event.get('artist_slug')}' has no stage name. Skipping event insertion.")
                    error_events += 1
                    continue # Skip events without a stage
                
                # 3. Insert event with stage_id
                if stage_id: # Only insert if we have a valid stage_id
                    try:
                        cursor.execute("""
                            INSERT INTO events (artist_slug, stage_id, start_time, end_time) 
                            VALUES (?, ?, ?, ?)
                        """, (
                            event['artist_slug'], 
                            stage_id, 
                            event['start_time'], 
                            event.get('end_time') # Use .get() for optional end_time
                        ))
                        inserted_events += 1
                    except sqlite3.Error as e:
                        print(f"Database error inserting event '{event.get('artist_slug', 'N/A')}' with stage_id {stage_id}: {e}")
                        error_events += 1
                # else: # Already handled by the continue statements above
                    # print(f"Skipping event insertion for '{event.get('artist_slug')}' due to missing stage_id.")

            print(f"Event insertion complete. Inserted: {inserted_events}, Errors/Skipped: {error_events}")

        except sqlite3.Error as e:
            print(f"General database error during event sync: {e}")
            conn.rollback() # Rollback on general error during event sync phase
        # else: # Commit is handled outside the loops
            # pass 

    # --- Commit Changes and Close Connection ---
    try:
        conn.commit()
        print("Database changes committed.")
    except sqlite3.Error as e:
        print(f"Database commit error: {e}")
        conn.rollback() # Rollback if commit fails
    finally:
        if conn:
            conn.close()
            print(f"Database connection to {db_filename} closed.")

# --- Main Execution ---
def main():
    """Main function to fetch data and sync the database."""
    # 1. Fetch and parse fresh data from API
    parsed_data = fetch_and_parse_api_data(API_URL)
    if parsed_data is None:
        print("Failed to fetch or parse API data. Exiting sync process.")
        sys.exit(1)

    # 2. Synchronize the database
    sync_database(DB_FILE, parsed_data)

if __name__ == "__main__":
    print("Starting Smukfest Artist & Schedule DB Sync...")
    main()
    print("Sync process finished.") 
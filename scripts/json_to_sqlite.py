import json
import sqlite3
import sys

# Define file paths
JSON_FILE = "smukfest_artists.json"
DB_FILE = "smukfest_artists.db"

def load_json_data(filename):
    """Loads artist data from a JSON file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Successfully loaded data from {filename}")
        # Basic validation: Check if it's a list
        if not isinstance(data, list):
             print(f"Error: Expected a list of artists in {filename}, but got {type(data)}")
             return None
        return data
    except FileNotFoundError:
        print(f"Error: JSON file not found at {filename}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filename}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading {filename}: {e}")
        return None

def create_database_and_table(db_filename):
    """Connects to the SQLite database and creates the artists table if it doesn't exist."""
    try:
        conn = sqlite3.connect(db_filename)
        cursor = conn.cursor()
        print(f"Successfully connected to database {db_filename}")

        # Create table - Using slug as PRIMARY KEY assuming it's unique
        # Using 'IF NOT EXISTS' ensures we don't get an error if the table already exists
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS artists (
            slug TEXT PRIMARY KEY,
            title TEXT,
            image_url TEXT,
            nationality TEXT,
            spotify_link TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """)
        print("Table 'artists' checked/created successfully.")
        return conn, cursor
    except sqlite3.Error as e:
        print(f"Database error during connection/table creation: {e}")
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred during DB setup: {e}")
        return None, None


def insert_artists_data(conn, cursor, artists_data):
    """Inserts artist data into the SQLite database table."""
    inserted_count = 0
    skipped_count = 0
    try:
        for artist in artists_data:
            # Ensure basic structure and get slug
            if not isinstance(artist, dict):
                print(f"Warning: Skipping non-dictionary item: {artist}")
                skipped_count += 1
                continue

            slug = artist.get('slug')
            if not slug:
                print(f"Warning: Skipping artist with missing slug: {artist.get('title', 'N/A')}")
                skipped_count += 1
                continue

            # Prepare data tuple, handling potential None values
            data_tuple = (
                slug,
                artist.get('title'),
                artist.get('url (image)'), # Match the key from the JSON
                artist.get('nationality'),
                artist.get('spotifyLink'),  # Match the key from the JSON
                artist.get('createdAt'),    # Added field
                artist.get('updatedAt')     # Added field
            )

            # Use INSERT OR IGNORE to handle potential duplicate slugs gracefully
            try:
                cursor.execute("""
                INSERT OR IGNORE INTO artists (slug, title, image_url, nationality, spotify_link, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, data_tuple)
                # Check if a row was actually inserted (affected row count)
                if cursor.rowcount > 0:
                    inserted_count += 1
                else:
                     # If rowcount is 0 with INSERT OR IGNORE, it means the PK (slug) already existed
                     print(f"Info: Slug '{slug}' already exists, skipping insertion.")
                     skipped_count += 1

            except sqlite3.Error as e:
                print(f"Database error inserting artist with slug {slug}: {e}")
                skipped_count += 1

        conn.commit()
        print(f"Data insertion complete. Inserted: {inserted_count}, Skipped/Ignored: {skipped_count}")

    except Exception as e:
        print(f"An unexpected error occurred during data insertion: {e}")
        # Rollback changes in case of an error during the loop
        conn.rollback()
        print("Transaction rolled back due to error.")

def main():
    """Main function to orchestrate loading JSON and saving to SQLite."""
    artists = load_json_data(JSON_FILE)
    if artists is None:
        sys.exit(1) # Exit if loading failed

    if not artists:
        print("JSON file loaded, but it contains no artist data. Nothing to insert.")
        sys.exit(0)

    conn, cursor = create_database_and_table(DB_FILE)
    if conn is None or cursor is None:
        sys.exit(1) # Exit if DB connection/setup failed

    insert_artists_data(conn, cursor, artists)

    # Close the database connection
    if conn:
        try:
            conn.close()
            print(f"Database connection to {DB_FILE} closed.")
        except sqlite3.Error as e:
            print(f"Error closing database connection: {e}")

if __name__ == "__main__":
    main() 
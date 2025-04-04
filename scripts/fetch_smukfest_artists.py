import requests
import json
import sys

# Define the API endpoint
API_URL = "https://www.smukfest.dk/api/content?path=%2Fprogram"

# Define the expected itemType for artist entries (based on the provided snippet)
# We might need to adjust this based on the full JSON structure.
ARTIST_ITEM_TYPE = "1104017" # Corresponds to 'Musik 2025' contentType

def fetch_and_parse_artists(url):
    """Fetches data from the API, parses JSON, and extracts artist info directly from the _artists list."""
    print(f"Fetching data from {url}...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        print("Data fetched successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

    try:
        data = response.json()
        print("JSON parsed successfully.")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        # Optionally print response text for debugging non-JSON responses
        # print("Response text:", response.text)
        sys.exit(1)

    # Navigate directly to the _artists list
    try:
        artists_list = data['data']['content']['_artists']
        print(f"Found _artists list with {len(artists_list)} entries.")
    except (KeyError, TypeError) as e:
        print(f"Error accessing 'data.content._artists' in the JSON structure: {e}")
        print("Please verify the JSON structure from the API.")
        # print full data structure for debugging if needed
        # print(json.dumps(data, indent=2))
        return None

    extracted_artists = []
    for artist_data in artists_list:
        # Ensure artist_data is a dictionary before accessing keys
        if not isinstance(artist_data, dict):
            print(f"Warning: Skipping non-dictionary item in _artists list: {artist_data}")
            continue

        # Extract nationality safely
        nationality = None
        if 'nationality' in artist_data and isinstance(artist_data['nationality'], dict):
            nationality = artist_data['nationality'].get('nationality') # e.g., 'DK'

        # Extract image URL safely
        image_url = None
        if 'thumbnail' in artist_data and isinstance(artist_data['thumbnail'], dict):
            image_url = artist_data['thumbnail'].get('url')
        if not image_url and 'images' in artist_data and isinstance(artist_data['images'], list) and len(artist_data['images']) > 0:
             if isinstance(artist_data['images'][0], dict):
                 image_url = artist_data['images'][0].get('url')
        if not image_url and 'previewImage' in artist_data and isinstance(artist_data['previewImage'], dict):
             image_url = artist_data['previewImage'].get('url') # Fallback

        artist_info = {
            'title': artist_data.get('title'),
            'slug': artist_data.get('slug'),
            'url (image)': image_url,
            'nationality': nationality,
            'spotifyLink': artist_data.get('spotifyLink'),
            'createdAt': artist_data.get('createdAt'),
            'updatedAt': artist_data.get('updatedAt')
        }

        # Only add if a title exists (basic check for a valid entry)
        if artist_info['title']:
            extracted_artists.append(artist_info)
        else:
             print(f"Warning: Skipping artist entry due to missing title: {artist_data.get('id')}")


    if not extracted_artists:
         print("Error: Could not extract any artist data from the _artists list.")
         return None

    print(f"Successfully extracted data for {len(extracted_artists)} artists.")

    # Deduplication might still be relevant if the API returns duplicates, but less likely now.
    unique_artists = []
    seen_titles = set()
    for artist in extracted_artists:
        identifier = artist.get('title') # Use title as primary identifier
        if identifier and identifier not in seen_titles:
            unique_artists.append(artist)
            seen_titles.add(identifier)
        elif identifier:
            print(f"Warning: Duplicate title found and skipped: {identifier}")

    print(f"Returning {len(unique_artists)} unique artists.")
    return unique_artists

def save_to_json(data, filename="smukfest_artists.json"):
    """Saves the extracted artist data to a JSON file."""
    if data is None:
        print("No data to save.")
        return

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Artist data successfully saved to {filename}")
    except IOError as e:
        print(f"Error saving data to {filename}: {e}")

if __name__ == "__main__":
    artists_data = fetch_and_parse_artists(API_URL)
    save_to_json(artists_data) 
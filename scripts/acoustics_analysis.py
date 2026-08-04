import csv
import json
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import time

def load_songlist(filepath):
    songs = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                title = parts[0].strip()
                artist = parts[1].strip()
                # Handle the weird numbering at the beginning of some files
                if title.startswith('"') and title.endswith('"'):
                    title = title.replace('"', '')
                songs.append({"Title": title, "Artist": artist})
    return songs

def init_spotify_client():
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("Warning: SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET environment variables not set.")
        print("Spotify API fallback will be disabled.")
        return None

    try:
        client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        # Test connection
        sp.search(q="test", limit=1)
        print("Successfully authenticated with Spotify API.")
        return sp
    except Exception as e:
        print(f"Failed to authenticate with Spotify API: {e}")
        return None

def get_spotify_data(sp, title, artist):
    if not sp:
        return None

    query = f"track:{title} artist:{artist}"
    try:
        results = sp.search(q=query, type='track', limit=1)
        if results and results['tracks']['items']:
            track = results['tracks']['items'][0]
            track_id = track['id']

            # Fetch audio features
            features = sp.audio_features([track_id])
            if features and features[0]:
                feat = features[0]

                # Approximate mapping for moods based on valence and energy
                valence = feat.get('valence', 0)
                energy = feat.get('energy', 0)

                is_happy = "Yes" if valence > 0.6 and energy > 0.5 else ""
                is_sad = "Yes" if valence < 0.4 and energy < 0.5 else ""
                is_aggressive = "Yes" if energy > 0.8 else ""
                is_relaxed = "Yes" if energy < 0.4 else ""
                is_party = "Yes" if feat.get('danceability', 0) > 0.7 and energy > 0.6 else ""

                return {
                    "Genre": "Spotify API (Unknown)", # Search API doesn't return genre directly on track
                    "BPM": str(round(feat.get('tempo', 0), 1)),
                    "Energy_Level": "High" if energy > 0.7 else ("Low" if energy < 0.4 else "Medium"),
                    "Danceability": str(round(feat.get('danceability', 0), 2)),
                    "Key": str(feat.get('key', '')),
                    "Psychoacoustics_Moods": {
                        "Happy": is_happy,
                        "Sad": is_sad,
                        "Aggressive": is_aggressive,
                        "Relaxed": is_relaxed,
                        "Party": is_party
                    },
                    "Vibe": "",
                    "Source": "Spotify API Fallback"
                }
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 429:
            print("Spotify API rate limit reached. Backing off...")
            time.sleep(5)
        else:
             print(f"Spotify API error for {title} - {artist}: {e}")
    except Exception as e: # noqa: BLE001
        print(f"Error fetching data from Spotify for {title} - {artist}: {e}")

    return None

def analyze_acoustics(songlist_path, db_path, output_path):
    print(f"Loading songlist from {songlist_path}")
    target_songs = load_songlist(songlist_path)

    print(f"Loaded {len(target_songs)} target songs. Cross-referencing with DB...")

    analysis_results = []

    sp = init_spotify_client()
    api_calls = 0

    with open(db_path, 'r', encoding='utf-8-sig') as f:
        # Read the entire DB into memory for faster searching since it's relatively small
        # and we need to do O(N*M) matching
        db_rows = list(csv.DictReader(f))

        for target in target_songs:
            target_title = target["Title"].lower()
            target_artist = target["Artist"].lower()

            matched = False
            for row in db_rows:
                db_title = row.get("Title", "").strip().lower()
                db_artist = row.get("Artist", "").strip().lower()

                # Basic matching - could be improved with fuzzy matching if needed
                if target_title == db_title and target_artist == db_artist:

                    # Check if we have meaningful acoustic data
                    bpm = row.get("Spotify BPM") or row.get("BPM")
                    energy = row.get("Spotify Energy Level") or row.get("Energy")

                    if bpm or energy:
                        acoustics = {
                            "Requested_Title": target["Title"],
                            "Requested_Artist": target["Artist"],
                            "Matched_Title": row.get("Title"),
                            "Matched_Artist": row.get("Artist"),
                            "Genre": row.get("Genre") or row.get("Spotify Genre"),
                            "BPM": bpm,
                            "Energy_Level": energy,
                            "Danceability": row.get("Spotify Danceability"),
                            "Key": row.get("Spotify Key Full"),
                            "Psychoacoustics_Moods": {
                                "Happy": row.get("Spotify Mood Happy"),
                                "Sad": row.get("Spotify Mood Sad"),
                                "Aggressive": row.get("Spotify Mood Aggressive"),
                                "Relaxed": row.get("Spotify Mood Relaxed"),
                                "Party": row.get("Spotify Mood Party")
                            },
                            "Vibe": row.get("Vibe") or row.get("Spotify Vibe"),
                            "Source": "Local DB"
                        }
                        analysis_results.append(acoustics)
                        matched = True
                        break

            # If no match in DB, or match had no data, try Spotify API
            if not matched and sp:
                if api_calls > 0 and api_calls % 10 == 0:
                     time.sleep(1) # Simple rate limiting

                print(f"Falling back to Spotify API for: {target['Title']} - {target['Artist']}")
                spotify_data = get_spotify_data(sp, target["Title"], target["Artist"])
                api_calls += 1

                if spotify_data:
                    spotify_data["Requested_Title"] = target["Title"]
                    spotify_data["Requested_Artist"] = target["Artist"]
                    spotify_data["Matched_Title"] = target["Title"] # Assuming perfect match for structure
                    spotify_data["Matched_Artist"] = target["Artist"]
                    analysis_results.append(spotify_data)

    # Ensure export directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "total_requested": len(target_songs),
            "total_matched": len(analysis_results),
            "results": analysis_results
        }, f, indent=4)

    print(f"Analysis complete. Matched {len(analysis_results)} songs out of {len(target_songs)}.")
    print(f"Results saved to {output_path}")

if __name__ == "__main__":
    songlist_file = "songlist.txt"
    db_file = "data/processed/Main_Song_Database.csv"
    output_file = "data/exports/jules/acoustics_report.json"

    if not os.path.exists(songlist_file):
        print(f"Error: {songlist_file} not found.")
    elif not os.path.exists(db_file):
         print(f"Error: {db_file} not found.")
    else:
        analyze_acoustics(songlist_file, db_file, output_file)

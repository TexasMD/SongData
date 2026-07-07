import pandas as pd
import sqlite3
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]

# Inputs from the active CSV database
V2_DIR = PROJECT_DIR / "SongDB_v2"
RECORDINGS_CSV = V2_DIR / "recordings.csv"
SONGS_CSV = V2_DIR / "songs.csv"
EXT_LINKS_CSV = V2_DIR / "external_links.csv"
PLAYLIST_MEMBERSHIP_CSV = V2_DIR / "playlist_membership.csv"

# Output strictly limited to the staging/jules directory (Proof of Concept)
STAGING_DIR = PROJECT_DIR / "data" / "staging" / "jules"
DB_PATH = STAGING_DIR / "poc.sqlite"

def create_sqlite_poc():
    print(f"Generating SQLite Proof of Concept at: {DB_PATH}")

    # Ensure staging directory exists
    os.makedirs(STAGING_DIR, exist_ok=True)

    # Remove existing POC if it exists to start fresh
    if DB_PATH.exists():
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)

    try:
        # Load and write Recordings
        if RECORDINGS_CSV.exists():
            print("Loading recordings.csv...")
            df_rec = pd.read_csv(RECORDINGS_CSV, encoding='utf-8-sig', dtype=str)
            df_rec.to_sql("recordings", conn, if_exists="replace", index=False)
            print(f" -> Inserted {len(df_rec)} rows into 'recordings' table.")

        # Load and write Songs
        if SONGS_CSV.exists():
            print("Loading songs.csv...")
            df_songs = pd.read_csv(SONGS_CSV, encoding='utf-8-sig', dtype=str)
            df_songs.to_sql("songs", conn, if_exists="replace", index=False)
            print(f" -> Inserted {len(df_songs)} rows into 'songs' table.")

        # Load and write External Links
        if EXT_LINKS_CSV.exists():
            print("Loading external_links.csv...")
            df_ext = pd.read_csv(EXT_LINKS_CSV, encoding='utf-8-sig', dtype=str)
            df_ext.to_sql("external_links", conn, if_exists="replace", index=False)
            print(f" -> Inserted {len(df_ext)} rows into 'external_links' table.")

        # Load and write Playlist Membership
        if PLAYLIST_MEMBERSHIP_CSV.exists():
            print("Loading playlist_membership.csv...")
            df_play = pd.read_csv(PLAYLIST_MEMBERSHIP_CSV, encoding='utf-8-sig', dtype=str)
            df_play.to_sql("playlist_membership", conn, if_exists="replace", index=False)
            print(f" -> Inserted {len(df_play)} rows into 'playlist_membership' table.")

        print("\nSQLite PoC generation complete!")
        print("Note: This DB is strictly for export/viewing. The CSV remains the Source of Truth.")

    except Exception as e:
        print(f"Error generating SQLite DB: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_sqlite_poc()

import sys
import sqlite3
import time
from pathlib import Path

# Ensure root directory is in sys.path
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.db_access import DEFAULT_DB_PATH
from src.cover_scraper import scrape_covers

def get_db_connection():
    return sqlite3.connect(DEFAULT_DB_PATH)

def init_daemon():
    conn = get_db_connection()
    # Create a table to track which recordings have been processed
    conn.execute('''
        CREATE TABLE IF NOT EXISTS antigravity_cover_daemon_log (
            recording_id TEXT PRIMARY KEY,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            covers_found INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def run_daemon(batch_size: int = 25):
    print(f"Starting cover daemon (batch size: {batch_size})...")
    init_daemon()
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    
    # Get recordings that haven't been checked yet
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT r.recording_id, r.title, r.artist 
        FROM recordings r
        LEFT JOIN antigravity_cover_daemon_log log ON r.recording_id = log.recording_id
        WHERE log.recording_id IS NULL
        LIMIT {batch_size}
    ''')
    
    recordings_to_check = cursor.fetchall()
    
    if not recordings_to_check:
        print("No new recordings to check.")
        return
        
    for rec in recordings_to_check:
        rec_id = rec["recording_id"]
        title = rec["title"]
        artist = rec["artist"]
        
        print(f"Checking '{title}' by '{artist}'...")
        
        try:
            covers = scrape_covers(title, artist)
            
            if covers:
                for cover in covers:
                    conn.execute(
                        "INSERT INTO antigravity_cover_candidates (original_recording_id, title, artist, musicbrainz_recording_id, source) VALUES (?, ?, ?, ?, ?)",
                        (rec_id, cover["title"], cover["artist"], cover["musicbrainz_recording_id"], "MusicBrainz")
                    )
                
            conn.execute(
                "INSERT INTO antigravity_cover_daemon_log (recording_id, covers_found) VALUES (?, ?)",
                (rec_id, len(covers))
            )
            conn.commit()
            print(f"  -> Found {len(covers)} covers.")
            
        except Exception as e:
            print(f"  -> Error processing {rec_id}: {e}")
            
        # Add a sleep to be extremely polite to MusicBrainz
        time.sleep(2)
        
    conn.close()
    print("Daemon batch completed.")

if __name__ == "__main__":
    run_daemon()

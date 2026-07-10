import sys
import sqlite3
import time
from pathlib import Path

import pandas as pd

# Ensure root directory is in sys.path
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.db_access import DEFAULT_DB_PATH
from src.cover_scraper import scrape_covers
from src.source_checks import (
    ensure_source_query_checks_table,
    export_source_query_checks_csv,
    record_source_query_check,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANTIGRAVITY_STAGE_DIR = PROJECT_ROOT / "data" / "staging" / "antigravity"
CSV_PATH = ANTIGRAVITY_STAGE_DIR / "cover_relationship_candidates.csv"
SOURCE_CHECKS_CSV_PATH = ANTIGRAVITY_STAGE_DIR / "source_query_checks.csv"

def get_db_connection():
    return sqlite3.connect(DEFAULT_DB_PATH)

def ensure_cover_candidates_table(conn):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS antigravity_cover_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_recording_id TEXT,
            title TEXT,
            artist TEXT,
            original_title TEXT,
            original_artist TEXT,
            original_year TEXT,
            musicbrainz_recording_id TEXT,
            source TEXT
        )
    ''')

    existing_columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(antigravity_cover_candidates)")
    }
    for column_name, column_type in (
        ("original_title", "TEXT"),
        ("original_artist", "TEXT"),
        ("original_year", "TEXT"),
    ):
        if column_name not in existing_columns:
            conn.execute(
                f"ALTER TABLE antigravity_cover_candidates ADD COLUMN {column_name} {column_type}"
            )

def ensure_candidate_last_checked_columns(conn):
    existing_columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(antigravity_cover_candidates)")
    }
    for column_name in (
        "musicbrainz_last_checked_at",
        "coverinfo_last_checked_at",
        "secondhandsongs_last_checked_at",
        "whosampled_last_checked_at",
    ):
        if column_name not in existing_columns:
            conn.execute(
                f"ALTER TABLE antigravity_cover_candidates ADD COLUMN {column_name} TEXT"
            )

def init_daemon():
    conn = get_db_connection()
    ensure_cover_candidates_table(conn)
    ensure_candidate_last_checked_columns(conn)
    ensure_source_query_checks_table(conn)
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
        SELECT r.recording_id, r.title, r.artist, r.release_year
        FROM recordings r
        LEFT JOIN antigravity_cover_daemon_log log ON r.recording_id = log.recording_id
        WHERE log.recording_id IS NULL
        LIMIT {batch_size}
    ''')
    
    recordings_to_check = cursor.fetchall()

    if not recordings_to_check:
        print("No new recordings to check.")

    for rec in recordings_to_check:
        rec_id = rec["recording_id"]
        title = rec["title"]
        artist = rec["artist"]
        original_year = "" if rec["release_year"] is None else str(rec["release_year"])
        source_checks: dict[str, str] = {}

        def on_source_checked(source: str, query_kind: str, query_url: str, result_count: int | None, checked_at: str) -> None:
            source_checks[source] = checked_at
            record_source_query_check(
                conn,
                recording_id=rec_id,
                source=source,
                query_kind=query_kind,
                last_query_url=query_url,
                last_result_count=result_count,
                checked_at=checked_at,
            )
        
        print(f"Checking '{title}' by '{artist}'...")
        
        try:
            covers = scrape_covers(title, artist, original_year, on_source_checked=on_source_checked)
            
            if covers:
                for cover in covers:
                    conn.execute(
                        """
                        INSERT INTO antigravity_cover_candidates
                        (original_recording_id, title, artist, original_title, original_artist, original_year, musicbrainz_recording_id, source, musicbrainz_last_checked_at, coverinfo_last_checked_at, secondhandsongs_last_checked_at, whosampled_last_checked_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            rec_id,
                            cover["title"],
                            cover["artist"],
                            cover.get("original_title", title),
                            cover.get("original_artist", artist),
                            cover.get("original_year", original_year),
                            cover.get("musicbrainz_recording_id"),
                            cover.get("source", ""),
                            source_checks.get("MusicBrainz", ""),
                            source_checks.get("cover.info", ""),
                            source_checks.get("SecondHandSongs", ""),
                            source_checks.get("WhoSampled", ""),
                        )
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

    ANTIGRAVITY_STAGE_DIR.mkdir(parents=True, exist_ok=True)
    pd.read_sql_query("SELECT * FROM antigravity_cover_candidates", conn).to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"Wrote CSV snapshot to {CSV_PATH}")
    export_source_query_checks_csv(conn, SOURCE_CHECKS_CSV_PATH)
    print(f"Wrote source query log to {SOURCE_CHECKS_CSV_PATH}")

    conn.close()
    print("Daemon batch completed.")

if __name__ == "__main__":
    run_daemon()

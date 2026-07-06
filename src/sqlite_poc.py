import sqlite3
import os
from typing import List, Dict, Any

DB_PATH = "data/staging/jules/poc.db"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS songs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            version TEXT,
            spotify_id TEXT,
            musicbrainz_id TEXT,
            bpm REAL,
            song_key TEXT
        )
    ''')
    conn.commit()
    conn.close()

def insert_records(records: List[Dict[str, Any]]):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for record in records:
        # Assuming stable_id is injected or generated elsewhere, doing a basic one here for POC if missing
        from .stable_id import generate_stable_id
        stable_id = record.get("StableID") or generate_stable_id(record.get("Title", ""), record.get("Artist", ""), record.get("Version", ""))

        cursor.execute('''
            INSERT OR REPLACE INTO songs (id, title, artist, version, spotify_id, musicbrainz_id, bpm, song_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            stable_id,
            record.get("Title", ""),
            record.get("Artist", ""),
            record.get("Version", ""),
            record.get("SpotifyID", ""),
            record.get("MusicBrainzID", ""),
            record.get("BPM"),
            record.get("Key", "")
        ))

    conn.commit()
    conn.close()

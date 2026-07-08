import sqlite3
import contextlib
import os
from typing import List, Dict, Any
from .stable_id import generate_stable_id
from .config import paths

DB_PATH = str(paths().sqlite_poc_path)

def init_db(db_path: str = DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        with conn:
            cursor = conn.cursor()

            # 1. Recordings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recordings (
                    recording_id TEXT PRIMARY KEY,
                    song_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    version TEXT,
                    spotify_track_id TEXT,
                    musicbrainz_id TEXT,
                    isrc TEXT
                )
            """)

            # 2. External Links
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS external_links (
                    recording_id TEXT PRIMARY KEY,
                    shs_link TEXT,
                    whosampled_link TEXT,
                    ug_link TEXT,
                    video_link TEXT,
                    FOREIGN KEY (recording_id) REFERENCES recordings(recording_id)
                )
            """)

            # 3. Performance Metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metadata (
                    recording_id TEXT PRIMARY KEY,
                    bpm REAL,
                    key TEXT,
                    tuning TEXT,
                    capo INTEGER,
                    difficulty INTEGER,
                    vocal_range TEXT,
                    instrumentation TEXT,
                    arrangement TEXT,
                    FOREIGN KEY (recording_id) REFERENCES recordings(recording_id)
                )
            """)

            # 4. Tags & Playlists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags_playlists (
                    recording_id TEXT PRIMARY KEY,
                    mood TEXT,
                    event TEXT,
                    situation TEXT,
                    setlist_role TEXT,
                    energy INTEGER,
                    playlists TEXT,
                    FOREIGN KEY (recording_id) REFERENCES recordings(recording_id)
                )
            """)

            # Create a unified view for the UI
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS view_search AS
                SELECT
                    r.recording_id,
                    r.song_id,
                    r.title,
                    r.artist,
                    r.version,
                    r.spotify_track_id,
                    r.musicbrainz_id,
                    pm.bpm,
                    pm.key,
                    pm.tuning,
                    pm.difficulty,
                    tp.mood,
                    tp.event,
                    tp.playlists,
                    el.shs_link,
                    el.ug_link
                FROM recordings r
                LEFT JOIN performance_metadata pm ON r.recording_id = pm.recording_id
                LEFT JOIN tags_playlists tp ON r.recording_id = tp.recording_id
                LEFT JOIN external_links el ON r.recording_id = el.recording_id
            """)


def insert_v2_records(records: List[Dict[str, Any]], db_path: str = DB_PATH):
    init_db(db_path)
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        with conn:
            cursor = conn.cursor()

            recordings_data = []
            external_links_data = []
            performance_metadata_data = []
            tags_playlists_data = []

            for record in records:
                title = record.get("Title", "")
                artist = record.get("Artist", "")
                version = record.get("Version", "")

                recording_id = record.get("Recording ID") or generate_stable_id(
                    title, artist, version
                )
                song_id = record.get("Song ID") or generate_stable_id(title, artist, "")

                recordings_data.append((
                    recording_id,
                    song_id,
                    title,
                    artist,
                    version,
                    record.get("Spotify Track ID"),
                    record.get("MusicBrainz ID"),
                    record.get("ISRC")
                ))

                external_links_data.append((
                    recording_id,
                    record.get("SHS Link"),
                    record.get("WhoSampled Link"),
                    record.get("UG Link"),
                    record.get("Video Link")
                ))

                performance_metadata_data.append((
                    recording_id,
                    record.get("BPM"),
                    record.get("Key"),
                    record.get("Tuning"),
                    record.get("Capo"),
                    record.get("Difficulty"),
                    record.get("Vocal Range"),
                    record.get("Instrumentation"),
                    record.get("Arrangement")
                ))

                tags_playlists_data.append((
                    recording_id,
                    record.get("Mood"),
                    record.get("Event"),
                    record.get("Situation"),
                    record.get("Setlist Role"),
                    record.get("Energy"),
                    record.get("Playlists")
                ))

            # Recordings
            cursor.executemany('''
                INSERT OR REPLACE INTO recordings (recording_id, song_id, title, artist, version, spotify_track_id, musicbrainz_id, isrc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', recordings_data)

            # External Links
            cursor.executemany('''
                INSERT OR REPLACE INTO external_links (recording_id, shs_link, whosampled_link, ug_link, video_link)
                VALUES (?, ?, ?, ?, ?)
            ''', external_links_data)

            # Performance Metadata
            cursor.executemany('''
                INSERT OR REPLACE INTO performance_metadata (recording_id, bpm, key, tuning, capo, difficulty, vocal_range, instrumentation, arrangement)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', performance_metadata_data)

            # Tags & Playlists
            cursor.executemany('''
                INSERT OR REPLACE INTO tags_playlists (recording_id, mood, event, situation, setlist_role, energy, playlists)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', tags_playlists_data)


def insert_records(records: List[Dict[str, Any]]):
    # Backward compatibility for existing poc.db usage if any
    insert_v2_records(records, db_path=DB_PATH)

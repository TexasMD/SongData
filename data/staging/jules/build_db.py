import sqlite3
import csv
from pathlib import Path

# Schema definitions mapping SQL Column -> CSV Header -> SQL Data Type
SONGS_SCHEMA = [
    ("song_id", "Song ID", "TEXT PRIMARY KEY"),
    ("canonical_title", "Canonical Title", "TEXT"),
    ("canonical_artist", "Canonical Artist", "TEXT"),
    ("musicbrainz_work_id", "MusicBrainz Work ID", "TEXT"),
    ("primary_recording_id", "Primary Recording ID", "TEXT"),
    ("preferred_primary_release", "Preferred Primary Release", "TEXT"),
    ("first_published_year", "First Published Year", "INTEGER"),
    ("genre_family", "Genre Family", "TEXT"),
    ("default_mood_tags", "Default Mood Tags", "TEXT"),
    ("default_event_tags", "Default Event Tags", "TEXT"),
    ("default_situation_tags", "Default Situation Tags", "TEXT"),
    ("notes", "Notes", "TEXT"),
]

RECORDINGS_SCHEMA = [
    ("recording_id", "Recording ID", "TEXT PRIMARY KEY"),
    ("song_id", "Song ID", "TEXT REFERENCES songs(song_id)"),
    ("main_db_csv_line", "Main DB CSV Line", "TEXT"),
    ("title", "Title", "TEXT"),
    ("canonical_title", "Canonical Title", "TEXT"),
    ("version", "Version", "TEXT"),
    ("artist", "Artist", "TEXT"),
    ("original_artist", "Original Artist", "TEXT"),
    ("covering_artist", "Covering Artist", "TEXT"),
    ("cover_song", "Cover Song", "TEXT"),
    ("album", "Album", "TEXT"),
    ("alternate_albums", "Alternate Albums", "TEXT"),
    ("release_year", "Release Year", "INTEGER"),
    ("duration", "Duration", "TEXT"),
    ("duration_ms", "Duration ms", "INTEGER"),
    ("genre", "Genre", "TEXT"),
    ("genre_detail", "Genre Detail", "TEXT"),
    ("bpm", "BPM", "REAL"),
    ("bpm_source", "BPM Source", "TEXT"),
    ("key", "Key", "TEXT"),
    ("key_source", "Key Source", "TEXT"),
    ("scale", "Scale", "TEXT"),
    ("time_signature", "Time Signature", "TEXT"),
    ("tuning", "Tuning", "TEXT"),
    ("capo", "Capo", "TEXT"),
    ("guitar_difficulty", "Guitar Difficulty", "TEXT"),
    ("bass_difficulty", "Bass Difficulty", "TEXT"),
    ("drum_difficulty", "Drum Difficulty", "TEXT"),
    ("vocal_range", "Vocal Range", "TEXT"),
    ("instrumentation", "Instrumentation", "TEXT"),
    ("main_riff_hook", "Main Riff/Hook", "TEXT"),
    ("solo", "Solo", "TEXT"),
    ("arrangement_notes", "Arrangement Notes", "TEXT"),
    ("mood_tags", "Mood Tags", "TEXT"),
    ("event_tags", "Event Tags", "TEXT"),
    ("situation_tags", "Situation Tags", "TEXT"),
    ("setlist_role", "Setlist Role", "TEXT"),
    ("crowd_energy", "Crowd Energy", "TEXT"),
    ("danceability", "Danceability", "TEXT"),
    ("vocal_type", "Vocal Type", "TEXT"),
    ("explicit_lyric_risk", "Explicit/Lyric Risk", "TEXT"),
    ("playlists", "Playlists", "TEXT"),
    ("source_files", "Source Files", "TEXT"),
    ("spotify_track_id", "Spotify Track ID", "TEXT"),
    ("legacy_spotify_id", "Legacy Spotify ID", "TEXT"),
    ("spotify_isrc", "Spotify ISRC", "TEXT"),
    ("spotify_popularity", "Spotify Popularity", "INTEGER"),
    ("spotify_verified", "Spotify Verified", "TEXT"),
    ("spotify_match_method", "Spotify Match Method", "TEXT"),
    ("spotify_match_score", "Spotify Match Score", "REAL"),
    ("musicbrainz_recording_id", "MusicBrainz Recording ID", "TEXT"),
    ("musicbrainz_verified", "MusicBrainz Verified", "TEXT"),
    ("discogs_verified", "Discogs Verified", "TEXT"),
    ("itunes_verified", "iTunes Verified", "TEXT"),
    ("secondhandsongs_search_url", "SecondHandSongs Search URL", "TEXT"),
    ("secondhandsongs_verified_url", "SecondHandSongs Verified URL", "TEXT"),
    ("secondhandsongs_link_status", "SecondHandSongs Link Status", "TEXT"),
    ("whosampled_search_url", "WhoSampled Search URL", "TEXT"),
    ("whosampled_verified_url", "WhoSampled Verified URL", "TEXT"),
    ("whosampled_link_status", "WhoSampled Link Status", "TEXT"),
    ("ultimate_guitar_search_url", "Ultimate Guitar Search URL", "TEXT"),
    ("ultimate_guitar_official_tab_url", "Ultimate Guitar Official Tab URL", "TEXT"),
    ("ultimate_guitar_best_tab_url", "Ultimate Guitar Best Tab URL", "TEXT"),
    ("ultimate_guitar_tab_preference", "Ultimate Guitar Tab Preference", "TEXT"),
    ("ultimate_guitar_tab_status", "Ultimate Guitar Tab Status", "TEXT"),
    ("duplicate_merge_notes", "Duplicate Merge Notes", "TEXT"),
    ("data_quality_notes", "Data Quality Notes", "TEXT")
]

EXTERNAL_LINKS_SCHEMA = [
    ("recording_id", "Recording ID", "TEXT REFERENCES recordings(recording_id)"),
    ("song_id", "Song ID", "TEXT REFERENCES songs(song_id)"),
    ("site", "Site", "TEXT"),
    ("search_url", "Search URL", "TEXT"),
    ("verified_url", "Verified URL", "TEXT"),
    ("link_type", "Link Type", "TEXT"),
    ("link_status", "Link Status", "TEXT"),
    ("preferred_match_rule", "Preferred Match Rule", "TEXT"),
    ("last_checked", "Last Checked", "TEXT"),
    ("notes", "Notes", "TEXT")
]

PLAYLIST_MEMBERSHIP_SCHEMA = [
    ("recording_id", "Recording ID", "TEXT REFERENCES recordings(recording_id)"),
    ("song_id", "Song ID", "TEXT REFERENCES songs(song_id)"),
    ("playlist", "Playlist", "TEXT"),
    ("source", "Source", "TEXT"),
    ("notes", "Notes", "TEXT")
]

TAG_OPTIONS_SCHEMA = [
    ("category", "Category", "TEXT"),
    ("value", "Value", "TEXT")
]

TABLES = {
    # Songs needs to be created first because recordings reference it
    "songs": {"schema": SONGS_SCHEMA, "csv": "songs.csv", "auto_id": False},
    "recordings": {"schema": RECORDINGS_SCHEMA, "csv": "recordings.csv", "auto_id": False},
    "external_links": {"schema": EXTERNAL_LINKS_SCHEMA, "csv": "external_links.csv", "auto_id": True},
    "playlist_membership": {"schema": PLAYLIST_MEMBERSHIP_SCHEMA, "csv": "playlist_membership.csv", "auto_id": True},
    "tag_options": {"schema": TAG_OPTIONS_SCHEMA, "csv": "tag_options.csv", "auto_id": True}
}

def create_and_populate_db(base_dir: Path):
    db_path = base_dir / "music.sqlite"

    # Overwrite DB if it already exists
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    # Enable foreign key constraint checking
    conn.execute("PRAGMA foreign_keys = ON;")

    for table_name, info in TABLES.items():
        schema_def = info["schema"]

        # Build CREATE TABLE statement
        columns_sql = []
        if info["auto_id"]:
            columns_sql.append("id INTEGER PRIMARY KEY AUTOINCREMENT")

        for sql_col, _, sql_type in schema_def:
            columns_sql.append(f"{sql_col} {sql_type}")

        create_stmt = f"CREATE TABLE {table_name} (\n    {', '.join(columns_sql)}\n);"
        conn.execute(create_stmt)

        # Read and insert CSV data
        csv_file = base_dir / info["csv"]
        if csv_file.exists():
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                sql_cols = [s[0] for s in schema_def]
                csv_cols = [s[1] for s in schema_def]

                placeholders = ", ".join(["?"] * len(sql_cols))
                insert_stmt = f"INSERT INTO {table_name} ({', '.join(sql_cols)}) VALUES ({placeholders})"

                data_batch = []
                for row in reader:
                    row_data = []
                    for sql_col, csv_col, sql_type in schema_def:
                        val = row.get(csv_col, "")
                        if val is not None:
                            val = val.strip()

                        if not val:
                            val = None
                        elif "INTEGER" in sql_type and val is not None:
                            try:
                                val = int(float(val)) # Support strings like '1995.0'
                            except ValueError:
                                val = None
                        elif "REAL" in sql_type and val is not None:
                            try:
                                val = float(val)
                            except ValueError:
                                val = None

                        row_data.append(val)
                    data_batch.append(tuple(row_data))

                conn.executemany(insert_stmt, data_batch)
                print(f"Inserted {len(data_batch)} rows into {table_name}")
        else:
            print(f"Warning: {csv_file.name} not found. Skipped data import for {table_name}.")

    # Create strategic indices to optimize likely query patterns
    indices = [
        "CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(canonical_artist);",
        "CREATE INDEX IF NOT EXISTS idx_recordings_song ON recordings(song_id);",
        "CREATE INDEX IF NOT EXISTS idx_recordings_artist ON recordings(artist);",
        "CREATE INDEX IF NOT EXISTS idx_recordings_title ON recordings(title);",
        "CREATE INDEX IF NOT EXISTS idx_ext_links_rec ON external_links(recording_id);",
        "CREATE INDEX IF NOT EXISTS idx_ext_links_song ON external_links(song_id);",
        "CREATE INDEX idx_playlist_rec ON playlist_membership(recording_id);"
    ]
    for idx_stmt in indices:
        conn.execute(idx_stmt)

    conn.commit()
    conn.close()
    print(f"Database built successfully at {db_path}")

if __name__ == "__main__":
    work_dir = Path(r"D:\Music\MusicDB\data\staging\jules")
    create_and_populate_db(work_dir)

#!/usr/bin/env python3
import argparse
import csv
import sqlite3
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import paths

# Columns written to CSV (one-line-per-cell to satisfy CSV import)
CSV_COLUMNS = [
    "filepath",  # path to audio file (preferred) or fallback URL/track id
    "title",  # performance_title
    "artist",  # performing artist name
    "album",  # album title (if available)
    "tracknumber",  # track number on album (if available)
    "discnumber",  # disc number (if available)
    "date",  # release year (YYYY)
    "genre",  # genre (if available)
    "composer",  # author_writer_names
    "isrc",  # ISRC code
    "work_title",  # underlying work title
    "original_artist",  # original artist name (denormalized)
    "is_original_release",  # 1 or 0
    "years_after_original",  # integer or empty
    "source_db",  # source of relationship (SHS, COVERINFO, etc.)
    "platform_ids",  # concatenated platform ids/urls (spotify:id;itunes:id;preview_url)
    "album_artist",  # album artist (if different)
]


def export_ql_csv(db_path: Path, output_path: Path):
    """Export database metadata to a Quod Libet compatible CSV."""
    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check available views/tables
    cursor.execute(
        "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view')"
    )
    objects = {row["name"]: row["type"] for row in cursor.fetchall()}

    if "v_unified_song_performances" in objects:
        print("Detected 'v_unified_song_performances' view. Using unified schema.")
        query = """
            SELECT
              COALESCE(v.filepath, '') AS filepath,
              v.performance_title AS title,
              v.performing_artist_name AS artist,
              COALESCE(v.album_title, '') AS album,
              COALESCE(v.track_number, '') AS tracknumber,
              COALESCE(v.disc_number, '') AS discnumber,
              COALESCE(v.performance_release_year, '') AS date,
              COALESCE(v.genre, '') AS genre,
              COALESCE(v.author_writer_names, '') AS composer,
              COALESCE(v.isrc, '') AS isrc,
              COALESCE(v.original_work_title, '') AS work_title,
              COALESCE(v.original_artist_name, '') AS original_artist,
              COALESCE(v.is_original_release, 0) AS is_original_release,
              COALESCE(v.years_after_original, '') AS years_after_original,
              COALESCE(v.source_db, '') AS source_db,
              COALESCE(v.platform_ids, '') AS platform_ids,
              COALESCE(v.album_artist, '') AS album_artist
            FROM v_unified_song_performances v
        """
    elif "recordings" in objects:
        print("Detected 'recordings' table. Using local fallback schema mapping.")
        # Map local recordings schema into the requested exact columns.
        query = """
            SELECT
                COALESCE(r.source_files, '') AS filepath,
                r.title AS title,
                r.artist AS artist,
                COALESCE(r.album, '') AS album,
                '' AS tracknumber,
                '' AS discnumber,
                COALESCE(r.release_year, '') AS date,
                COALESCE(r.genre, '') AS genre,
                '' AS composer,
                COALESCE(r.spotify_isrc, '') AS isrc,
                COALESCE(s.canonical_title, r.cover_song, '') AS work_title,
                COALESCE(r.original_artist, '') AS original_artist,
                CASE WHEN r.cover_song IS NULL OR r.cover_song = '' THEN 1 ELSE 0 END AS is_original_release,
                '' AS years_after_original,
                '' AS source_db,
                COALESCE(r.spotify_track_id, '') AS platform_ids,
                '' AS album_artist
            FROM recordings r
            LEFT JOIN songs s ON r.song_id = s.song_id
        """
    else:
        print(
            "Error: Could not find a suitable table or view for export.",
            file=sys.stderr,
        )
        sys.exit(1)

    cursor.execute(query)
    rows = cursor.fetchall()

    if not rows:
        print("No records found to export.")
        sys.exit(0)

    print(f"Exporting {len(rows)} records to {output_path}...")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))

    print("Export complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Export MusicDB metadata to a Quod Libet compatible CSV."
    )
    # Default to music.sqlite in the staging area based on exploration
    default_db = paths().staging_dir / "jules" / "music.sqlite"
    default_out = paths().exports_dir / "ql_export.csv"

    parser.add_argument(
        "--db",
        type=Path,
        default=default_db,
        help=f"Path to the input SQLite database. (default: {default_db})",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=default_out,
        help=f"Path to the output CSV file. (default: {default_out})",
    )

    args = parser.parse_args()

    export_ql_csv(args.db, args.out)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import csv
import sqlite3
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import paths


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
                performance_title AS title,
                performing_artist_name AS artist,
                performance_release_year AS date,
                original_artist_name AS originalartist,
                original_release_year AS originaldate,
                original_work_title AS work,
                isrc,
                mb_artist_id AS musicbrainz_artistid
            FROM v_unified_song_performances
        """
    elif "recordings" in objects:
        print("Detected 'recordings' table. Using local schema.")
        query = """
            SELECT
                r.title AS title,
                r.artist AS artist,
                r.album AS album,
                r.release_year AS date,
                r.original_artist AS originalartist,
                r.version AS version,
                r.genre AS genre,
                r.bpm AS bpm,
                r.key AS key,
                r.mood_tags AS mood,
                s.first_published_year AS originaldate
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

    # Get column names
    fieldnames = rows[0].keys()

    print(f"Exporting {len(rows)} records to {output_path}...")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
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

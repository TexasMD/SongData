"""export-quodlibet command implementation."""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

from src.config import paths


def run(
    *,
    write_enabled: bool = False,
    db_path: Path | None = None,
    out: Path | None = None,
) -> int:
    """Export database metadata to a Quod Libet compatible CSV."""
    if db_path is None:
        db_path = paths().staging_dir / "jules" / "music_metadata_unified.sqlite"
        if not db_path.exists():
            # Fallback to the other common db path
            db_path = paths().staging_dir / "jules" / "music.sqlite"

    if out is None:
        out = paths().exports_dir / "ql_export.csv"

    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}", file=sys.stderr)
        return 1

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(f"file:{db_path.absolute().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view')"
    )
    objects = {row["name"]: row["type"] for row in cursor.fetchall()}

    if "performances" in objects and "artists" in objects and "works" in objects:
        print("Detected unified base tables. Using comprehensive join schema.")
        query = """
        SELECT
          COALESCE(e.filepath, e.preview_url, e.platform_track_id, '') AS `~filename`,
          p.performance_title AS title,
          pa.artist_name AS artist,
          COALESCE(al.album_title, '') AS album,
          COALESCE(al.track_number, '') AS tracknumber,
          COALESCE(al.disc_number, '') AS discnumber,
          COALESCE(p.release_year, '') AS date,
          COALESCE(al.genre, '') AS genre,
          COALESCE(w.author_writer_names, '') AS composer,
          COALESCE(p.isrc, '') AS isrc,
          COALESCE(w.work_title, '') AS work_title,
          COALESCE(p.original_artist_name, '') AS original_artist,
          COALESCE(p.is_original_release, 0) AS is_original_release,
          COALESCE(p.years_after_original, '') AS years_after_original,
          COALESCE(cr.source_db, '') AS source_db,
          GROUP_CONCAT(
            DISTINCT COALESCE(e.source || ':' || COALESCE(e.platform_track_id, e.preview_url, ''), '')
          ) AS platform_ids,
          COALESCE(al.album_artist, '') AS album_artist
        FROM performances p
        LEFT JOIN artists pa ON p.performer_artist_id = pa.artist_id
        LEFT JOIN works w ON p.work_id = w.work_id
        LEFT JOIN cover_relationships cr ON cr.cover_performance_id = p.performance_id
        LEFT JOIN albums al ON al.album_id = p.album_id
        LEFT JOIN external_track_ids e ON e.performance_id = p.performance_id
        GROUP BY p.performance_id
        """
    elif "v_unified_song_performances" in objects:
        print("Detected 'v_unified_song_performances' view. Using unified view schema.")
        query = """
        SELECT
            COALESCE(filepath, '') AS `~filename`,
            performance_title AS title,
            performing_artist_name AS artist,
            COALESCE(album_title, '') AS album,
            COALESCE(track_number, '') AS tracknumber,
            COALESCE(disc_number, '') AS discnumber,
            COALESCE(performance_release_year, '') AS date,
            COALESCE(genre, '') AS genre,
            COALESCE(author_writer_names, '') AS composer,
            COALESCE(isrc, '') AS isrc,
            COALESCE(original_work_title, '') AS work_title,
            COALESCE(original_artist_name, '') AS original_artist,
            COALESCE(is_original_release, 0) AS is_original_release,
            COALESCE(years_after_original, '') AS years_after_original,
            COALESCE(source_db, '') AS source_db,
            COALESCE(platform_ids, '') AS platform_ids,
            COALESCE(album_artist, '') AS album_artist
        FROM v_unified_song_performances
        """
    elif "recordings" in objects:
        print("Detected 'recordings' table. Using local fallback schema.")
        query = """
            SELECT
                r.recording_id AS `~filename`,
                r.title AS title,
                r.artist AS artist,
                r.album AS album,
                '' AS tracknumber,
                '' AS discnumber,
                r.release_year AS date,
                r.genre AS genre,
                '' AS composer,
                '' AS isrc,
                '' AS work_title,
                r.original_artist AS original_artist,
                '' AS is_original_release,
                '' AS years_after_original,
                '' AS source_db,
                '' AS platform_ids,
                '' AS album_artist
            FROM recordings r
        """
    else:
        print(
            "Error: Could not find suitable tables or views for export.",
            file=sys.stderr,
        )
        return 1

    try:
        cursor.execute(query)
    except sqlite3.OperationalError as e:
        print(f"Error executing query: {e}", file=sys.stderr)
        # If the base tables join fails (e.g. schema mismatch), try fallback to view
        if "performances" in objects and "v_unified_song_performances" in objects:
            print(
                "Falling back to v_unified_song_performances view...", file=sys.stderr
            )
            query = """
             SELECT
                 COALESCE(filepath, '') AS `~filename`,
                 performance_title AS title,
                 performing_artist_name AS artist,
                 COALESCE(album_title, '') AS album,
                 COALESCE(track_number, '') AS tracknumber,
                 COALESCE(disc_number, '') AS discnumber,
                 COALESCE(performance_release_year, '') AS date,
                 COALESCE(genre, '') AS genre,
                 COALESCE(author_writer_names, '') AS composer,
                 COALESCE(isrc, '') AS isrc,
                 COALESCE(original_work_title, '') AS work_title,
                 COALESCE(original_artist_name, '') AS original_artist,
                 COALESCE(is_original_release, 0) AS is_original_release,
                 COALESCE(years_after_original, '') AS years_after_original,
                 COALESCE(source_db, '') AS source_db,
                 COALESCE(platform_ids, '') AS platform_ids,
                 COALESCE(album_artist, '') AS album_artist
             FROM v_unified_song_performances
             """
            try:
                cursor.execute(query)
            except sqlite3.OperationalError as e2:
                print(f"Fallback view query also failed: {e2}", file=sys.stderr)
                return 1
        else:
            return 1

    rows = cursor.fetchall()

    if not rows:
        print("No records found to export.")
        return 0

    fieldnames = rows[0].keys()

    if not write_enabled:
        print(f"DRY RUN: Would export {len(rows)} records to {out}")
        print("Pass --write to write the file.")
        return 0

    print(f"Exporting {len(rows)} records to {out}...")
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        # We need to map filename correctly if it's empty in legacy mode
        for row in rows:
            row_dict = dict(row)
            if not row_dict.get("~filename"):
                # Make a fallback filename
                isrc_val = row_dict.get("isrc")
                if isrc_val:
                    row_dict["~filename"] = f"ISRC:{isrc_val}"
                else:
                    row_dict["~filename"] = (
                        f"D:\\Music\\Library\\{row_dict.get('artist', 'Unknown')}\\{row_dict.get('title', 'Unknown')}.flac"
                    )
            writer.writerow(row_dict)

    print("Export complete.")
    return 0

#!/usr/bin/env python3
import argparse
import sys
import os
import hashlib
import re
import csv
import sqlite3
from src.quality import generate_quality_report as lib_generate_quality_report, \
    format_report_as_json, format_report_as_markdown

# Add parent directory to path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.normalization import normalize_text, normalize_artist
from src.stable_id import generate_stable_id
from src.duplicates import find_duplicates, group_by_version
from src.schema import validate_record
from src.quality import generate_quality_report
from src.sqlite_poc import insert_records
from src.utils import backup_file, read_csv

INPUT_MOCK_FILE = "data/staging/recordings_mock.csv"

def ensure_mock_file():
    if not os.path.exists(INPUT_MOCK_FILE):
        os.makedirs(os.path.dirname(INPUT_MOCK_FILE), exist_ok=True)
        with open(INPUT_MOCK_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Recording ID", "Song ID", "Title", "Artist", "Version", "Spotify Track ID", "MusicBrainz ID", "BPM", "Key", "Playlists", "Arrangement", "SHS Link"])
            writer.writeheader()
            writer.writerow({
                "Recording ID": "rec1",
                "Song ID": "song1",
                "Title": "Test Song",
                "Artist": "Test Artist",
                "Version": "",
                "Spotify Track ID": "sp1",
                "MusicBrainz ID": "mb1",
                "BPM": "120",
                "Key": "C",
                "Playlists": "Test;Cool",
                "Arrangement": "Acoustic",
                "SHS Link": "http://shs.com/1"
            })

def build_v2(args):
    print(f"build-v2: dry-run={not args.write}")
    if args.write:
        print("Executing write operations for build-v2...")
        # Example logic to trigger SQLite POC
        # insert_records([])

def rebuild(args):
    """
    Rebuilds the compatibility Main_Song_Database.csv from recordings.csv.
    """
    print(f"rebuild: dry-run={not args.write}")

    ensure_mock_file()
    input_file = INPUT_MOCK_FILE
    output_dir = "data/staging/jules"
    output_file = os.path.join(output_dir, "Main_Song_Database.csv")

    if args.write:
        print(f"Rebuilding {output_file} from {input_file}...")
        os.makedirs(output_dir, exist_ok=True)

        # Backup before writing
        if os.path.exists(output_file):
            backup_path = backup_file(output_file)
            if backup_path:
                print(f"Created backup at {backup_path}")

        records_to_export = []
        records = read_csv(input_file)
        for row in records:
            # Mapping as per docs/SCHEMA_V2.md
            comp_row = {
                "Title": row.get("Title", ""),
                "Artist": row.get("Artist", ""),
                "Version": row.get("Version", ""),
                "Spotify ID": row.get("Spotify Track ID", ""),
                "MBID": row.get("MusicBrainz ID", ""),
                "BPM": row.get("BPM", ""),
                "Key": row.get("Key", ""),
                "Playlists": row.get("Playlists", ""),
                "Notes": f"{row.get('Arrangement', '')} {row.get('SHS Link', '')}".strip()
            }
            records_to_export.append(comp_row)

        with open(output_file, 'w', newline='') as f:
            if records_to_export:
                writer = csv.DictWriter(f, fieldnames=records_to_export[0].keys())
                writer.writeheader()
                writer.writerows(records_to_export)

        print(f"Successfully rebuilt {output_file} with {len(records_to_export)} records.")
    else:
        print(f"DRY RUN: Would rebuild {output_file} from {input_file}")
        if os.path.exists(output_file):
            print(f"DRY RUN: Would create backup of {output_file}")

def review_active_vs_staged(args):
    print("review-active-vs-staged...")

def quality_report(args):
    print(f"quality-report: dry-run={not args.write}")

    ensure_mock_file()
    records = read_csv(INPUT_MOCK_FILE)
    report = generate_quality_report(records)

    if args.write:
        export_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'exports')
        os.makedirs(export_dir, exist_ok=True)

        json_file = os.path.join(export_dir, 'quality_report.json')
        md_file = os.path.join(export_dir, 'quality_report.md')

        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Exported JSON report to {json_file}")

        with open(md_file, 'w') as f:
            f.write("# Quality Report\n\n")
            for k, v in report.items():
                f.write(f"- **{k}**: {v}\n")
        print(f"Exported Markdown report to {md_file}")
    else:
        print("DRY RUN: Would export JSON and Markdown reports to data/exports")
        print("Report contents:")
        print(json.dumps(report, indent=2))

def import_playlist(args):
    print(f"import-playlist: dry-run={not args.write}")

def verify(args):
    print("verify...")
    ensure_mock_file()
    records = read_csv(INPUT_MOCK_FILE)
    all_errors = []

    for i, record in enumerate(records):
        errors = validate_record(record)
        if errors:
            all_errors.append(f"Row {i+1} ({record.get('Title', 'Unknown')}): {errors}")

    if all_errors:
        print("Validation errors found:")
        for error in all_errors:
             print(error)
    else:
        print(f"Validation successful for {len(records)} records.")

def export_view(args):
    print("export-view...")
    export_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'exports', 'jules')
    os.makedirs(export_dir, exist_ok=True)
    export_file = os.path.join(export_dir, 'export.json')

    ensure_mock_file()
    records = read_csv(INPUT_MOCK_FILE)

    if args.write:
        with open(export_file, 'w') as f:
            json.dump(records, f, indent=2)
        print(f"Exported to {export_file}")
    else:
        print(f"dry-run: Would export to {export_file}")

def main():
    parser = argparse.ArgumentParser(description="MusicDB CLI")
    parser.add_argument("--write", action="store_true", help="Enable write operations (dry-run by default)")
    parser.add_argument("--db-path", default="data/processed/Main_Song_Database.csv", help="Path to the main CSV database")

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # build-v2
    subparsers.add_parser("build-v2", help="Build V2 of the database")

    # review-active-vs-staged
    subparsers.add_parser("review-active-vs-staged", help="Review active vs staged changes")

    # quality-report
    subparsers.add_parser("quality-report", help="Generate quality reports")

    # import-playlist
    subparsers.add_parser("import-playlist", help="Import a playlist")

    # verify
    subparsers.add_parser("verify", help="Verify the database")

    # export-view
    subparsers.add_parser("export-view", help="Export a view of the database")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if not args.write:
        print("DRY-RUN MODE: No changes will be saved to the database.")

    print(f"Executing command: {args.command}")

    if args.command == "verify":
        verify_database(args.db_path)
    elif args.command == "quality-report":
        generate_quality_report(args.db_path, args.write)
    elif args.command == "build-v2":
        build_v2(args.db_path, args.write)
    elif args.command == "review-active-vs-staged":
        review_active_vs_staged(args.db_path)
    elif args.command == "import-playlist":
        import_playlist(args.db_path, args.write)
    elif args.command == "export-view":
        export_view(args.db_path)

def export_view(db_path):
    export_path = "data/exports/jules/MusicDB_View.csv"
    print(f"Exporting view to {export_path}...")

    # Simple export: all songs with BPM > 100
    with open(db_path, mode='r', encoding='utf-8') as fin, \
         open(export_path, mode='w', encoding='utf-8', newline='') as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            try:
                if row.get("bpm") and int(row["bpm"]) > 100:
                    writer.writerow(row)
            except ValueError:
                continue
    print("Export complete.")

def import_playlist(db_path, write_enabled):
    # This is a mock implementation for the prototype
    print("Importing mock playlist...")
    new_songs = [
        {"song_id": "song_new_1", "title": "New Song 1", "artist": "New Artist 1", "album": "New Album 1"},
        {"song_id": "song_new_2", "title": "New Song 2", "artist": "New Artist 2", "album": "New Album 2"}
    ]

    if not write_enabled:
        print(f"DRY-RUN: Would add {len(new_songs)} songs to {db_path}")
        return

    with open(db_path, mode='a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "song_id", "title", "artist", "album", "spotify_id",
            "musicbrainz_id", "bpm", "key", "musician_performance", "external_links"
        ])
        for song in new_songs:
            writer.writerow(song)
    print(f"Added {len(new_songs)} songs to {db_path}")

def review_active_vs_staged(active_path):
    staged_path = "data/staging/jules/MusicDB.sqlite"
    if not os.path.exists(staged_path):
        print(f"No staged database found at {staged_path}")
        return

    print(f"Comparing active CSV ({active_path}) with staged SQLite ({staged_path})...")

    # Load CSV into a set of IDs
    active_ids = set()
    with open(active_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            active_ids.add(row['song_id'])

    # Load SQLite into a set of IDs
    conn = sqlite3.connect(staged_path)
    cursor = conn.cursor()
    cursor.execute("SELECT song_id FROM songs")
    staged_ids = {row[0] for row in cursor.fetchall()}
    conn.close()

    new_in_staged = staged_ids - active_ids
    missing_in_staged = active_ids - staged_ids

    print(f"  New songs in staged: {len(new_in_staged)}")
    for sid in list(new_in_staged)[:5]:
        print(f"    - {sid}")
    if len(new_in_staged) > 5: print("    ...")

    print(f"  Missing songs in staged: {len(missing_in_staged)}")
    for sid in list(missing_in_staged)[:5]:
        print(f"    - {sid}")
    if len(missing_in_staged) > 5: print("    ...")

def build_v2(csv_path, write_enabled, sqlite_path=None):
    if sqlite_path is None:
        sqlite_path = "data/staging/jules/MusicDB.sqlite"
    if not write_enabled:
        print(f"DRY-RUN: Would rebuild SQLite DB at {sqlite_path}")
        return

    if os.path.exists(sqlite_path):
        print(f"Deleting existing SQLite DB at {sqlite_path} for a clean rebuild...")
        os.remove(sqlite_path)

    print(f"Creating SQLite DB at {sqlite_path}...")
    os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS songs (
            song_id TEXT PRIMARY KEY,
            title TEXT,
            artist TEXT,
            album TEXT,
            spotify_id TEXT,
            musicbrainz_id TEXT,
            bpm INTEGER,
            key TEXT,
            musician_performance TEXT,
            external_links TEXT
        )
    """)

    # Import data from CSV
    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
                INSERT OR REPLACE INTO songs
                (song_id, title, artist, album, spotify_id, musicbrainz_id, bpm, key, musician_performance, external_links)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['song_id'], row['title'], row['artist'], row['album'],
                row['spotify_id'], row['musicbrainz_id'], row['bpm'],
                row['key'], row['musician_performance'], row['external_links']
            ))

    conn.commit()
    conn.close()
    print("SQLite DB created and populated.")

def generate_quality_report(db_path, write_enabled=False, export_dir=None):
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return

    records = []
    with open(db_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    report = lib_generate_quality_report(records)

    print("Quality Report Summary:")
    print(f"  Total songs: {report['total_records']}")
    print(f"  Missing Spotify IDs: {report['missing_spotify_ids']}")
    print(f"  Missing MusicBrainz IDs: {report['missing_musicbrainz_ids']}")
    print(f"  Missing BPM: {report['missing_bpm']}")
    print(f"  Missing Key: {report['missing_key']}")
    print(f"  Missing Musician Performance: {report['missing_musician_performance']}")
    print(f"  Duplicates detected (artist/title groups): {report['duplicate_review_groups']}")
    print(f"  Version groups detected: {report['version_review_groups']}")
    print(f"  Unverified external links: {report['unverified_external_links']}")
    print(f"  Pending Antigravity suggestions: {report['pending_antigravity_suggestions']}")

    if write_enabled:
        if export_dir is None:
            export_dir = "data/exports/jules"
        os.makedirs(export_dir, exist_ok=True)

        json_path = os.path.join(export_dir, "quality_report.json")
        with open(json_path, "w") as f:
            f.write(format_report_as_json(report))
        print(f"JSON report saved to {json_path}")

        md_path = os.path.join(export_dir, "quality_report.md")
        with open(md_path, "w") as f:
            f.write(format_report_as_markdown(report))
        print(f"Markdown report saved to {md_path}")

def verify_database(db_path):
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return

    expected_headers = [
        "song_id", "title", "artist", "album", "spotify_id",
        "musicbrainz_id", "bpm", "key", "musician_performance", "external_links"
    ]

    errors = []
    with open(db_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != expected_headers:
            errors.append(f"Header mismatch. Expected {expected_headers}, got {reader.fieldnames}")

        for i, row in enumerate(reader, start=2):
            if not row.get("song_id"):
                errors.append(f"Line {i}: Missing song_id")
            if not row.get("title"):
                errors.append(f"Line {i}: Missing title")
            if not row.get("artist"):
                errors.append(f"Line {i}: Missing artist")

    if errors:
        print("Verification failed with following errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Verification successful!")

if __name__ == "__main__":
    main()

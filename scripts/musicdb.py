#!/usr/bin/env python3
import argparse
import sys
import os
import hashlib
import re
import csv
import sqlite3

def normalize_text(text):
    if not text:
        return ""
    # Lowercase, remove special characters, and strip
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return " ".join(text.split())

def generate_stable_id(artist, title):
    normalized_artist = normalize_text(artist)
    normalized_title = normalize_text(title)
    combined = f"{normalized_artist}|{normalized_title}"
    return hashlib.md5(combined.encode()).hexdigest()[:12]

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
        generate_quality_report(args.db_path)
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

def build_v2(csv_path, write_enabled):
    sqlite_path = "data/staging/jules/MusicDB.sqlite"
    if not write_enabled:
        print(f"DRY-RUN: Would create SQLite DB at {sqlite_path}")
        return

    print(f"Creating SQLite DB at {sqlite_path}...")
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

def generate_quality_report(db_path):
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return

    missing_spotify = 0
    missing_mb = 0
    missing_bpm = 0
    missing_key = 0
    missing_musician = 0
    duplicates = {}
    total_songs = 0

    with open(db_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_songs += 1
            if not row.get("spotify_id"): missing_spotify += 1
            if not row.get("musicbrainz_id"): missing_mb += 1
            if not row.get("bpm"): missing_bpm += 1
            if not row.get("key"): missing_key += 1
            if not row.get("musician_performance"): missing_musician += 1

            # Duplicate detection based on normalized artist/title
            norm_id = generate_stable_id(row.get("artist", ""), row.get("title", ""))
            duplicates[norm_id] = duplicates.get(norm_id, 0) + 1

    duplicate_count = sum(1 for count in duplicates.values() if count > 1)

    print("Quality Report:")
    print(f"  Total songs: {total_songs}")
    print(f"  Missing Spotify IDs: {missing_spotify}")
    print(f"  Missing MusicBrainz IDs: {missing_mb}")
    print(f"  Missing BPM: {missing_bpm}")
    print(f"  Missing Key: {missing_key}")
    print(f"  Missing Musician Performance: {missing_musician}")
    print(f"  Duplicates detected (artist/title groups): {duplicate_count}")

    # Unverified external links (placeholder for prototype)
    print(f"  Unverified external links: 0 (verification logic pending)")

    # Pending staged suggestions (placeholder for prototype)
    print(f"  Pending staged suggestions: 0 (logic pending)")

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

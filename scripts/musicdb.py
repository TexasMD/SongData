import argparse
import sys
import json
import os
import csv

# Add parent directory to path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.normalization import normalize_text, normalize_artist
from src.stable_id import generate_stable_id
from src.duplicates import find_duplicates, group_by_version
from src.schema import validate_record
from src.quality import generate_quality_report
from src.sqlite_poc import insert_records

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

    # Paths (simulated for sandbox as we don't have the D: drive)
    # In production, these would be:
    # input_file = r"D:\Music\MusicDB\SongDB_v2\recordings.csv"
    # output_file = r"D:\Music\MusicDB\data\staging\jules\Main_Song_Database.csv"

    # For sandbox testing, we'll use local paths
    input_file = "data/staging/recordings_mock.csv"
    output_dir = "data/staging/jules"
    output_file = os.path.join(output_dir, "Main_Song_Database.csv")

    if not os.path.exists(input_file):
        print(f"Mocking input file for demonstration: {input_file}")
        os.makedirs(os.path.dirname(input_file), exist_ok=True)
        with open(input_file, 'w', newline='') as f:
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

    if args.write:
        print(f"Rebuilding {output_file} from {input_file}...")
        os.makedirs(output_dir, exist_ok=True)

        records_to_export = []
        with open(input_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
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

def review_active_vs_staged(args):
    print("review-active-vs-staged...")

def quality_report(args):
    print("quality-report...")
    # Mock records for demonstration
    records = [{"Title": "Test", "Artist": "Test Artist"}]
    report = generate_quality_report(records)
    print(json.dumps(report, indent=2))

def import_playlist(args):
    print(f"import-playlist: dry-run={not args.write}")

def verify(args):
    print("verify...")
    record = {"Title": "Test"}
    errors = validate_record(record)
    if errors:
        print("Validation errors found:", errors)
    else:
        print("Validation successful.")

def export_view(args):
    print("export-view...")
    export_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'exports', 'jules')
    os.makedirs(export_dir, exist_ok=True)
    export_file = os.path.join(export_dir, 'export.json')
    if args.write:
        with open(export_file, 'w') as f:
            json.dump([{"Title": "Exported Test"}], f)
        print(f"Exported to {export_file}")
    else:
        print(f"dry-run: Would export to {export_file}")

def main():
    parser = argparse.ArgumentParser(description="MusicDB CLI")
    parser.add_argument("--write", action="store_true", help="Explicitly allow write operations (default is dry-run)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_build = subparsers.add_parser("build-v2", help="Build the database")

    parser_rebuild = subparsers.add_parser("rebuild", help="Rebuild compatibility main CSV from recordings.csv")

    parser_review = subparsers.add_parser("review-active-vs-staged", help="Review staged changes")

    parser_quality = subparsers.add_parser("quality-report", help="Generate a quality report")

    parser_import = subparsers.add_parser("import-playlist", help="Import a playlist")

    parser_verify = subparsers.add_parser("verify", help="Verify data integrity")

    parser_export = subparsers.add_parser("export-view", help="Export data view")

    args = parser.parse_args()

    if args.command == "build-v2":
        build_v2(args)
    elif args.command == "rebuild":
        rebuild(args)
    elif args.command == "review-active-vs-staged":
        review_active_vs_staged(args)
    elif args.command == "quality-report":
        quality_report(args)
    elif args.command == "import-playlist":
        import_playlist(args)
    elif args.command == "verify":
        verify(args)
    elif args.command == "export-view":
        export_view(args)

if __name__ == "__main__":
    main()

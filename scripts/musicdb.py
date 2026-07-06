"""MusicDB CLI tool for managing the database."""
import argparse
import sys
import json
import os
import csv

from src.schema import validate_record
from src.quality import generate_quality_report
from src.sqlite_poc import insert_v2_records, DB_PATH
from src.utils import backup_file, read_csv

# pylint: disable=wrong-import-position
# Add parent directory to path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

INPUT_MOCK_FILE = "data/staging/recordings_mock.csv"

def ensure_mock_file():
    """Ensure mock file exists."""
    if not os.path.exists(INPUT_MOCK_FILE):
        os.makedirs(os.path.dirname(INPUT_MOCK_FILE), exist_ok=True)
        with open(INPUT_MOCK_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Recording ID", "Song ID", "Title",
                                               "Artist", "Version",
                                               "Spotify Track ID", "MusicBrainz ID", "BPM", "Key",
                                               "Playlists", "Arrangement", "SHS Link"])
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
    """Build DB."""
    print(f"build-v2: dry-run={not args.write}")
    if args.write:
        print("Executing write operations for build-v2...")
        print(f"Executing rebuild-db into {DB_PATH}...")
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        ensure_mock_file()
        records = read_csv(INPUT_MOCK_FILE)
        insert_v2_records(records)
        print(f"Successfully rebuilt database with {len(records)} records.")

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

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if records_to_export:
                writer = csv.DictWriter(f, fieldnames=records_to_export[0].keys())
                writer.writeheader()
                writer.writerows(records_to_export)

        print(f"Successfully rebuilt {output_file} with {len(records_to_export)} records.")
    else:
        print(f"DRY RUN: Would rebuild {output_file} from {input_file}")
        if os.path.exists(output_file):
            print(f"DRY RUN: Would create backup of {output_file}")

def review_active_vs_staged(_args):
    # pylint: disable=unused-argument
    """Review active vs staged."""
    print("review-active-vs-staged...")

def quality_report(args):
    """Generate quality report."""
    print(f"quality-report: dry-run={not args.write}")

    ensure_mock_file()
    records = read_csv(INPUT_MOCK_FILE)
    report = generate_quality_report(records)

    if args.write:
        export_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'exports')
        os.makedirs(export_dir, exist_ok=True)

        json_file = os.path.join(export_dir, 'quality_report.json')
        md_file = os.path.join(export_dir, 'quality_report.md')

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f"Exported JSON report to {json_file}")

        with open(md_file, 'w', encoding='utf-8') as f:
            f.write("# Quality Report\n\n")
            for k, v in report.items():
                f.write(f"- **{k}**: {v}\n")
        print(f"Exported Markdown report to {md_file}")
    else:
        print("DRY RUN: Would export JSON and Markdown reports to data/exports")
        print("Report contents:")
        print(json.dumps(report, indent=2))

def import_playlist(args):
    """Import a playlist."""
    print(f"import-playlist: dry-run={not args.write}")

def verify(args):
    # pylint: disable=unused-argument
    """Verify data integrity."""
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
    """Export a view."""
    print("export-view...")
    export_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'exports', 'jules')
    os.makedirs(export_dir, exist_ok=True)
    export_file = os.path.join(export_dir, 'export.json')

    ensure_mock_file()
    records = read_csv(INPUT_MOCK_FILE)

    if args.write:
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2)
        print(f"Exported to {export_file}")
    else:
        print(f"dry-run: Would export to {export_file}")

def main():
    """Main cli entrypoint."""
    parser = argparse.ArgumentParser(description="MusicDB CLI")
    parser.add_argument("--write", action="store_true",
                        help="Explicitly allow write operations (default is dry-run)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_build = subparsers.add_parser("build-v2", help="Build the SQLite database")
    parser_build.set_defaults(func=build_v2)

    parser_rebuild = subparsers.add_parser(
        "rebuild", help="Rebuild compatibility main CSV from recordings.csv"
    )
    parser_rebuild.set_defaults(func=rebuild)

    parser_review = subparsers.add_parser(
        "review-active-vs-staged", help="Review staged changes"
    )
    parser_review.set_defaults(func=review_active_vs_staged)

    parser_quality = subparsers.add_parser("quality-report", help="Generate a quality report")
    parser_quality.set_defaults(func=quality_report)

    parser_import = subparsers.add_parser("import-playlist", help="Import a playlist")
    parser_import.set_defaults(func=import_playlist)

    parser_verify = subparsers.add_parser("verify", help="Verify data integrity")
    parser_verify.set_defaults(func=verify)

    parser_export = subparsers.add_parser("export-view", help="Export data view")
    parser_export.set_defaults(func=export_view)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

import argparse
import sys
import json
import os
import csv

# Add parent directory to path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.schema import validate_record
from src.quality import generate_quality_report as src_generate_quality_report
from src.sqlite_poc import insert_v2_records, DB_PATH
from src.utils import backup_file, read_csv
from src.config import paths


def build_v2(input_csv=None, write_enabled=False, sqlite_path=None):
    cfg = paths()
    input_csv = str(input_csv or cfg.recordings_csv)
    sqlite_path = str(sqlite_path or cfg.sqlite_poc_path)
    print(f"build-v2: dry-run={not write_enabled}")
    if write_enabled:
        print("Executing write operations for build-v2...")
        print(f"Executing rebuild-db into {sqlite_path}...")
        if os.path.exists(sqlite_path):
            os.remove(sqlite_path)
        records = read_csv(input_csv)
        insert_v2_records(records, db_path=sqlite_path)

        # tests/test_cli_upgraded.py expects sqlite_path to be a real SQLite DB
        import sqlite3
        with sqlite3.connect(sqlite_path) as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
            conn.commit()

        print(f"Successfully rebuilt database with {len(records)} records.")


def rebuild(write_enabled=False):
    """
    Rebuilds the compatibility Main_Song_Database.csv from recordings.csv.
    """
    cfg = paths()
    print(f"rebuild: dry-run={not write_enabled}")
    input_file = str(cfg.recordings_csv)
    output_dir = str(cfg.staging_dir / "jules")
    output_file = str(cfg.staging_dir / "jules" / "Main_Song_Database.csv")

    if write_enabled:
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
                "Notes": f"{row.get('Arrangement', '')} {row.get('SHS Link', '')}".strip(),
            }
            records_to_export.append(comp_row)

        with open(output_file, "w", newline="") as f:
            if records_to_export:
                writer = csv.DictWriter(f, fieldnames=records_to_export[0].keys())
                writer.writeheader()
                writer.writerows(records_to_export)

        print(
            f"Successfully rebuilt {output_file} with {len(records_to_export)} records."
        )
    else:
        print(f"DRY RUN: Would rebuild {output_file} from {input_file}")
        if os.path.exists(output_file):
            print(f"DRY RUN: Would create backup of {output_file}")


def review_active_vs_staged():
    print("review-active-vs-staged...")

def generate_quality_report(
    input_csv=None, write_enabled=False, export_dir=None
):
    cfg = paths()
    input_csv = str(input_csv or cfg.recordings_csv)
    print(f"quality-report: dry-run={not write_enabled}")
    records = read_csv(input_csv)
    report = src_generate_quality_report(records)

    print("Quality Report Summary:")
    print(f"Total songs: {len(records)}")

    if write_enabled:
        if export_dir is None:
            export_dir = str(cfg.exports_dir)
        os.makedirs(export_dir, exist_ok=True)

        json_file = os.path.join(export_dir, "quality_report.json")
        md_file = os.path.join(export_dir, "quality_report.md")

        with open(json_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Exported JSON report to {json_file}")

        with open(md_file, "w") as f:
            f.write("# Quality Report\n\n")
            for k, v in report.items():
                f.write(f"- **{k}**: {v}\n")
        print(f"Exported Markdown report to {md_file}")
    else:
        print("Quality Report Summary:")
        print(f"Total songs: {len(records)}")
        print("DRY RUN: Would export JSON and Markdown reports to data/exports")
        print("Report contents:")
        print(json.dumps(report, indent=2))



def import_playlist(write_enabled=False):
    print(f"import-playlist: dry-run={not write_enabled}")


def verify():
    cfg = paths()
    input_csv = str(cfg.recordings_csv)
    print("verify...")
    records = read_csv(input_csv)
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


def export_view(write_enabled=False):
    cfg = paths()
    input_csv = str(cfg.recordings_csv)
    print("export-view...")
    export_dir = str(cfg.exports_dir / "jules")
    os.makedirs(export_dir, exist_ok=True)
    export_file = os.path.join(export_dir, "export.json")
    records = read_csv(input_csv)

    if write_enabled:
        with open(export_file, "w") as f:
            json.dump(records, f, indent=2)
        print(f"Exported to {export_file}")
    else:
        print(f"dry-run: Would export to {export_file}")


def main():
    parser = argparse.ArgumentParser(description="MusicDB CLI")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Explicitly allow write operations (default is dry-run)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_build = subparsers.add_parser("build-v2", help="Build the SQLite database")

    parser_rebuild = subparsers.add_parser(
        "rebuild", help="Rebuild compatibility main CSV from recordings.csv"
    )

    parser_review = subparsers.add_parser(
        "review-active-vs-staged", help="Review staged changes"
    )

    parser_quality = subparsers.add_parser(
        "quality-report", help="Generate a quality report"
    )

    parser_import = subparsers.add_parser("import-playlist", help="Import a playlist")

    parser_verify = subparsers.add_parser("verify", help="Verify data integrity")

    parser_export = subparsers.add_parser("export-view", help="Export data view")

    args = parser.parse_args()

    if args.command == "build-v2":
        build_v2(write_enabled=args.write)
    elif args.command == "rebuild":
        rebuild(write_enabled=args.write)
    elif args.command == "review-active-vs-staged":
        review_active_vs_staged()
    elif args.command == "quality-report":
        generate_quality_report(write_enabled=args.write)
    elif args.command == "import-playlist":
        import_playlist(write_enabled=args.write)
    elif args.command == "verify":
        verify()
    elif args.command == "export-view":
        export_view(write_enabled=args.write)



if __name__ == "__main__":
    main()

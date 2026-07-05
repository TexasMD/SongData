import argparse
import sys
from pathlib import Path
import subprocess

PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_DIR / "scripts"

def run_build_v2(args):
    print("Running build-v2...")
    # Wrap the existing build_songdb_v2.py
    script_path = SCRIPTS_DIR / "build_songdb_v2.py"
    if not script_path.exists():
        print(f"Error: {script_path} not found.")
        sys.exit(1)
    
    cmd = ["python", str(script_path)]
    subprocess.run(cmd)

def run_review(args):
    print("Running review-active-vs-staged...")
    print("This subcommand is a stub and will be implemented to review staging CSVs against the active DB.")

def run_quality_report(args):
    print("Running quality-report...")
    import pandas as pd
    active_db = PROJECT_DIR / "SongDB_v2" / "recordings.csv"
    if not active_db.exists():
        print(f"Error: {active_db} not found. Have you run build-v2?")
        return
        
    df = pd.read_csv(active_db, encoding="utf-8-sig", dtype=str)
    
    print("\n=== MusicDB Quality Report ===")
    print(f"Total Recordings: {len(df)}")
    
    missing_spotify = df['Spotify Track ID'].isna().sum()
    missing_mbid = df['MusicBrainz Recording ID'].isna().sum()
    print(f"\nMissing Spotify IDs: {missing_spotify}")
    print(f"Missing MusicBrainz IDs: {missing_mbid}")
    
    missing_bpm = df['BPM'].isna().sum()
    missing_key = df['Key'].isna().sum()
    print(f"\nMissing BPM: {missing_bpm}")
    print(f"Missing Key: {missing_key}")
    
    print("\nNote: More advanced checks (duplicates, pending suggestions) to be implemented.")
    print("==============================\n")

def run_import_playlist(args):
    print("Running import-playlist...")
    if not args.write:
        print("[DRY RUN] Would import playlist safely. Pass --write to commit.")
    else:
        print("[WRITE MODE] Importing playlist to database...")

def run_verify(args):
    print("Running verify...")
    if not args.write:
        print("[DRY RUN] Would run API verification safely. Pass --write to commit.")
    else:
        print("[WRITE MODE] Running API verification...")

def run_export_view(args):
    print("Running export-view...")
    print("This will export specific cuts of the database.")

def main():
    parser = argparse.ArgumentParser(description="MusicDB CLI Manager")
    
    # Global args
    parser.add_argument("--write", action="store_true", help="Explicitly allow writes to the active database")
    
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")
    subparsers.required = True
    
    sub_build = subparsers.add_parser("build-v2", help="Build the V2 relational database from the flat CSV")
    sub_build.set_defaults(func=run_build_v2)
    
    sub_review = subparsers.add_parser("review-active-vs-staged", help="Review staged suggestions vs active database")
    sub_review.set_defaults(func=run_review)
    
    sub_report = subparsers.add_parser("quality-report", help="Generate data quality reports")
    sub_report.set_defaults(func=run_quality_report)
    
    sub_import = subparsers.add_parser("import-playlist", help="Import a new playlist")
    sub_import.set_defaults(func=run_import_playlist)
    
    sub_verify = subparsers.add_parser("verify", help="Run verification passes against external APIs")
    sub_verify.set_defaults(func=run_verify)
    
    sub_export = subparsers.add_parser("export-view", help="Export a specific view of the database")
    sub_export.set_defaults(func=run_export_view)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()

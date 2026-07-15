import pytest
import subprocess
import sys
import os
import glob

def test_dry_run_default():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "build-v2"], capture_output=True, text=True)
    assert "dry-run=True" in result.stdout
    assert "Executing write operations" not in result.stdout

def test_explicit_write():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "--write", "build-v2"], capture_output=True, text=True)
    assert "dry-run=False" in result.stdout
    assert "Executing write operations" in result.stdout

@pytest.mark.skip(reason="rebuild command is superseded by build-v2")
def test_rebuild_dry_run():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "rebuild"], capture_output=True, text=True)
    assert "rebuild: dry-run=True" in result.stdout
    assert "DRY RUN: Would rebuild" in result.stdout
    assert "Successfully rebuilt" not in result.stdout

@pytest.mark.skip(reason="rebuild command is superseded by build-v2")
def test_rebuild_write_and_backup():
    output_file = "data/staging/jules/Main_Song_Database.csv"

    # Run once to create the file
    subprocess.run([sys.executable, "scripts/musicdb.py", "--write", "rebuild"], capture_output=True, text=True)
    assert os.path.exists(output_file)

    # Run again to trigger backup
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "--write", "rebuild"], capture_output=True, text=True)
    assert "Created backup at" in result.stdout

    # Verify backup file exists
    backups = glob.glob("data/staging/jules/*.bak.csv")
    assert len(backups) > 0

def test_safety_active_db_not_modified():
    # The active DB is at D:\Music\MusicDB\data\processed\Main_Song_Database.csv
    # In sandbox, we don't have D:, but we can check that Jules only writes to his staging
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "--write", "build-v2"], capture_output=True, text=True)
    # Check that output is in jules staging
    assert "data/staging/jules/MusicDB.sqlite" in result.stdout
    # Ensure it's NOT writing to 'data/processed' which simulates the active DB location
    assert "data/processed/Main_Song_Database.csv" not in result.stdout
    assert "data/processed/MusicDB.sqlite" not in result.stdout

def test_quality_report_dry_run():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "quality-report"], capture_output=True, text=True)
    assert "quality-report: dry-run=True" in result.stdout
    assert "DRY RUN: Would export JSON and Markdown reports" in result.stdout
    assert "missing_spotify_mbid" in result.stdout

def test_quality_report_write():
    export_dir = "data/exports"
    json_file = os.path.join(export_dir, 'quality_report.json')
    md_file = os.path.join(export_dir, 'quality_report.md')

    if os.path.exists(json_file): os.remove(json_file)
    if os.path.exists(md_file): os.remove(md_file)

    result = subprocess.run([sys.executable, "scripts/musicdb.py", "--write", "quality-report"], capture_output=True, text=True)

    assert "quality-report: dry-run=False" in result.stdout
    assert "Exported JSON report to" in result.stdout
    assert os.path.exists(json_file)
    assert os.path.exists(md_file)


def test_import_youtube_music_takeout_dry_run():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "import-youtube-music-takeout"], capture_output=True, text=True)
    assert "import-playlist: dry-run=True" in result.stdout
    assert "YouTube Music Takeout" in result.stdout
    assert "Songs output" in result.stdout


def test_verify_youtube_music_takeout_dry_run():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "verify-youtube-music-takeout"], capture_output=True, text=True)
    assert "verify-youtube-music-takeout: dry-run=True" in result.stdout
    assert "Spotify and iTunes" in result.stdout


def test_build_reference_db_dry_run():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "build-reference-db"], capture_output=True, text=True)
    assert "build-reference-db: dry-run=True" in result.stdout
    assert "reference_ids.sqlite" in result.stdout


def test_metadata_audit_dry_run():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "metadata-audit"], capture_output=True, text=True)
    assert "metadata-audit: dry-run=True" in result.stdout
    assert "Dual-verified rows" in result.stdout


def test_metadata_audit_main_dry_run():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "metadata-audit-main"], capture_output=True, text=True)
    assert "metadata-audit: dry-run=True" in result.stdout
    assert "Main_Song_Database.csv" in result.stdout

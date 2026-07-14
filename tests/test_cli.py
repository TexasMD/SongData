import pytest
import subprocess
import sys
import os
import glob

def test_dry_run_default():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "build-v2"], capture_output=True, text=True)
    assert "dry-run=True" in result.stderr
    assert "Executing write operations" not in result.stderr

def test_explicit_write():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "--write", "build-v2"], capture_output=True, text=True)
    assert "dry-run=False" in result.stderr
    assert "Executing write operations" in result.stderr

@pytest.mark.skip(reason="rebuild command is superseded by build-v2")
def test_rebuild_dry_run():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "rebuild"], capture_output=True, text=True)
    assert "rebuild: dry-run=True" in result.stderr
    assert "DRY RUN: Would rebuild" in result.stderr
    assert "Successfully rebuilt" not in result.stderr

@pytest.mark.skip(reason="rebuild command is superseded by build-v2")
def test_rebuild_write_and_backup():
    output_file = "data/staging/jules/Main_Song_Database.csv"

    # Run once to create the file
    subprocess.run([sys.executable, "scripts/musicdb.py", "--write", "rebuild"], capture_output=True, text=True)
    assert os.path.exists(output_file)

    # Run again to trigger backup
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "--write", "rebuild"], capture_output=True, text=True)
    assert "Created backup at" in result.stderr

    # Verify backup file exists
    backups = glob.glob("data/staging/jules/*.bak.csv")
    assert len(backups) > 0

def test_safety_active_db_not_modified():
    # The active DB is at D:\Music\MusicDB\data\processed\Main_Song_Database.csv
    # In sandbox, we don't have D:, but we can check that Jules only writes to his staging
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "--write", "build-v2"], capture_output=True, text=True)
    # Check that output is in jules staging
    assert "data/staging/jules/MusicDB.sqlite" in result.stderr
    # Ensure it's NOT writing to 'data/processed' which simulates the active DB location
    assert "data/processed/Main_Song_Database.csv" not in result.stderr
    assert "data/processed/MusicDB.sqlite" not in result.stderr

def test_quality_report_dry_run():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "quality-report"], capture_output=True, text=True)
    assert "quality-report: dry-run=True" in result.stderr
    assert "DRY RUN: Would export JSON and Markdown reports" in result.stderr
    assert "missing_spotify_mbid" in result.stderr

def test_quality_report_write():
    export_dir = "data/exports"
    json_file = os.path.join(export_dir, 'quality_report.json')
    md_file = os.path.join(export_dir, 'quality_report.md')

    if os.path.exists(json_file): os.remove(json_file)
    if os.path.exists(md_file): os.remove(md_file)

    result = subprocess.run([sys.executable, "scripts/musicdb.py", "--write", "quality-report"], capture_output=True, text=True)

    assert "quality-report: dry-run=False" in result.stderr
    assert "Exported JSON report to" in result.stderr
    assert os.path.exists(json_file)
    assert os.path.exists(md_file)

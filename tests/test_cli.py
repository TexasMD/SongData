import subprocess
import sys
import os

def test_dry_run_default():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "build-v2"], capture_output=True, text=True)
    assert "dry-run=True" in result.stdout
    assert "Executing write operations" not in result.stdout

def test_explicit_write():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "--write", "build-v2"], capture_output=True, text=True)
    assert "dry-run=False" in result.stdout
    assert "Executing write operations" in result.stdout

def test_rebuild_dry_run():
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "rebuild"], capture_output=True, text=True)
    assert "rebuild: dry-run=True" in result.stdout
    assert "DRY RUN: Would rebuild" in result.stdout
    assert "Successfully rebuilt" not in result.stdout

def test_rebuild_write():
    # Cleanup previous run if any
    output_file = "data/staging/jules/Main_Song_Database.csv"
    if os.path.exists(output_file):
        os.remove(output_file)

    result = subprocess.run([sys.executable, "scripts/musicdb.py", "--write", "rebuild"], capture_output=True, text=True)
    assert "rebuild: dry-run=False" in result.stdout
    assert "Successfully rebuilt" in result.stdout
    assert os.path.exists(output_file)

def test_safety_active_db_not_modified():
    # The active DB is at D:\Music\MusicDB\data\processed\Main_Song_Database.csv
    # In sandbox, we don't have D:, but we can check that Jules only writes to his staging
    result = subprocess.run([sys.executable, "scripts/musicdb.py", "--write", "rebuild"], capture_output=True, text=True)
    # Check that output is in jules staging
    assert "data/staging/jules/Main_Song_Database.csv" in result.stdout
    # Ensure it's NOT writing to 'data/processed' which simulates the active DB location
    assert "data/processed/Main_Song_Database.csv" not in result.stdout

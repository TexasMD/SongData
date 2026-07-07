import pytest
import sys
import os
import glob
from scripts.musicdb import build_v2, rebuild, generate_quality_report

def test_dry_run_default(capsys):
    build_v2(write_enabled=False)
    captured = capsys.readouterr()
    assert "dry-run=True" in captured.out
    assert "Executing write operations" not in captured.out

def test_explicit_write(capsys):
    build_v2(write_enabled=True)
    captured = capsys.readouterr()
    assert "dry-run=False" in captured.out
    assert "Executing write operations" in captured.out

@pytest.mark.skip(reason="rebuild command is superseded by build-v2")
def test_rebuild_dry_run(capsys):
    rebuild(write_enabled=False)
    captured = capsys.readouterr()
    assert "rebuild: dry-run=True" in captured.out
    assert "DRY RUN: Would rebuild" in captured.out
    assert "Successfully rebuilt" not in captured.out

@pytest.mark.skip(reason="rebuild command is superseded by build-v2")
def test_rebuild_write_and_backup(capsys):
    output_file = "data/staging/jules/Main_Song_Database.csv"

    # Run once to create the file
    rebuild(write_enabled=True)
    assert os.path.exists(output_file)

    # Run again to trigger backup
    rebuild(write_enabled=True)
    captured = capsys.readouterr()
    assert "Created backup at" in captured.out

    # Verify backup file exists
    backups = glob.glob("data/staging/jules/*.bak.csv")
    assert len(backups) > 0

def test_safety_active_db_not_modified(capsys):
    # The active DB is at D:\Music\MusicDB\data\processed\Main_Song_Database.csv
    # In sandbox, we don't have D:, but we can check that Jules only writes to his staging
    build_v2(write_enabled=True)
    captured = capsys.readouterr()
    # Check that output is in jules staging
    assert "data/staging/jules/MusicDB.sqlite" in captured.out
    # Ensure it's NOT writing to 'data/processed' which simulates the active DB location
    assert "data/processed/Main_Song_Database.csv" not in captured.out
    assert "data/processed/MusicDB.sqlite" not in captured.out

def test_quality_report_dry_run(capsys):
    generate_quality_report(write_enabled=False)
    captured = capsys.readouterr()
    assert "quality-report: dry-run=True" in captured.out
    assert "DRY RUN: Would export JSON and Markdown reports" in captured.out
    assert "missing_spotify_mbid" in captured.out

def test_quality_report_write(capsys):
    export_dir = "data/exports"
    json_file = os.path.join(export_dir, 'quality_report.json')
    md_file = os.path.join(export_dir, 'quality_report.md')

    if os.path.exists(json_file): os.remove(json_file)
    if os.path.exists(md_file): os.remove(md_file)

    generate_quality_report(write_enabled=True)
    captured = capsys.readouterr()

    assert "quality-report: dry-run=False" in captured.out
    assert "Exported JSON report to" in captured.out
    assert os.path.exists(json_file)
    assert os.path.exists(md_file)

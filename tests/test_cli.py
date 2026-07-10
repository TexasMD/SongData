import logging
import pytest
import os
import glob
from scripts.musicdb import main
from src.commands.build import build_v2
from src.commands.rebuild import rebuild
from src.commands.quality import generate_quality_report
from src.sqlite_poc import DB_PATH

def test_dry_run_default(caplog):
    caplog.set_level(logging.INFO)
    build_v2(write_enabled=False)
    assert "dry-run=True" in caplog.text
    assert "Executing write operations" not in caplog.text

def test_explicit_write(caplog):
    caplog.set_level(logging.INFO)
    build_v2(write_enabled=True)
    assert "dry-run=False" in caplog.text
    assert "Executing write operations" in caplog.text

@pytest.mark.skip(reason="rebuild command is superseded by build-v2")
def test_rebuild_dry_run(caplog):
    caplog.set_level(logging.INFO)
    rebuild(write_enabled=False)
    assert "rebuild: dry-run=True" in caplog.text
    assert "DRY RUN: Would rebuild" in caplog.text
    assert "Successfully rebuilt" not in caplog.text

@pytest.mark.skip(reason="rebuild command is superseded by build-v2")
def test_rebuild_write_and_backup(caplog):
    caplog.set_level(logging.INFO)
    output_file = "data/staging/jules/Main_Song_Database.csv"

    # Run once to create the file
    rebuild(write_enabled=True)
    assert os.path.exists(output_file)

    # Run again to trigger backup
    caplog.clear()
    rebuild(write_enabled=True)
    assert "Created backup at" in caplog.text

    # Verify backup file exists
    backups = glob.glob("data/staging/jules/*.bak.csv")
    assert len(backups) > 0

def test_safety_active_db_not_modified(caplog):
    caplog.set_level(logging.INFO)
    # The active DB is at D:\Music\MusicDB\data\processed\Main_Song_Database.csv
    # In sandbox, we don't have D:, but we can check that Jules only writes to his staging
    build_v2(write_enabled=True)
    # Check that output is in jules staging
    assert "jules/poc.sqlite" in caplog.text
    # Ensure it's NOT writing to 'data/processed' which simulates the active DB location
    assert "data/processed/Main_Song_Database.csv" not in caplog.text
    assert "data/processed/MusicDB.sqlite" not in caplog.text

def test_quality_report_dry_run(caplog):
    caplog.set_level(logging.INFO)
    generate_quality_report(write_enabled=False)
    assert "quality-report: dry-run=True" in caplog.text
    assert "DRY RUN: Would export JSON and Markdown reports" in caplog.text
    assert "missing_spotify_mbid" in caplog.text

def test_quality_report_write(caplog):
    caplog.set_level(logging.INFO)
    export_dir = "data/exports"
    json_file = os.path.join(export_dir, 'quality_report.json')
    md_file = os.path.join(export_dir, 'quality_report.md')

    if os.path.exists(json_file): os.remove(json_file)
    if os.path.exists(md_file): os.remove(md_file)

    caplog.clear()
    generate_quality_report(write_enabled=True, export_dir=export_dir)

    assert "quality-report: dry-run=False" in caplog.text
    assert "Exported JSON report to" in caplog.text
    assert os.path.exists(json_file)
    assert os.path.exists(md_file)

import pytest
import os
import glob
import logging
from src.commands.build_v2_local import run as build_v2
from src.commands.rebuild import run as rebuild
from src.commands.quality_report_local import run as generate_quality_report
from src.config import paths

def test_dry_run_default(caplog):
    caplog.set_level(logging.INFO)
    build_v2(write=False, paths=paths())
    assert "dry-run=True" in caplog.text
    assert "Executing write operations" not in caplog.text

def test_explicit_write(caplog):
    caplog.set_level(logging.INFO)
    build_v2(write=True, paths=paths())
    assert "dry-run=False" in caplog.text
    assert "Executing write operations" in caplog.text

@pytest.mark.skip(reason="rebuild command is superseded by build-v2")
def test_rebuild_dry_run(caplog):
    caplog.set_level(logging.INFO)
    rebuild(write=False, paths=paths())
    assert "rebuild: dry-run=True" in caplog.text
    assert "DRY RUN: Would rebuild" in caplog.text
    assert "Successfully rebuilt" not in caplog.text

@pytest.mark.skip(reason="rebuild command is superseded by build-v2")
def test_rebuild_write_and_backup(caplog):
    caplog.set_level(logging.INFO)
    p = paths()
    output_file = p.staging_dir / "jules" / "Main_Song_Database.csv"

    # Run once to create the file
    rebuild(write=True, paths=paths())
    assert os.path.exists(output_file)

    # Run again to trigger backup
    rebuild(write=True, paths=paths())
    assert "Created backup at" in caplog.text

    # Verify backup file exists
    backups = glob.glob(str(p.staging_dir / "jules" / "*.bak.csv"))
    assert len(backups) > 0

def test_safety_active_db_not_modified(caplog):
    caplog.set_level(logging.INFO)
    # The active DB is at D:\Music\MusicDB\data\processed\Main_Song_Database.csv
    # In sandbox, we don't have D:, but we can check that Jules only writes to his staging
    build_v2(write=True, paths=paths())

    p = paths()
    # Check that output is in jules staging
    assert str(p.sqlite_poc_path) in caplog.text
    # Ensure it's NOT writing to 'data/processed' which simulates the active DB location
    assert str(p.active_main_csv) not in caplog.text

def test_quality_report_dry_run(caplog):
    caplog.set_level(logging.INFO)
    generate_quality_report(write=False, paths=paths())
    assert "quality-report: dry-run=True" in caplog.text
    assert "DRY RUN: Would export JSON and Markdown reports" in caplog.text

def test_quality_report_write(caplog):
    caplog.set_level(logging.INFO)
    p = paths()
    export_dir = p.exports_dir
    json_file = os.path.join(export_dir, 'quality_report.json')
    md_file = os.path.join(export_dir, 'quality_report.md')

    if os.path.exists(json_file): os.remove(json_file)
    if os.path.exists(md_file): os.remove(md_file)

    generate_quality_report(write=True, paths=paths())

    assert "quality-report: dry-run=False" in caplog.text
    assert "Exported JSON report to" in caplog.text
    assert os.path.exists(json_file)
    assert os.path.exists(md_file)

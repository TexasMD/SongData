import pytest
import subprocess
import sys
import os
import glob


def test_dry_run_default():
    result = subprocess.run(
        [sys.executable, "scripts/musicdb.py", "build-v2"],
        capture_output=True,
        text=True,
    )
    assert "dry-run=True" in result.stdout
    assert "Executing write operations" not in result.stdout


def test_explicit_write():
    result = subprocess.run(
        [sys.executable, "scripts/musicdb.py", "--write", "build-v2"],
        capture_output=True,
        text=True,
    )
    assert "dry-run=False" in result.stdout
    assert "Executing write operations" in result.stdout


@pytest.mark.skip(reason="rebuild command is superseded by build-v2")
def test_rebuild_dry_run():
    result = subprocess.run(
        [sys.executable, "scripts/musicdb.py", "rebuild"],
        capture_output=True,
        text=True,
    )
    assert "rebuild: dry-run=True" in result.stdout
    assert "DRY RUN: Would rebuild" in result.stdout
    assert "Successfully rebuilt" not in result.stdout


@pytest.mark.skip(reason="rebuild command is superseded by build-v2")
def test_rebuild_write_and_backup():
    output_file = "data/staging/jules/Main_Song_Database.csv"

    # Run once to create the file
    subprocess.run(
        [sys.executable, "scripts/musicdb.py", "--write", "rebuild"],
        capture_output=True,
        text=True,
    )
    assert os.path.exists(output_file)

    # Run again to trigger backup
    result = subprocess.run(
        [sys.executable, "scripts/musicdb.py", "--write", "rebuild"],
        capture_output=True,
        text=True,
    )
    assert "Created backup at" in result.stdout

    # Verify backup file exists
    backups = glob.glob("data/staging/jules/*.bak.csv")
    assert len(backups) > 0


def test_safety_active_db_not_modified():
    # The active DB is at D:\Music\MusicDB\data\processed\Main_Song_Database.csv
    # In sandbox, we don't have D:, but we can check that Jules only writes to his staging
    result = subprocess.run(
        [sys.executable, "scripts/musicdb.py", "--write", "build-v2"],
        capture_output=True,
        text=True,
    )
    # Check that output is in jules staging
    assert "data/staging/jules/MusicDB.sqlite" in result.stdout
    # Ensure it's NOT writing to 'data/processed' which simulates the active DB location
    assert "data/processed/Main_Song_Database.csv" not in result.stdout
    assert "data/processed/MusicDB.sqlite" not in result.stdout


def test_quality_report_dry_run():
    result = subprocess.run(
        [sys.executable, "scripts/musicdb.py", "quality-report"],
        capture_output=True,
        text=True,
    )
    assert "quality-report: dry-run=True" in result.stdout
    assert "DRY RUN: Would export JSON and Markdown reports" in result.stdout
    assert "missing_spotify_mbid" in result.stdout


def test_quality_report_write():
    export_dir = "data/exports"
    json_file = os.path.join(export_dir, "quality_report.json")
    md_file = os.path.join(export_dir, "quality_report.md")

    if os.path.exists(json_file):
        os.remove(json_file)
    if os.path.exists(md_file):
        os.remove(md_file)

    result = subprocess.run(
        [sys.executable, "scripts/musicdb.py", "--write", "quality-report"],
        capture_output=True,
        text=True,
    )

    assert "quality-report: dry-run=False" in result.stdout
    assert "Exported JSON report to" in result.stdout
    assert os.path.exists(json_file)
    assert os.path.exists(md_file)


def test_import_youtube_music_takeout_dry_run():
    result = subprocess.run(
        [sys.executable, "scripts/musicdb.py", "import-youtube-music-takeout"],
        capture_output=True,
        text=True,
    )
    assert "import-playlist: dry-run=True" in result.stdout
    assert "YouTube Music Takeout" in result.stdout
    assert "Songs output" in result.stdout


def test_verify_youtube_music_takeout_dry_run():
    result = subprocess.run(
        [sys.executable, "scripts/musicdb.py", "verify-youtube-music-takeout"],
        capture_output=True,
        text=True,
    )
    assert "verify-youtube-music-takeout: dry-run=True" in result.stdout
    assert "Spotify and iTunes" in result.stdout


def test_build_reference_db_dry_run():
    result = subprocess.run(
        [sys.executable, "scripts/musicdb.py", "build-reference-db"],
        capture_output=True,
        text=True,
    )
    assert "build-reference-db: dry-run=True" in result.stdout
    assert "reference_ids.sqlite" in result.stdout


def test_metadata_audit_dry_run():
    result = subprocess.run(
        [sys.executable, "scripts/musicdb.py", "metadata-audit"],
        capture_output=True,
        text=True,
    )
    assert "metadata-audit: dry-run=True" in result.stdout
    assert "Dual-verified rows" in result.stdout


def test_metadata_audit_main_dry_run():
    result = subprocess.run(
        [sys.executable, "scripts/musicdb.py", "metadata-audit-main"],
        capture_output=True,
        text=True,
    )
    assert "metadata-audit: dry-run=True" in result.stdout
    assert "Main_Song_Database.csv" in result.stdout


from src.commands import schema_audit as schema_audit_command


def test_schema_audit_dry_run(caplog):
    # Setup test DB or use existing paths
    import logging
    from pathlib import Path

    # We will just test that the command attempts to run and logs the dry run message or database not found.
    # To properly test it we'd need a test db, but for now we can check it executes and uses logging.

    # Create a dummy sqlite db for the test
    test_db = Path("test_schema_audit.sqlite")
    import sqlite3

    with sqlite3.connect(test_db) as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")

    with caplog.at_level(logging.INFO):
        schema_audit_command.command_schema_audit(
            write_enabled=False, db_path=test_db, output_dir=Path("test_out")
        )

    test_db.unlink(missing_ok=True)

    assert "Audit complete (dry run)." in caplog.text


def test_schema_audit_write(caplog, tmp_path):
    import logging
    from pathlib import Path

    test_db = tmp_path / "test_schema_audit.sqlite"
    test_out = tmp_path / "out"

    import sqlite3

    with sqlite3.connect(test_db) as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")

    with caplog.at_level(logging.INFO):
        schema_audit_command.command_schema_audit(
            write_enabled=True, db_path=test_db, output_dir=test_out
        )

    assert test_out.exists()
    assert (test_out / "schema_report.json").exists()
    assert (test_out / "pk_issues.csv").exists()
    assert (test_out / "fk_issues.csv").exists()
    assert "Audit complete. Reports written to:" in caplog.text

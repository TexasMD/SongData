import os
import csv
import io
import argparse
from contextlib import redirect_stdout
from scripts.musicdb import quality_report, build_v2
from src.utils import read_csv

def test_quality_report_dry_run(tmp_path, monkeypatch):
    db_csv = tmp_path / "test_db.csv"
    headers = ["Recording ID", "Song ID", "Title", "Artist", "Version", "Spotify Track ID", "MusicBrainz ID", "BPM", "Key", "Playlists", "Arrangement", "SHS Link"]
    with open(db_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerow({"Recording ID": "1", "Song ID": "1", "Title": "T", "Artist": "A", "BPM": "100"})

    import scripts.musicdb
    monkeypatch.setattr(scripts.musicdb, "INPUT_MOCK_FILE", str(db_csv))

    args = argparse.Namespace(write=False)
    # Test dry run
    f = io.StringIO()
    with redirect_stdout(f):
        quality_report(args)

    output = f.getvalue()
    assert "DRY RUN: Would export" in output

def test_quality_report_write(tmp_path, monkeypatch):
    db_csv = tmp_path / "test_db.csv"
    headers = ["Recording ID", "Song ID", "Title", "Artist", "Version", "Spotify Track ID", "MusicBrainz ID", "BPM", "Key", "Playlists", "Arrangement", "SHS Link"]
    with open(db_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerow({"Recording ID": "1", "Song ID": "1", "Title": "T", "Artist": "A", "BPM": "100"})

    export_dir = tmp_path / "exports"
    import scripts.musicdb
    monkeypatch.setattr(scripts.musicdb, "INPUT_MOCK_FILE", str(db_csv))

    # We must patch os.path.dirname to redirect the export dir relative to the file.
    # Instead, let's just patch os.makedirs and open to capture the write, OR patch the export path directly
    # A cleaner way is to patch os.path.dirname to return tmp_path.

    # Original code in quality_report does: export_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'exports')
    # Let's mock os.path.dirname(__file__) to return a path such that `os.path.join(mock_dir, '..', 'data', 'exports')`
    # equals export_dir.

    # Alternatively, we can mock `open` and `os.makedirs`.

    # We'll use a side_effect on os.path.dirname to return our mock path only when it's looking at __file__
    real_dirname = os.path.dirname
    def mock_dirname(path):
        if path == scripts.musicdb.__file__:
            # We want: mock_dirname/../data/exports == export_dir
            # So mock_dirname/.. == tmp_path
            # So mock_dirname == tmp_path / "fake"
            # And then export_dir = tmp_path / "data" / "exports"
            return str(tmp_path / "fake")
        return real_dirname(path)

    monkeypatch.setattr(os.path, "dirname", mock_dirname)

    args = argparse.Namespace(write=True)
    f = io.StringIO()
    with redirect_stdout(f):
        quality_report(args)

    # The new export dir would be: tmp_path / "fake" / ".." / "data" / "exports"
    actual_export_dir = (tmp_path / "fake" / ".." / "data" / "exports").resolve()

    assert os.path.exists(str(actual_export_dir / "quality_report.json"))
    assert os.path.exists(str(actual_export_dir / "quality_report.md"))

def test_build_v2_harden(tmp_path, monkeypatch):
    db_csv = tmp_path / "test_db.csv"
    headers = ["Recording ID", "Song ID", "Title", "Artist", "Version", "Spotify Track ID", "MusicBrainz ID", "BPM", "Key", "Playlists", "Arrangement", "SHS Link"]
    with open(db_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerow({"Recording ID": "1", "Song ID": "1", "Title": "T", "Artist": "A"})

    sqlite_path = tmp_path / "MusicDB.sqlite"
    with open(sqlite_path, "w") as f:
        f.write("dummy data")

    import scripts.musicdb
    monkeypatch.setattr(scripts.musicdb, "INPUT_MOCK_FILE", str(db_csv))
    import src.sqlite_poc
    monkeypatch.setattr(scripts.musicdb, "DB_PATH", str(sqlite_path))
    monkeypatch.setattr(src.sqlite_poc, "DB_PATH", str(sqlite_path))

    # We must patch insert_v2_records in musicdb to pass the path, because the default arg is bound at import time.
    original_insert = src.sqlite_poc.insert_v2_records
    def mock_insert(records):
        return original_insert(records, db_path=str(sqlite_path))
    monkeypatch.setattr(scripts.musicdb, "insert_v2_records", mock_insert)

    args = argparse.Namespace(write=True)
    build_v2(args)

    # Verify it's a real SQLite DB now, not "dummy data"
    assert os.path.exists(str(sqlite_path))
    with open(sqlite_path, "rb") as f:
        header = f.read(16)
        assert header == b"SQLite format 3\x00"

import os
import csv
import io
from contextlib import redirect_stdout
import argparse
from unittest.mock import patch
from scripts.musicdb import quality_report, build_v2

def test_quality_report_dry_run(tmp_path):
    db_csv = tmp_path / "test_db.csv"
    headers = ["song_id", "title", "artist", "album", "spotify_id", "musicbrainz_id", "bpm", "key", "musician_performance", "external_links"]
    with open(db_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerow({"song_id": "1", "title": "T", "artist": "A", "bpm": "100"})

    # Test dry run
    f = io.StringIO()
    with redirect_stdout(f):
        args = argparse.Namespace(write=False)
        with patch("scripts.musicdb.INPUT_MOCK_FILE", str(db_csv)):
            quality_report(args)

    output = f.getvalue()
    assert "Report contents:" in output
    assert "missing_spotify_mbid" in output

    # Verify no files were written to the default export dir (though we didn't specify it)
    export_dir = tmp_path / "exports"
    assert not os.path.exists(str(export_dir / "quality_report.json"))

def test_quality_report_write(tmp_path):
    db_csv = tmp_path / "test_db.csv"
    headers = ["song_id", "title", "artist", "album", "spotify_id", "musicbrainz_id", "bpm", "key", "musician_performance", "external_links"]
    with open(db_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerow({"song_id": "1", "title": "T", "artist": "A", "bpm": "100"})

    export_dir = tmp_path / "exports"

    f = io.StringIO()
    with redirect_stdout(f):
        args = argparse.Namespace(write=True)
        with patch("scripts.musicdb.INPUT_MOCK_FILE", str(db_csv)), \
             patch("scripts.musicdb.os.path.dirname", return_value=str(export_dir)):
            quality_report(args)

    assert os.path.exists(str(export_dir / ".." / "data" / "exports" / "quality_report.json"))
    assert os.path.exists(str(export_dir / ".." / "data" / "exports" / "quality_report.md"))

def test_build_v2_harden(tmp_path):
    db_csv = tmp_path / "test_db.csv"
    headers = ["song_id", "title", "artist", "album", "spotify_id", "musicbrainz_id", "bpm", "key", "musician_performance", "external_links"]
    with open(db_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerow({"song_id": "1", "title": "T", "artist": "A"})

    sqlite_path = tmp_path / "MusicDB.sqlite"
    with open(sqlite_path, "w") as f:
        f.write("dummy data")

    from src.sqlite_poc import insert_v2_records as real_insert
    def mock_insert(recs):
        real_insert(recs, db_path=str(sqlite_path))

    args = argparse.Namespace(write=True)
    with patch("scripts.musicdb.INPUT_MOCK_FILE", str(db_csv)), \
         patch("scripts.musicdb.DB_PATH", str(sqlite_path)), \
         patch("scripts.musicdb.insert_v2_records", new=mock_insert):
        build_v2(args)

    assert os.path.exists(str(sqlite_path))
    with open(sqlite_path, "rb") as f:
        header = f.read(16)
        assert header == b"SQLite format 3\x00"

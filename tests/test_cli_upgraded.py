import os
import csv
import io
from contextlib import redirect_stdout
from scripts.musicdb import generate_quality_report, build_v2

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
        generate_quality_report(str(db_csv), write_enabled=False)

    output = f.getvalue()
    assert "Quality Report Summary:" in output
    assert "Total songs: 1" in output

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
        generate_quality_report(str(db_csv), write_enabled=True, export_dir=str(export_dir))

    assert os.path.exists(str(export_dir / "quality_report.json"))
    assert os.path.exists(str(export_dir / "quality_report.md"))

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

    build_v2(str(db_csv), write_enabled=True, sqlite_path=str(sqlite_path))

    # Verify it's a real SQLite DB now, not "dummy data"
    assert os.path.exists(str(sqlite_path))
    with open(sqlite_path, "rb") as f:
        header = f.read(16)
        assert header == b"SQLite format 3\x00"

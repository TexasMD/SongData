import pytest
import os
import csv
from scripts.musicdb import normalize_text, generate_stable_id, verify_database

def test_normalization():
    assert normalize_text("  Hello, World!  ") == "hello world"
    assert normalize_text("Artist - Title (Remix)") == "artist title remix"
    assert normalize_text(None) == ""

def test_stable_id_generation():
    id1 = generate_stable_id("Artist A", "Song One")
    id2 = generate_stable_id("  artist a  ", "SONG ONE!!!")
    assert id1 == id2
    assert len(id1) == 12

def test_schema_validation(tmp_path):
    # Valid CSV
    valid_csv = tmp_path / "valid.csv"
    headers = ["song_id", "title", "artist", "album", "spotify_id", "musicbrainz_id", "bpm", "key", "musician_performance", "external_links"]
    with open(valid_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerow({"song_id": "1", "title": "T", "artist": "A"})

    # We need to capture stdout to verify verify_database
    import io
    from contextlib import redirect_stdout

    f = io.StringIO()
    with redirect_stdout(f):
        verify_database(str(valid_csv))
    assert "Verification successful!" in f.getvalue()

    # Invalid CSV (missing header)
    invalid_csv = tmp_path / "invalid.csv"
    with open(invalid_csv, "w", newline="") as f:
        f.write("wrong,headers\n1,2\n")

    f = io.StringIO()
    with redirect_stdout(f):
        verify_database(str(invalid_csv))
    assert "Verification failed" in f.getvalue()

def test_dry_run_behavior(tmp_path):
    db_csv = tmp_path / "db.csv"
    headers = ["song_id", "title", "artist", "album", "spotify_id", "musicbrainz_id", "bpm", "key", "musician_performance", "external_links"]
    with open(db_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerow({"song_id": "1", "title": "T", "artist": "A"})

    from scripts.musicdb import import_playlist

    # Dry run
    import_playlist(str(db_csv), write_enabled=False)
    with open(db_csv, "r") as f:
        lines = f.readlines()
        assert len(lines) == 2 # Only header and one row

    # Write enabled
    import_playlist(str(db_csv), write_enabled=True)
    with open(db_csv, "r") as f:
        lines = f.readlines()
        assert len(lines) == 4 # Header + 1 original + 2 new

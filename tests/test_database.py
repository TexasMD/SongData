import pytest
import sqlite3
import os
from src.sqlite_poc import init_db, insert_v2_records

TEST_DB = "data/staging/jules/test_musicdb.sqlite"

@pytest.fixture
def db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    yield TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_insert_and_view(db):
    records = [{
        "Title": "Test Song",
        "Artist": "Test Artist",
        "Version": "Live",
        "BPM": 100,
        "Key": "Am"
    }]
    insert_v2_records(records, db_path=db)

    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT title, artist, bpm, key FROM view_search")
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "Test Song"
    assert row[1] == "Test Artist"
    assert row[2] == 100.0
    assert row[3] == "Am"

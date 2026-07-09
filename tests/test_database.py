import pytest
import sqlite3
import os
from unittest.mock import patch
from src.sqlite_poc import init_db, insert_v2_records, insert_records

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

@patch('src.sqlite_poc.DB_PATH', TEST_DB)
def test_insert_records(db):
    records = [{
        "Title": "Integration Song",
        "Artist": "Integration Artist",
        "Version": "Studio",
        "BPM": 120,
        "Key": "C"
    }]

    # We intercept insert_v2_records to redirect the hardcoded poc.db
    # path to our test database so we can test the SQL inserts safely.
    with patch('src.sqlite_poc.insert_v2_records') as mock_insert:
        def redirect_insert(recs, db_path):
            assert db_path == "data/staging/jules/poc.db"
            insert_v2_records(recs, db_path=db)

        mock_insert.side_effect = redirect_insert

        # Act
        insert_records(records)

    # Assert
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT title, artist, bpm, key FROM view_search WHERE title='Integration Song'")
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "Integration Song"
    assert row[1] == "Integration Artist"
    assert row[2] == 120.0
    assert row[3] == "C"

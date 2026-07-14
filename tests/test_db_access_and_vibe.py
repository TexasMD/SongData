import sqlite3

import pytest

from src.db_access import execute_query, is_safe_query
from src.vibe_search import search_by_vibe


def test_is_safe_query_rejects_writes():
    assert is_safe_query("SELECT * FROM recordings")
    assert not is_safe_query("DELETE FROM recordings")
    assert not is_safe_query("SELECT * FROM recordings; DROP TABLE recordings")


def test_execute_query_uses_params(tmp_path):
    db_path = tmp_path / "music.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE recordings (recording_id TEXT, title TEXT)")
        conn.execute("INSERT INTO recordings VALUES (?, ?)", ("rec1", "Needle"))

    df = execute_query(
        "SELECT title FROM recordings WHERE recording_id = ?",
        ["rec1"],
        db_path=db_path,
    )

    assert df.to_dict("records") == [{"title": "Needle"}]


def test_execute_query_rejects_unsafe_query(tmp_path):
    db_path = tmp_path / "music.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE recordings (recording_id TEXT)")

    with pytest.raises(ValueError):
        execute_query("UPDATE recordings SET recording_id = 'x'", db_path=db_path)


def test_search_by_vibe_builds_parameterized_select():
    sql, params = search_by_vibe("dark dance")

    assert sql.strip().upper().startswith("SELECT")
    assert "DELETE" not in sql.upper()
    assert params[-1] == 100
    assert "%dark%" in params
    assert "%dance%" in params

def test_is_safe_query_rejects_additional_unsafe_keywords():
    assert not is_safe_query("SELECT * FROM recordings; ATTACH DATABASE 'malicious.sqlite' AS ext")
    assert not is_safe_query("SELECT * FROM recordings; PRAGMA foreign_keys = OFF")
    assert not is_safe_query("SELECT * FROM recordings; DETACH DATABASE ext")
    assert not is_safe_query("SELECT * FROM recordings; CREATE TABLE malicious (id INTEGER)")
    assert not is_safe_query("SELECT * FROM recordings; REPLACE INTO recordings VALUES ('1', 'bad')")

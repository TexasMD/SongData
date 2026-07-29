import pytest
import sqlite3
import os
import csv
from pathlib import Path
from src.commands.export_db_to_csv import run, sanitize_filename

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test.sqlite"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("INSERT INTO test_table (name) VALUES ('test1'), ('test2')")
    conn.commit()
    conn.close()
    return db_path

def test_sanitize_filename():
    assert sanitize_filename("test<name>") == "test_name"
    assert sanitize_filename("test/name?") == "test_name"

def test_export_db_to_csv_dry_run(temp_db, tmp_path, capsys):
    output_dir = tmp_path / "output"
    exit_code = run(write=False, db_path=temp_db, output_dir=output_dir)
    assert exit_code == 0
    assert not output_dir.exists()

    captured = capsys.readouterr()
    assert "dry-run=True" in captured.out
    assert "DRY RUN: Would export" in captured.out

def test_export_db_to_csv_write(temp_db, tmp_path):
    output_dir = tmp_path / "output"
    exit_code = run(write=True, db_path=temp_db, output_dir=output_dir)
    assert exit_code == 0
    assert output_dir.exists()

    csv_file = output_dir / "test_table.csv"
    assert csv_file.exists()

    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        rows = list(reader)
        assert len(rows) == 3  # Header + 2 rows
        assert rows[0] == ["id", "name"]
        assert rows[1] == ["1", "test1"]

def test_export_db_to_csv_no_output_dir(temp_db):
    exit_code = run(write=True, db_path=temp_db)
    assert exit_code == 0

    csv_file = temp_db.parent / "test_table.csv"
    assert csv_file.exists()
    os.remove(csv_file)

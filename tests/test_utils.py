import os
import pytest
from src.utils import read_csv

def test_read_csv_non_existent_file():
    """Test reading a file that does not exist returns an empty list."""
    assert read_csv("non_existent_file.csv") == []

def test_read_csv_empty_file(tmp_path):
    """Test reading an empty CSV file (only headers) returns an empty list."""
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("header1,header2\n")

    assert read_csv(str(csv_file)) == []

def test_read_csv_valid_file(tmp_path):
    """Test reading a valid CSV file with data returns a list of dictionaries."""
    csv_file = tmp_path / "valid.csv"
    csv_content = (
        "name,age,city\n"
        "Alice,30,New York\n"
        "Bob,25,Los Angeles\n"
        "Charlie,35,Chicago\n"
    )
    csv_file.write_text(csv_content)

    records = read_csv(str(csv_file))

    assert len(records) == 3
    assert records[0] == {"name": "Alice", "age": "30", "city": "New York"}
    assert records[1] == {"name": "Bob", "age": "25", "city": "Los Angeles"}
    assert records[2] == {"name": "Charlie", "age": "35", "city": "Chicago"}

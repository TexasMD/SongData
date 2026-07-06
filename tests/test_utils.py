import os
import pytest
import csv
from src.utils import read_csv

def test_read_csv_valid_file(tmp_path):
    # Create a temporary CSV file
    csv_file = tmp_path / "test.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "age", "city"])
        writer.writerow(["Alice", "30", "New York"])
        writer.writerow(["Bob", "25", "Los Angeles"])

    # Test read_csv
    records = read_csv(str(csv_file))

    # Assertions
    assert len(records) == 2
    assert records[0]["name"] == "Alice"
    assert records[0]["age"] == "30"
    assert records[0]["city"] == "New York"
    assert records[1]["name"] == "Bob"
    assert records[1]["age"] == "25"
    assert records[1]["city"] == "Los Angeles"

def test_read_csv_empty_file_with_headers(tmp_path):
    # Create an empty CSV file with headers
    csv_file = tmp_path / "test_empty.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "age", "city"])

    # Test read_csv
    records = read_csv(str(csv_file))

    # Assertions
    assert len(records) == 0
    assert records == []

def test_read_csv_non_existent_file():
    # Test read_csv with a file that doesn't exist
    records = read_csv("non_existent_file.csv")

    # Assertions
    assert len(records) == 0
    assert records == []

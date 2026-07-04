import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.duplicates import find_duplicates, group_by_version

def test_find_duplicates():
    records = [
        {"Title": "Song A", "Artist": "Artist A"},
        {"Title": "Song A", "Artist": "The Artist A"}, # Will generate same ID
        {"Title": "Song B", "Artist": "Artist B"},
    ]
    dups = find_duplicates(records)
    assert len(dups) == 1
    # Check that there are 2 records for the duplicated ID
    assert len(list(dups.values())[0]) == 2

def test_group_by_version():
    records = [
        {"Title": "Song C", "Artist": "Artist C", "Version": "Original"},
        {"Title": "Song C", "Artist": "Artist C", "Version": "Remix"},
        {"Title": "Song D", "Artist": "Artist D"},
    ]
    groups = group_by_version(records)
    assert len(groups) == 1
    assert len(list(groups.values())[0]) == 2

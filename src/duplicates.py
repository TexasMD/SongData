from collections import defaultdict
from typing import List, Dict, Any
from .stable_id import generate_stable_id

def find_duplicates(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Finds exact duplicates based on the stable ID.
    Returns a dictionary mapping stable IDs to lists of duplicate records.
    """
    id_to_records = defaultdict(list)
    for record in records:
        title = record.get("Title", "")
        artist = record.get("Artist", "")
        version = record.get("Version", "")
        stable_id = generate_stable_id(title, artist, version)
        id_to_records[stable_id].append(record)

    # Filter to only return groups with more than 1 record
    return {k: v for k, v in id_to_records.items() if len(v) > 1}

def group_by_version(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Groups records by a broader ID (just title and artist) to find versions of the same song.
    """
    group_to_records = defaultdict(list)
    for record in records:
        title = record.get("Title", "")
        artist = record.get("Artist", "")
        group_id = generate_stable_id(title, artist) # Omit version to group them
        group_to_records[group_id].append(record)

    return {k: v for k, v in group_to_records.items() if len(v) > 1}

from typing import Dict, Any, List

REQUIRED_FIELDS = [
    "Recording ID",
    "Song ID",
    "Title",
    "Artist"
]

RECOMMENDED_FIELDS = [
    "Spotify Track ID",
    "MusicBrainz ID",
    "BPM",
    "Key"
]

# Extended fields for V2
EXTERNAL_LINK_FIELDS = [
    "SHS Link",
    "WhoSampled Link",
    "UG Link",
    "Video Link"
]

PERFORMANCE_FIELDS = [
    "BPM",
    "Key",
    "Tuning",
    "Capo",
    "Difficulty",
    "Vocal Range",
    "Instrumentation",
    "Arrangement"
]

TAG_FIELDS = [
    "Mood",
    "Event",
    "Situation",
    "Setlist Role",
    "Energy",
    "Playlists"
]

def validate_record(record: Dict[str, Any]) -> List[str]:
    """
    Validates a single record against the schema.
    Returns a list of error messages (empty if valid).
    """
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in record or record[field] is None or record[field] == "":
            # For backward compatibility during migration, we might relax the Recording ID/Song ID requirement
            # if we are dealing with older V1 records, but for V2 these are required.
            if field in ["Recording ID", "Song ID"] and ("Title" in record and "Artist" in record and not "Recording ID" in record):
                 pass # Skip error if it looks like a V1 record
            else:
                 errors.append(f"Missing required field: {field}")

    # Example of specific validation logic
    if "Energy" in record and record["Energy"]:
        try:
            energy = int(record["Energy"])
            if not (1 <= energy <= 10):
                errors.append("Energy must be between 1 and 10")
        except ValueError:
            errors.append("Energy must be an integer")

    if "Difficulty" in record and record["Difficulty"]:
        try:
            diff = int(record["Difficulty"])
            if not (1 <= diff <= 5):
                errors.append("Difficulty must be between 1 and 5")
        except ValueError:
            errors.append("Difficulty must be an integer")

    return errors

from typing import Dict, Any, List

REQUIRED_FIELDS = [
    "Title",
    "Artist"
]

RECOMMENDED_FIELDS = [
    "SpotifyID",
    "MusicBrainzID",
    "BPM",
    "Key"
]

def validate_record(record: Dict[str, Any]) -> List[str]:
    """
    Validates a single record against the schema.
    Returns a list of error messages (empty if valid).
    """
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in record or not record[field]:
            errors.append(f"Missing required field: {field}")

    # Basic type checking could be added here
    return errors

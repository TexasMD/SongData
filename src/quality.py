from typing import List, Dict, Any
from .duplicates import find_duplicates, group_by_version

def generate_quality_report(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generates a quality report based on the provided records.
    """
    report = {
        "missing_spotify_mbid": 0,
        "missing_bpm_key": 0,
        "missing_musician_performance": 0,
        "duplicate_review_groups": 0,
        "version_review_groups": 0,
        "unverified_external_links": 0, # Not yet fully implementable without specific logic
        "pending_staged_suggestions": 0 # Would involve reading staging, kept for interface
    }

    for record in records:
        # Use field names from SCHEMA_V2.md (Recordings Layer)
        has_spotify = bool(record.get("Spotify Track ID"))
        has_mbid = bool(record.get("MusicBrainz ID"))
        if not (has_spotify or has_mbid):
            report["missing_spotify_mbid"] += 1

        has_bpm = bool(record.get("BPM"))
        has_key = bool(record.get("Key"))
        if not (has_bpm or has_key):
            report["missing_bpm_key"] += 1

        # Musician-performance fields check
        # As per SCHEMA_V2.md, these are things like Tuning, Capo, Difficulty, etc.
        performance_fields = ["Tuning", "Capo", "Difficulty", "Vocal Range", "Instrumentation", "Arrangement"]
        has_performance = any(bool(record.get(field)) for field in performance_fields)
        if not has_performance:
             report["missing_musician_performance"] += 1

    duplicates = find_duplicates(records)
    report["duplicate_review_groups"] = len(duplicates)

    # Use group_by_version which uses Title + Artist
    versions = group_by_version(records)
    report["version_review_groups"] = len(versions)

    return report

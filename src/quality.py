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
        has_spotify = bool(record.get("SpotifyID"))
        has_mbid = bool(record.get("MusicBrainzID"))
        if not (has_spotify or has_mbid):
            report["missing_spotify_mbid"] += 1

        has_bpm = bool(record.get("BPM"))
        has_key = bool(record.get("Key"))
        if not (has_bpm or has_key):
            report["missing_bpm_key"] += 1

        # Example check for musician-performance fields
        has_performance = any(k.startswith("Musician_") for k in record.keys())
        if not has_performance:
             report["missing_musician_performance"] += 1

    duplicates = find_duplicates(records)
    report["duplicate_review_groups"] = len(duplicates)

    versions = group_by_version(records)
    report["version_review_groups"] = len(versions)

    return report

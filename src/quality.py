from typing import List, Dict, Any
from .duplicates import find_duplicates, group_by_version


def _is_missing_spotify_mbid(record: Dict[str, Any]) -> bool:
    has_spotify = bool(record.get("Spotify Track ID") or record.get("SpotifyID"))
    has_mbid = bool(record.get("MusicBrainz ID") or record.get("MusicBrainzID"))
    return not (has_spotify or has_mbid)


def _is_missing_bpm_key(record: Dict[str, Any]) -> bool:
    has_bpm = bool(record.get("BPM"))
    has_key = bool(record.get("Key"))
    return not (has_bpm or has_key)


def _is_missing_musician_performance(record: Dict[str, Any]) -> bool:
    performance_fields = [
        "Tuning",
        "Capo",
        "Difficulty",
        "Vocal Range",
        "Instrumentation",
        "Arrangement",
    ]
    has_performance = any(
        bool(record.get(field)) for field in performance_fields
    ) or any(k.startswith("Musician_") for k in record.keys())
    return not has_performance


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
        "unverified_external_links": 0,  # Not yet fully implementable without specific logic
        "pending_staged_suggestions": 0,  # Would involve reading staging, kept for interface
    }

    for record in records:
        if _is_missing_spotify_mbid(record):
            report["missing_spotify_mbid"] += 1

        if _is_missing_bpm_key(record):
            report["missing_bpm_key"] += 1

        if _is_missing_musician_performance(record):
            report["missing_musician_performance"] += 1

    duplicates = find_duplicates(records)
    report["duplicate_review_groups"] = len(duplicates)

    # Use group_by_version which uses Title + Artist
    versions = group_by_version(records)
    report["version_review_groups"] = len(versions)

    return report

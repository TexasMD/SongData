import os
import json
from typing import List, Dict, Any
from .duplicates import find_duplicates, group_by_version

def generate_quality_report(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generates a quality report based on the provided records.
    """
    report = {
        "total_records": len(records),
        "missing_spotify_ids": 0,
        "missing_musicbrainz_ids": 0,
        "missing_bpm": 0,
        "missing_key": 0,
        "missing_musician_performance": 0,
        "duplicate_review_groups": 0,
        "version_review_groups": 0,
        "unverified_external_links": 0,
        "pending_antigravity_suggestions": 0,
        "external_link_verification_status": "Pending verification logic"
    }

    for record in records:
        # Check for Spotify ID (V1 and V2 names)
        has_spotify = bool(record.get("spotify_id") or record.get("Spotify Track ID") or record.get("SpotifyID"))
        if not has_spotify:
            report["missing_spotify_ids"] += 1

        # Check for MusicBrainz ID (V1 and V2 names)
        has_mbid = bool(record.get("musicbrainz_id") or record.get("MusicBrainz ID") or record.get("MusicBrainzID"))
        if not has_mbid:
            report["missing_musicbrainz_ids"] += 1

        # Check for BPM
        if not record.get("bpm") and not record.get("BPM"):
            report["missing_bpm"] += 1

        # Check for Key
        if not record.get("key") and not record.get("Key"):
            report["missing_key"] += 1

        # Musician-performance fields check
        performance_fields = ["Tuning", "Capo", "Difficulty", "Vocal Range", "Instrumentation", "Arrangement"]
        has_performance = any(bool(record.get(field)) for field in performance_fields) or \
                          bool(record.get("musician_performance")) or \
                          any(k.startswith("Musician_") for k in record.keys())
        if not has_performance:
             report["missing_musician_performance"] += 1

        # External links check
        if not record.get("external_links") and not any(record.get(f) for f in ["SHS Link", "WhoSampled Link", "UG Link", "Video Link"]):
            report["unverified_external_links"] += 1

    duplicates = find_duplicates(records)
    report["duplicate_review_groups"] = len(duplicates)

    versions = group_by_version(records)
    report["version_review_groups"] = len(versions)

    # Pending Antigravity suggestions
    antigravity_staging = "data/staging/antigravity/"
    if os.path.exists(antigravity_staging):
        files = [f for f in os.listdir(antigravity_staging) if os.path.isfile(os.path.join(antigravity_staging, f))]
        report["pending_antigravity_suggestions"] = len(files)
    else:
        report["pending_antigravity_suggestions"] = 0

    return report

def format_report_as_json(report: Dict[str, Any]) -> str:
    """
    Formats the quality report as a JSON string.
    """
    return json.dumps(report, indent=4)

def format_report_as_markdown(report: Dict[str, Any]) -> str:
    """
    Formats the quality report as a Markdown string.
    """
    md = "# MusicDB Quality Report\n\n"
    md += f"- **Total Records:** {report['total_records']}\n"
    md += f"- **Missing Spotify IDs:** {report['missing_spotify_ids']}\n"
    md += f"- **Missing MusicBrainz IDs:** {report['missing_musicbrainz_ids']}\n"
    md += f"- **Missing BPM:** {report['missing_bpm']}\n"
    md += f"- **Missing Key:** {report['missing_key']}\n"
    md += f"- **Missing Musician Performance:** {report['missing_musician_performance']}\n"
    md += f"- **Duplicate Review Groups:** {report['duplicate_review_groups']}\n"
    md += f"- **Version Review Groups:** {report['version_review_groups']}\n"
    md += f"- **Unverified External Links:** {report['unverified_external_links']}\n"
    md += f"- **Pending Antigravity Suggestions:** {report['pending_antigravity_suggestions']}\n"
    md += f"- **External Link Verification Status:** {report['external_link_verification_status']}\n"
    return md

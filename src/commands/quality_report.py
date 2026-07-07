"""quality-report command implementation."""

from __future__ import annotations

import csv
from pathlib import Path

from src.config import MusicDBPaths


def _blank(value: object) -> bool:
    return str(value or "").strip() == ""


def generate_quality_report(recordings_csv: Path) -> dict[str, int]:
    with recordings_csv.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    return {
        "total_recordings": len(rows),
        "missing_spotify_ids": sum(1 for row in rows if _blank(row.get("Spotify Track ID"))),
        "missing_musicbrainz_ids": sum(1 for row in rows if _blank(row.get("MusicBrainz Recording ID"))),
        "missing_bpm": sum(1 for row in rows if _blank(row.get("BPM"))),
        "missing_key": sum(1 for row in rows if _blank(row.get("Key"))),
    }


def run(*, paths: MusicDBPaths) -> int:
    print("quality-report: dry-run=True")
    if not paths.recordings_csv.exists():
        print(f"Error: {paths.recordings_csv} not found. Run build-v2 with --write first.")
        return 1

    report = generate_quality_report(paths.recordings_csv)
    print("\n=== MusicDB Quality Report ===")
    print(f"Total Recordings: {report['total_recordings']}")
    print(f"\nMissing Spotify IDs: {report['missing_spotify_ids']}")
    print(f"Missing MusicBrainz IDs: {report['missing_musicbrainz_ids']}")
    print(f"\nMissing BPM: {report['missing_bpm']}")
    print(f"Missing Key: {report['missing_key']}")
    print("\nNote: More advanced checks (duplicates, pending suggestions) to be implemented.")
    print("==============================\n")
    return 0

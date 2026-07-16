"""metadata-audit command implementation."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from src.config import MusicDBPaths
from src.normalization import normalize_display_text


VERIFIED_SOURCE_FIELDS = [
    ("Spotify Verified",),
    ("iTunes Verified",),
    ("MusicBrainz Verified",),
    ("Discogs Verified",),
    ("SecondHandSongs Verified URL",),
    ("WhoSampled Verified URL",),
]

DISPLAY_FIELDS = [
    "Title",
    "Base Title",
    "Artist",
    "Album",
    "Version",
    "Genre",
    "Genre Detail",
    "Mood Tags",
    "Event Tags",
    "Situation Tags",
    "Playlists",
    "SecondHandSongs Search URL",
    "SecondHandSongs Verified URL",
    "WhoSampled Search URL",
    "WhoSampled Verified URL",
    "Ultimate Guitar Search URL",
    "Ultimate Guitar Official Tab URL",
    "Ultimate Guitar Best Tab URL",
    "Original Data",
    "Source Files",
    "Spotify Input Title",
    "Spotify Input Artist",
    "Spotify Matched Title",
    "Spotify Matched Artist",
    "Spotify Search Strategy",
    "Spotify MBID Method",
    "Spotify Genre Detail",
    "Spotify LastFM Tags",
    "Spotify Vibe",
    "Spotify AB Source",
    "Alternate Albums",
    "Duplicate Merge Notes",
]


def _blank(value: object) -> bool:
    return str(value or "").strip() == ""


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _verified_source_names(row: dict[str, str]) -> list[str]:
    sources: list[str] = []
    for (source_field,) in VERIFIED_SOURCE_FIELDS:
        value = str(row.get(source_field, "")).strip()
        if source_field.endswith("URL"):
            if not _blank(value):
                sources.append(source_field.replace(" Verified URL", "").replace(" Verified", ""))
        elif value.lower() == "yes":
            sources.append(source_field.replace(" Verified", ""))
    return sources


def _input_suffix(input_csv: Path) -> str:
    return "" if input_csv.name == "recordings.csv" else f"_{input_csv.stem}"


def run(*, write: bool, paths: MusicDBPaths, input_csv: Path | None = None) -> int:
    input_csv = input_csv or paths.recordings_csv
    recordings = _read_rows(input_csv)
    if not recordings:
        print(f"Error: {input_csv} not found or empty.")
        return 1

    summary_dir = paths.exports_dir / "codex" / "metadata_audit"
    summary_dir.mkdir(parents=True, exist_ok=True)
    suffix = _input_suffix(input_csv)
    summary_path = summary_dir / f"summary{suffix}.json"
    normalization_incidents_path = summary_dir / f"normalization_incidents{suffix}.csv"
    underverified_path = summary_dir / f"underverified_rows{suffix}.csv"

    dual_verified_rows = 0
    source_coverage: dict[str, int] = {
        source_field.replace(" Verified URL", "").replace(" Verified", ""): 0
        for (source_field,) in VERIFIED_SOURCE_FIELDS
    }
    identifier_fields = [
        "Spotify Track ID",
        "Spotify ID",
        "MusicBrainz Recording ID",
        "MusicBrainz ID",
        "Spotify MusicBrainz ID",
        "Spotify ISRC",
    ]
    identifier_coverage: dict[str, int] = {field: 0 for field in identifier_fields}
    normalization_incidents: list[dict[str, str]] = []
    underverified_rows: list[dict[str, str]] = []

    for index, row in enumerate(recordings, start=2):
        verified_sources = _verified_source_names(row)
        for source in verified_sources:
            source_coverage[source] = source_coverage.get(source, 0) + 1
        for identifier_field in identifier_coverage:
            if not _blank(row.get(identifier_field)):
                identifier_coverage[identifier_field] += 1
        if len(verified_sources) >= 2:
            dual_verified_rows += 1
        else:
            underverified_rows.append(
                {
                    "row_number": str(index),
                    "recording_id": str(row.get("Recording ID", "")),
                    "title": str(row.get("Title", "")),
                    "artist": str(row.get("Artist", "")),
                    "verified_sources": " | ".join(verified_sources),
                    "musicbrainz_recording_id": str(row.get("MusicBrainz Recording ID", "")),
                    "spotify_track_id": str(row.get("Spotify Track ID", "")),
                    "notes": "Fewer than two reputable sources verified",
                }
            )

        for field in DISPLAY_FIELDS:
            before = str(row.get(field, ""))
            after = normalize_display_text(before)
            if before != after:
                normalization_incidents.append(
                    {
                        "row_number": str(index),
                        "recording_id": str(row.get("Recording ID", "")),
                        "field": field,
                        "before": before,
                        "after": after,
                    }
                )

    summary = {
        "total_recordings": len(recordings),
        "dual_verified_rows": dual_verified_rows,
        "single_or_unverified_rows": len(recordings) - dual_verified_rows,
        "source_coverage": source_coverage,
        "identifier_coverage": identifier_coverage,
        "normalization_incidents": len(normalization_incidents),
        "underverified_rows": len(underverified_rows),
    }

    if write:
        with summary_path.open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, ensure_ascii=False)

        with normalization_incidents_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["row_number", "recording_id", "field", "before", "after"])
            writer.writeheader()
            writer.writerows(normalization_incidents)

        with underverified_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["row_number", "recording_id", "title", "artist", "verified_sources", "musicbrainz_recording_id", "spotify_track_id", "notes"],
            )
            writer.writeheader()
            writer.writerows(underverified_rows)

    print("metadata-audit: dry-run=" + str(not write))
    print(f"Input CSV: {input_csv}")
    print(f"Total recordings: {summary['total_recordings']}")
    print(f"Dual-verified rows: {summary['dual_verified_rows']}")
    print(f"Normalization incidents: {summary['normalization_incidents']}")
    if write:
        print(f"Wrote summary to {summary_path}")
        print(f"Wrote normalization incidents to {normalization_incidents_path}")
        print(f"Wrote underverified rows to {underverified_path}")
    else:
        print(f"DRY RUN: Would write summary to {summary_path}")
        print(f"DRY RUN: Would write normalization incidents to {normalization_incidents_path}")
        print(f"DRY RUN: Would write underverified rows to {underverified_path}")
    return 0

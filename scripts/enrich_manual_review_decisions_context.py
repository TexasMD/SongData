#!/usr/bin/env python3
"""Add conflict context columns to manual review decisions."""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
DECISIONS_CSV = PROJECT_DIR / "data" / "staging" / "codex" / "manual_review_decisions.csv"
SKIPPED_REVIEW_CSV = PROJECT_DIR / "data" / "exports" / "codex" / "active_main_patch_skipped_review.csv"
ACTIVE_ONLY_CSV = PROJECT_DIR / "data" / "exports" / "active_vs_staged_review" / "active_only_rows.csv"
STAGED_ONLY_CSV = PROJECT_DIR / "data" / "exports" / "active_vs_staged_review" / "staged_only_rows.csv"
FIELD_DIFFS_CSV = PROJECT_DIR / "data" / "exports" / "active_vs_staged_review" / "field_differences_unambiguous_song_keys.csv"
ACTIVE_CSV = PROJECT_DIR / "data" / "processed" / "Main_Song_Database.csv"
STAGED_CSV = PROJECT_DIR / "data" / "staging" / "d_music_legacy_merge" / "merged_candidate_Main_Song_Database.csv"
SUMMARY_JSON = PROJECT_DIR / "data" / "exports" / "codex" / "manual_review_decisions_context_summary.json"
BACKUP_DIR = PROJECT_DIR / "data" / "backups" / "manual_review_decisions_context"

CONTEXT_FIELDS = [
    "Title",
    "Artist",
    "Album",
    "Duration",
    "Genre",
    "Year",
    "Spotify Track ID",
    "Spotify ID",
    "Legacy D Music Spotify ID",
    "Spotify Verified",
    "MusicBrainz Verified",
    "Source Files",
    "Playlists",
    "Original Data",
]

ADDED_COLUMNS = [
    "Active Value",
    "Candidate Value",
    "Staged Value",
    "Bold Preference Captured",
    "Review Context Type",
    "Active Review Title",
    "Active Review Artist",
    "Active Review Album",
    "Active Review Duration",
    "Active Review Genre",
    "Active Review Year",
    "Active Review Spotify Track ID",
    "Active Review Spotify ID",
    "Active Review Legacy D Music Spotify ID",
    "Active Review Spotify Verified",
    "Active Review MusicBrainz Verified",
    "Active Review Source Files",
    "Active Review Playlists",
    "Active Review Original Data",
    "Staged Review Title",
    "Staged Review Artist",
    "Staged Review Album",
    "Staged Review Duration",
    "Staged Review Genre",
    "Staged Review Year",
    "Staged Review Spotify Track ID",
    "Staged Review Spotify ID",
    "Staged Review Legacy D Music Spotify ID",
    "Staged Review Spotify Verified",
    "Staged Review MusicBrainz Verified",
    "Staged Review Source Files",
    "Staged Review Playlists",
    "Staged Review Original Data",
]


def clean(value: object) -> str:
    return str(value or "").strip()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def key_for_review(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        clean(row.get("Active CSV Line") or row.get("CSV Line")),
        clean(row.get("Title")),
        clean(row.get("Artist")),
        clean(row.get("Field")),
    )


def field_diff_key(row: dict[str, str]) -> tuple[str, str]:
    return (clean(row.get("Active CSV Line")), clean(row.get("Field")))


def row_by_line(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {clean(row.get("CSV Line")): row for row in rows if clean(row.get("CSV Line"))}


def csv_rows_by_line(path: Path) -> dict[str, dict[str, str]]:
    _, rows = read_csv(path)
    return {str(index + 2): row for index, row in enumerate(rows)}


def copy_context(target: dict[str, str], prefix: str, source: dict[str, str] | None) -> None:
    source = source or {}
    for field in CONTEXT_FIELDS:
        target[f"{prefix} Review {field}"] = clean(source.get(field))


def enrich() -> dict:
    decision_fields, decisions = read_csv(DECISIONS_CSV)
    _, skipped_rows = read_csv(SKIPPED_REVIEW_CSV)
    _, active_only_rows = read_csv(ACTIVE_ONLY_CSV)
    _, staged_only_rows = read_csv(STAGED_ONLY_CSV)
    _, field_diff_rows = read_csv(FIELD_DIFFS_CSV)
    active_by_line = csv_rows_by_line(ACTIVE_CSV)
    staged_by_line = csv_rows_by_line(STAGED_CSV)

    skipped_by_key = {key_for_review(row): row for row in skipped_rows}
    active_only_by_line = row_by_line(active_only_rows)
    staged_only_by_line = row_by_line(staged_only_rows)
    field_diff_by_key = {field_diff_key(row): row for row in field_diff_rows}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / timestamp / DECISIONS_CSV.name
    backup_path.parent.mkdir(parents=True, exist_ok=False)
    shutil.copy2(DECISIONS_CSV, backup_path)

    context_counts: dict[str, int] = {}
    for row in decisions:
        skipped = skipped_by_key.get(key_for_review(row), {})
        field = clean(row.get("Field"))
        reason = clean(row.get("Source Review Reason"))
        line = clean(row.get("Active CSV Line"))

        row["Active Value"] = clean(skipped.get("Active Value"))
        row["Candidate Value"] = clean(skipped.get("Candidate Value"))
        row["Staged Value"] = clean(skipped.get("Staged Value"))
        row["Bold Preference Captured"] = "No - CSV stores text values only, not font formatting."

        if field in {"Genre", "Duration", "Album", "Spotify Verified"}:
            row["Review Context Type"] = "field_conflict"
            diff = field_diff_by_key.get((line, field), {})
            row["Active Value"] = clean(diff.get("Active Value")) or row["Active Value"]
            row["Staged Value"] = clean(diff.get("Staged Value")) or row["Staged Value"]
            active_context = dict(active_by_line.get(line, {}))
            staged_context = dict(staged_by_line.get(clean(diff.get("Staged CSV Line")), {}))
            if field:
                active_context[field] = row["Active Value"]
                staged_context[field] = row["Staged Value"]
            copy_context(row, "Active", active_context)
            copy_context(row, "Staged", staged_context)
        elif field == "__row_signature__" and reason.startswith("active-only"):
            row["Review Context Type"] = "active_only_row_signature"
            copy_context(row, "Active", active_only_by_line.get(line))
            copy_context(row, "Staged", None)
        elif field == "__row_signature__" and reason.startswith("staged-only"):
            row["Review Context Type"] = "staged_only_row_signature"
            copy_context(row, "Active", None)
            copy_context(row, "Staged", staged_only_by_line.get(line))
        elif field == "Spotify Track ID":
            row["Review Context Type"] = "spotify_track_id_conflict"
            copy_context(row, "Active", None)
            copy_context(row, "Staged", None)
        else:
            row["Review Context Type"] = "other"
            copy_context(row, "Active", None)
            copy_context(row, "Staged", None)

        context_counts[row["Review Context Type"]] = context_counts.get(row["Review Context Type"], 0) + 1

    fields = list(decision_fields)
    for column in ADDED_COLUMNS:
        if column not in fields:
            fields.append(column)
    write_csv(DECISIONS_CSV, fields, decisions)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decisions_csv": str(DECISIONS_CSV),
        "backup_path": str(backup_path),
        "rows": len(decisions),
        "context_counts": dict(sorted(context_counts.items())),
        "added_columns": ADDED_COLUMNS,
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    print(json.dumps(enrich(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a non-destructive patch candidate for MusicDB issue #3.

The active main CSV remains the source of truth. This script creates a staged
candidate that:
- keeps the same rows as the active DB
- adds staged legacy provenance columns
- copies safe active Spotify ID values into Spotify Track ID
- copies staged-only metadata values only for unambiguous song-key matches
- never overwrites a nonblank active value
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
ACTIVE_CSV = PROJECT_DIR / "data" / "processed" / "Main_Song_Database.csv"
STAGED_CSV = PROJECT_DIR / "data" / "staging" / "d_music_legacy_merge" / "merged_candidate_Main_Song_Database.csv"
REVIEW_DIR = PROJECT_DIR / "data" / "exports" / "active_vs_staged_review"
SPOTIFY_NORMALIZATION_CSV = REVIEW_DIR / "spotify_id_normalization_review.csv"
FIELD_DIFFS_CSV = REVIEW_DIR / "field_differences_unambiguous_song_keys.csv"
ACTIVE_ONLY_CSV = REVIEW_DIR / "active_only_rows.csv"
STAGED_ONLY_CSV = REVIEW_DIR / "staged_only_rows.csv"
OUT_STAGING = PROJECT_DIR / "data" / "staging" / "codex"
OUT_EXPORTS = PROJECT_DIR / "data" / "exports" / "codex"
DOC_REPORT = PROJECT_DIR / "docs" / "codex_issue_3_patch_candidate.md"

LEGACY_PROVENANCE_COLUMNS = [
    "Legacy D Music Spotify ID",
    "Legacy D Music Verification Notes",
    "Legacy D Music Source Files",
]

AUTO_STAGED_ONLY_FIELDS = {
    "MusicBrainz Verified",
    "Spotify Track ID",
    "Energy",
    "Vibe",
    "BPM",
    "Spotify Verified",
    "Genre",
}

PATCH_CANDIDATE = OUT_STAGING / "active_main_patch_candidate.csv"
PATCH_ACTIONS = OUT_EXPORTS / "active_main_patch_actions.csv"
SKIPPED_REVIEW = OUT_EXPORTS / "active_main_patch_skipped_review.csv"
SUMMARY_JSON = OUT_EXPORTS / "active_main_patch_summary.json"
VERIFICATION_JSON = OUT_EXPORTS / "active_main_patch_verification.json"


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def norm(value: object) -> str:
    value = clean(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[’‘`']", "", value)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"\b(feat|featuring|ft)\.?\b.*$", "", value)
    value = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", value)
    value = re.sub(r"\bthe\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def song_key(row: dict[str, str]) -> tuple[str, str]:
    title = row.get("Base Title") or row.get("Title")
    return (norm(title), norm(row.get("Artist")))


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [dict(row) for row in reader]
    return list(reader.fieldnames or []), rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_dicts(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add_action(
    actions: list[dict[str, str]],
    active_line: int,
    title: str,
    artist: str,
    field: str,
    old_value: str,
    new_value: str,
    action_type: str,
    reason: str,
    source: str,
) -> None:
    actions.append(
        {
            "Active CSV Line": str(active_line),
            "Title": title,
            "Artist": artist,
            "Field": field,
            "Old Value": old_value,
            "New Value": new_value,
            "Action Type": action_type,
            "Reason": reason,
            "Source": source,
        }
    )


def add_skip(
    skips: list[dict[str, str]],
    active_line: str,
    title: str,
    artist: str,
    field: str,
    active_value: str,
    candidate_value: str,
    staged_value: str,
    reason: str,
    source: str,
) -> None:
    skips.append(
        {
            "Active CSV Line": active_line,
            "Title": title,
            "Artist": artist,
            "Field": field,
            "Active Value": active_value,
            "Candidate Value": candidate_value,
            "Staged Value": staged_value,
            "Reason": reason,
            "Source": source,
        }
    )


def main() -> int:
    active_sha_before = sha256(ACTIVE_CSV)
    active_headers, active_rows = read_csv(ACTIVE_CSV)
    staged_headers, staged_rows = read_csv(STAGED_CSV)
    spotify_review = read_dicts(SPOTIFY_NORMALIZATION_CSV)
    field_diffs = read_dicts(FIELD_DIFFS_CSV)

    candidate_headers = list(active_headers)
    for column in LEGACY_PROVENANCE_COLUMNS:
        if column not in candidate_headers:
            candidate_headers.append(column)

    candidate_rows = [dict(row) for row in active_rows]
    for row in candidate_rows:
        for column in candidate_headers:
            row.setdefault(column, "")

    actions: list[dict[str, str]] = []
    skips: list[dict[str, str]] = []
    action_counts: Counter[str] = Counter()
    field_action_counts: Counter[str] = Counter()

    # Active CSV line numbers are 1-based and include the header row.
    active_by_line = {str(index + 2): row for index, row in enumerate(candidate_rows)}
    active_original_by_line = {str(index + 2): row for index, row in enumerate(active_rows)}

    # 1. Safe active Spotify ID -> Spotify Track ID normalization.
    for review in spotify_review:
        if clean(review.get("Status")) != "safe_to_copy_spotify_id_to_spotify_track_id":
            continue
        line = clean(review.get("Active CSV Line"))
        row = active_by_line.get(line)
        if row is None:
            continue
        spotify_id = clean(review.get("Spotify ID"))
        current_track_id = clean(row.get("Spotify Track ID"))
        if not spotify_id:
            continue
        if current_track_id:
            add_skip(
                skips,
                line,
                clean(row.get("Title")),
                clean(row.get("Artist")),
                "Spotify Track ID",
                clean(active_original_by_line.get(line, {}).get("Spotify Track ID")),
                current_track_id,
                spotify_id,
                "candidate already has Spotify Track ID",
                str(SPOTIFY_NORMALIZATION_CSV),
            )
            continue
        row["Spotify Track ID"] = spotify_id
        add_action(
            actions,
            int(line),
            clean(row.get("Title")),
            clean(row.get("Artist")),
            "Spotify Track ID",
            "",
            spotify_id,
            "safe_spotify_id_normalization",
            "active Spotify ID has valid track-id shape and active Spotify Track ID is blank",
            str(SPOTIFY_NORMALIZATION_CSV),
        )
        action_counts["safe_spotify_id_normalization"] += 1
        field_action_counts["Spotify Track ID"] += 1

    # 2. Staged provenance columns for unambiguous song-key matches only.
    active_by_key: dict[tuple[str, str], list[tuple[int, dict[str, str]]]] = defaultdict(list)
    staged_by_key: dict[tuple[str, str], list[tuple[int, dict[str, str]]]] = defaultdict(list)
    for index, row in enumerate(candidate_rows, start=2):
        active_by_key[song_key(row)].append((index, row))
    for index, row in enumerate(staged_rows, start=2):
        staged_by_key[song_key(row)].append((index, row))

    unambiguous_keys = [
        key
        for key in sorted(set(active_by_key) & set(staged_by_key))
        if len(active_by_key[key]) == 1 and len(staged_by_key[key]) == 1
    ]

    for key in unambiguous_keys:
        active_line, active_row = active_by_key[key][0]
        _, staged_row = staged_by_key[key][0]
        for column in LEGACY_PROVENANCE_COLUMNS:
            staged_value = clean(staged_row.get(column))
            if not staged_value:
                continue
            current_value = clean(active_row.get(column))
            if current_value:
                continue
            active_row[column] = staged_value
            add_action(
                actions,
                active_line,
                clean(active_row.get("Title")),
                clean(active_row.get("Artist")),
                column,
                "",
                staged_value,
                "staged_provenance_copy",
                "unambiguous song-key match and active provenance field is blank",
                str(STAGED_CSV),
            )
            action_counts["staged_provenance_copy"] += 1
            field_action_counts[column] += 1

    # 3. Staged-only metadata values for unambiguous song keys and allowlisted fields.
    for diff in field_diffs:
        if clean(diff.get("Difference Type")) != "staged_only_value":
            continue
        field = clean(diff.get("Field"))
        if field not in AUTO_STAGED_ONLY_FIELDS:
            continue
        line = clean(diff.get("Active CSV Line"))
        row = active_by_line.get(line)
        if row is None:
            continue
        staged_value = clean(diff.get("Staged Value"))
        if not staged_value:
            continue
        original_value = clean(active_original_by_line.get(line, {}).get(field))
        candidate_value = clean(row.get(field))
        if candidate_value:
            if candidate_value != staged_value:
                add_skip(
                    skips,
                    line,
                    clean(row.get("Title")),
                    clean(row.get("Artist")),
                    field,
                    original_value,
                    candidate_value,
                    staged_value,
                    "candidate field no longer blank after earlier safe patch; not overwriting",
                    str(FIELD_DIFFS_CSV),
                )
            continue
        row[field] = staged_value
        add_action(
            actions,
            int(line),
            clean(row.get("Title")),
            clean(row.get("Artist")),
            field,
            original_value,
            staged_value,
            "staged_only_metadata_copy",
            "unambiguous song-key match, staged-only value, active field blank, allowlisted field",
            str(FIELD_DIFFS_CSV),
        )
        action_counts["staged_only_metadata_copy"] += 1
        field_action_counts[field] += 1

    # 4. Review-only skip tables for known risky areas.
    spotify_conflicts = [
        row
        for row in spotify_review
        if clean(row.get("Status")) == "conflict_spotify_id_differs_from_track_id"
    ]
    for conflict in spotify_conflicts:
        add_skip(
            skips,
            clean(conflict.get("Active CSV Line")),
            clean(conflict.get("Title")),
            clean(conflict.get("Artist")),
            "Spotify Track ID",
            clean(conflict.get("Spotify Track ID")),
            clean(conflict.get("Spotify Track ID")),
            clean(conflict.get("Spotify ID")),
            "active Spotify ID differs from active Spotify Track ID; manual review required",
            str(SPOTIFY_NORMALIZATION_CSV),
        )

    for diff in field_diffs:
        if clean(diff.get("Difference Type")) != "conflict_both_nonblank":
            continue
        add_skip(
            skips,
            clean(diff.get("Active CSV Line")),
            clean(diff.get("Title")),
            clean(diff.get("Artist")),
            clean(diff.get("Field")),
            clean(diff.get("Active Value")),
            clean(diff.get("Active Value")),
            clean(diff.get("Staged Value")),
            "both active and staged have nonblank conflicting values; manual review required",
            str(FIELD_DIFFS_CSV),
        )

    # These are row-signature differences, not safe cell patches.
    for path, reason in [
        (ACTIVE_ONLY_CSV, "active-only row signature; no deletion proposed"),
        (STAGED_ONLY_CSV, "staged-only row signature; no append proposed"),
    ]:
        for row in read_dicts(path):
            add_skip(
                skips,
                clean(row.get("CSV Line")),
                clean(row.get("Title")),
                clean(row.get("Artist")),
                "__row_signature__",
                "",
                "",
                clean(row.get("Comparison Key")),
                reason,
                str(path),
            )

    write_csv(PATCH_CANDIDATE, candidate_headers, candidate_rows)
    action_fields = [
        "Active CSV Line",
        "Title",
        "Artist",
        "Field",
        "Old Value",
        "New Value",
        "Action Type",
        "Reason",
        "Source",
    ]
    skip_fields = [
        "Active CSV Line",
        "Title",
        "Artist",
        "Field",
        "Active Value",
        "Candidate Value",
        "Staged Value",
        "Reason",
        "Source",
    ]
    write_csv(PATCH_ACTIONS, action_fields, actions)
    write_csv(SKIPPED_REVIEW, skip_fields, skips)

    overwrite_violations = []
    for action in actions:
        line = int(action["Active CSV Line"])
        field = action["Field"]
        active_value = clean(active_rows[line - 2].get(field)) if field in active_headers else ""
        logged_old_value = clean(action["Old Value"])
        if active_value != logged_old_value:
            overwrite_violations.append(
                {
                    "line": line,
                    "field": field,
                    "active_value": active_value,
                    "logged_old_value": logged_old_value,
                }
            )
        if field in active_headers and active_value and active_value != clean(action["New Value"]):
            overwrite_violations.append(
                {
                    "line": line,
                    "field": field,
                    "active_value": active_value,
                    "new_value": clean(action["New Value"]),
                    "reason": "action would overwrite nonblank active value",
                }
            )

    staged_spotify_track_diffs = [
        diff
        for diff in field_diffs
        if clean(diff.get("Field")) == "Spotify Track ID"
        and clean(diff.get("Difference Type")) == "staged_only_value"
    ]
    represented_staged_spotify_track_ids = 0
    mismatched_staged_spotify_track_ids = []
    for diff in staged_spotify_track_diffs:
        line = int(clean(diff.get("Active CSV Line")))
        candidate_value = clean(candidate_rows[line - 2].get("Spotify Track ID"))
        staged_value = clean(diff.get("Staged Value"))
        if candidate_value == staged_value:
            represented_staged_spotify_track_ids += 1
        else:
            mismatched_staged_spotify_track_ids.append(
                {
                    "line": line,
                    "title": clean(diff.get("Title")),
                    "artist": clean(diff.get("Artist")),
                    "candidate_value": candidate_value,
                    "staged_value": staged_value,
                }
            )

    verification = {
        "overwrite_violations": len(overwrite_violations),
        "sample_overwrite_violations": overwrite_violations[:10],
        "staged_only_spotify_track_id_diffs": len(staged_spotify_track_diffs),
        "staged_spotify_track_ids_represented_in_candidate": represented_staged_spotify_track_ids,
        "staged_spotify_track_id_mismatches": len(mismatched_staged_spotify_track_ids),
        "sample_staged_spotify_track_id_mismatches": mismatched_staged_spotify_track_ids[:10],
    }

    active_sha_after = sha256(ACTIVE_CSV)
    candidate_sha = sha256(PATCH_CANDIDATE)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "active_csv": str(ACTIVE_CSV),
        "staged_csv": str(STAGED_CSV),
        "active_sha_before": active_sha_before,
        "active_sha_after": active_sha_after,
        "active_database_modified": active_sha_before != active_sha_after,
        "patch_candidate_csv": str(PATCH_CANDIDATE),
        "patch_candidate_sha256": candidate_sha,
        "patch_actions_csv": str(PATCH_ACTIONS),
        "skipped_review_csv": str(SKIPPED_REVIEW),
        "verification_json": str(VERIFICATION_JSON),
        "active_rows": len(active_rows),
        "candidate_rows": len(candidate_rows),
        "active_columns": len(active_headers),
        "candidate_columns": len(candidate_headers),
        "added_columns": [column for column in candidate_headers if column not in active_headers],
        "unambiguous_song_keys_used_for_provenance": len(unambiguous_keys),
        "patch_action_count": len(actions),
        "skipped_review_count": len(skips),
        "action_counts": dict(sorted(action_counts.items())),
        "field_action_counts": dict(sorted(field_action_counts.items())),
        "manual_review_inputs": {
            "spotify_conflict_rows": len(spotify_conflicts),
            "active_only_rows": len(read_dicts(ACTIVE_ONLY_CSV)),
            "staged_only_rows": len(read_dicts(STAGED_ONLY_CSV)),
        },
        "verification": verification,
    }
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    VERIFICATION_JSON.write_text(json.dumps(verification, indent=2), encoding="utf-8")
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report_lines = [
        "# Codex Issue #3 Patch Candidate",
        "",
        f"Generated: {summary['generated_at']}",
        "",
        "## Inputs",
        "",
        f"- Active DB: `{ACTIVE_CSV}`",
        f"- Staged candidate: `{STAGED_CSV}`",
        f"- Spotify review: `{SPOTIFY_NORMALIZATION_CSV}`",
        f"- Field differences: `{FIELD_DIFFS_CSV}`",
        "",
        "## Outputs",
        "",
        f"- Patch candidate: `{PATCH_CANDIDATE}`",
        f"- Patch actions: `{PATCH_ACTIONS}`",
        f"- Skipped/manual-review rows: `{SKIPPED_REVIEW}`",
        f"- Summary JSON: `{SUMMARY_JSON}`",
        f"- Verification JSON: `{VERIFICATION_JSON}`",
        "",
        "## Safety",
        "",
        f"- Active DB modified: `{summary['active_database_modified']}`",
        f"- Active SHA before: `{active_sha_before}`",
        f"- Active SHA after: `{active_sha_after}`",
        f"- Overwrite violations: {verification['overwrite_violations']:,}",
        f"- Staged-only Spotify Track IDs represented in candidate: {represented_staged_spotify_track_ids:,} / {len(staged_spotify_track_diffs):,}",
        f"- Staged-only Spotify Track ID mismatches: {verification['staged_spotify_track_id_mismatches']:,}",
        "",
        "## Candidate Shape",
        "",
        f"- Active rows: {len(active_rows):,}",
        f"- Candidate rows: {len(candidate_rows):,}",
        f"- Active columns: {len(active_headers):,}",
        f"- Candidate columns: {len(candidate_headers):,}",
        f"- Added columns: {', '.join(summary['added_columns'])}",
        "",
        "## Patch Actions",
        "",
        f"- Total proposed cell/field actions: {len(actions):,}",
        "",
        "| Action Type | Count |",
        "| --- | ---: |",
    ]
    for action_type, count in sorted(action_counts.items()):
        report_lines.append(f"| {action_type} | {count:,} |")
    report_lines.extend(["", "| Field | Count |", "| --- | ---: |"])
    for field, count in sorted(field_action_counts.items(), key=lambda item: (-item[1], item[0])):
        report_lines.append(f"| {field} | {count:,} |")
    report_lines.extend(
        [
            "",
            "## Left For Manual Review",
            "",
            f"- Skipped/manual-review entries: {len(skips):,}",
            f"- Active Spotify ID conflicts: {len(spotify_conflicts):,}",
            f"- Active-only row signatures: {len(read_dicts(ACTIVE_ONLY_CSV)):,}",
            f"- Staged-only row signatures: {len(read_dicts(STAGED_ONLY_CSV)):,}",
            "",
            "## Recommendation",
            "",
            "Review the patch actions and skipped-review CSVs before any promotion. If accepted, promote with a separate script that first creates a timestamped backup of `data/processed/Main_Song_Database.csv`.",
            "",
        ]
    )
    DOC_REPORT.write_text("\n".join(report_lines), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

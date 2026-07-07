#!/usr/bin/env python3
"""Compare the active MusicDB main CSV against the conservative staged candidate.

This script is read-only. It writes review reports under data/exports.
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
OUT_DIR = PROJECT_DIR / "data" / "exports" / "active_vs_staged_review"
DOC_REPORT = PROJECT_DIR / "docs" / "active_vs_staged_review_report.md"

IMPORTANT_FIELDS = [
    "Title",
    "Base Title",
    "Artist",
    "Album",
    "Duration",
    "Genre",
    "Year",
    "Original Artist",
    "Cover Song",
    "Orig Artist",
    "Covering Artist",
    "Source Files",
    "Playlists",
    "Original Data",
    "Energy",
    "BPM",
    "Vibe",
    "Discogs Verified",
    "Spotify Verified",
    "MusicBrainz Verified",
    "iTunes Verified",
    "Spotify ID",
    "Legacy D Music Spotify ID",
    "Spotify Track ID",
    "Spotify Popularity",
    "Spotify ISRC",
    "Spotify Album",
    "Spotify Release Date",
    "Spotify Duration (ms)",
    "Spotify MusicBrainz ID",
    "Spotify BPM",
    "Spotify Key Full",
    "Spotify Energy Level",
    "Spotify Danceability",
    "Spotify Genre",
    "Spotify LastFM Tags",
    "Spotify Vibe",
    "Alternate Albums",
    "Duplicate Merge Notes",
    "Legacy D Music Verification Notes",
    "Legacy D Music Source Files",
]

CONFLICT_FIELDS = [
    "Album",
    "Duration",
    "Genre",
    "Year",
    "Energy",
    "BPM",
    "Vibe",
    "Discogs Verified",
    "Spotify Verified",
    "MusicBrainz Verified",
    "iTunes Verified",
    "Spotify Track ID",
    "Spotify Popularity",
    "Spotify ISRC",
    "Spotify Album",
    "Spotify Release Date",
    "Spotify Duration (ms)",
    "Spotify MusicBrainz ID",
    "Spotify BPM",
    "Spotify Key Full",
    "Playlists",
    "Alternate Albums",
    "Duplicate Merge Notes",
]


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


def compact_duration(value: object) -> str:
    value = clean(value)
    if not value:
        return ""
    match = re.fullmatch(r"(\d+):(\d{2})", value)
    if match:
        return f"{int(match.group(1))}:{match.group(2)}"
    return norm(value)


def numeric_string(value: str) -> str | None:
    value = clean(value)
    if not value:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    if number.is_integer():
        return str(int(number))
    return str(number)


def duration_seconds(value: str) -> str | None:
    value = clean(value)
    if not value:
        return None
    parts = value.split(":")
    if len(parts) not in {2, 3} or not all(part.isdigit() for part in parts):
        return None
    nums = [int(part) for part in parts]
    if len(nums) == 2:
        return str(nums[0] * 60 + nums[1])
    return str(nums[0] * 3600 + nums[1] * 60 + nums[2])


def comparable_value(field: str, value: str) -> str:
    value = clean(value)
    if not value:
        return ""
    if field in {"Year", "Spotify Release Date"}:
        match = re.search(r"\b(19\d{2}|20\d{2})\b", value)
        return match.group(1) if match else value
    if field in {"Duration"}:
        return duration_seconds(value) or value
    if field in {"BPM", "Spotify BPM", "Spotify Popularity", "Spotify Duration (ms)", "Spotify Match Score"}:
        return numeric_string(value) or value
    if field in {"Spotify Verified", "MusicBrainz Verified", "Discogs Verified", "iTunes Verified"}:
        return value.lower()
    if field in {"Album", "Genre", "Spotify Album", "Spotify Genre", "Spotify Energy Level", "Spotify Vibe", "Vibe", "Energy"}:
        return norm(value)
    return value


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [dict(row) for row in reader]
    for idx, row in enumerate(rows, start=2):
        row["_csv_line"] = str(idx)
    return list(reader.fieldnames or []), rows


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def song_key(row: dict[str, str]) -> tuple[str, str]:
    title = row.get("Base Title") or row.get("Title")
    return (norm(title), norm(row.get("Artist")))


def row_signature(row: dict[str, str]) -> tuple[str, str, str, str]:
    title, artist = song_key(row)
    return (title, artist, norm(row.get("Album")), compact_duration(row.get("Duration")))


def display_value(row: dict[str, str], field: str) -> str:
    if field == "Legacy D Music Spotify ID":
        return clean(row.get("Legacy D Music Spotify ID"))
    return clean(row.get(field))


def compact_row(row: dict[str, str], source: str, key_value: tuple[str, ...]) -> dict[str, str]:
    out = {
        "Source": source,
        "Comparison Key": " || ".join(key_value),
        "CSV Line": row.get("_csv_line", ""),
    }
    for field in IMPORTANT_FIELDS:
        if field in row:
            out[field] = clean(row.get(field))
    return out


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        seen = set()
        for row in rows:
            for field in row:
                if field not in seen:
                    seen.add(field)
                    fieldnames.append(field)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def spotify_id_status(row: dict[str, str]) -> str:
    spotify_id = clean(row.get("Spotify ID"))
    spotify_track_id = clean(row.get("Spotify Track ID"))
    looks_like_track = bool(re.fullmatch(r"[A-Za-z0-9]{22}", spotify_id))
    if not spotify_id:
        return "no_legacy_spotify_id"
    if spotify_track_id and spotify_id == spotify_track_id:
        return "already_same"
    if spotify_track_id and spotify_id != spotify_track_id:
        return "conflict_spotify_id_differs_from_track_id"
    if not looks_like_track:
        return "needs_review_invalid_spotify_id_shape"
    return "safe_to_copy_spotify_id_to_spotify_track_id"


def main() -> int:
    active_headers, active_rows = read_csv(ACTIVE_CSV)
    staged_headers, staged_rows = read_csv(STAGED_CSV)

    active_only_columns = [col for col in active_headers if col not in staged_headers]
    staged_only_columns = [col for col in staged_headers if col not in active_headers]

    active_by_sig: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    staged_by_sig: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    active_by_song: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    staged_by_song: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in active_rows:
        active_by_sig[row_signature(row)].append(row)
        active_by_song[song_key(row)].append(row)
    for row in staged_rows:
        staged_by_sig[row_signature(row)].append(row)
        staged_by_song[song_key(row)].append(row)

    all_signatures = sorted(set(active_by_sig) | set(staged_by_sig))
    active_only_rows: list[dict[str, str]] = []
    staged_only_rows: list[dict[str, str]] = []
    signature_count_diffs: list[dict[str, str]] = []
    for sig in all_signatures:
        active_count = len(active_by_sig.get(sig, []))
        staged_count = len(staged_by_sig.get(sig, []))
        if active_count != staged_count:
            signature_count_diffs.append(
                {
                    "Comparison Key": " || ".join(sig),
                    "Active Count": str(active_count),
                    "Staged Count": str(staged_count),
                    "Delta Active Minus Staged": str(active_count - staged_count),
                }
            )
        if active_count > staged_count:
            for row in active_by_sig[sig][staged_count:]:
                active_only_rows.append(compact_row(row, "active_only", sig))
        elif staged_count > active_count:
            for row in staged_by_sig[sig][active_count:]:
                staged_only_rows.append(compact_row(row, "staged_only", sig))

    all_song_keys = sorted(set(active_by_song) | set(staged_by_song))
    unambiguous_keys = [
        key for key in all_song_keys if len(active_by_song.get(key, [])) == 1 and len(staged_by_song.get(key, [])) == 1
    ]
    active_duplicate_keys = [key for key, rows in active_by_song.items() if len(rows) > 1]
    staged_duplicate_keys = [key for key, rows in staged_by_song.items() if len(rows) > 1]
    missing_song_keys_active = [key for key in all_song_keys if key not in staged_by_song]
    missing_song_keys_staged = [key for key in all_song_keys if key not in active_by_song]

    field_differences: list[dict[str, str]] = []
    difference_counts: Counter[tuple[str, str]] = Counter()
    for key in unambiguous_keys:
        active = active_by_song[key][0]
        staged = staged_by_song[key][0]
        for field in CONFLICT_FIELDS:
            active_value = clean(active.get(field))
            staged_value = clean(staged.get(field))
            if not active_value and not staged_value:
                continue
            if comparable_value(field, active_value) == comparable_value(field, staged_value):
                continue
            if active_value and staged_value:
                difference_type = "conflict_both_nonblank"
            elif active_value and not staged_value:
                difference_type = "active_only_value"
            else:
                difference_type = "staged_only_value"
            difference_counts[(field, difference_type)] += 1
            field_differences.append(
                {
                    "Song Key": " || ".join(key),
                    "Active CSV Line": active.get("_csv_line", ""),
                    "Staged CSV Line": staged.get("_csv_line", ""),
                    "Title": clean(active.get("Title") or staged.get("Title")),
                    "Artist": clean(active.get("Artist") or staged.get("Artist")),
                    "Field": field,
                    "Difference Type": difference_type,
                    "Active Value": active_value,
                    "Staged Value": staged_value,
                }
            )

    spotify_normalization: list[dict[str, str]] = []
    spotify_status_counts: Counter[str] = Counter()
    for row in active_rows:
        status = spotify_id_status(row)
        spotify_status_counts[status] += 1
        if status != "no_legacy_spotify_id":
            spotify_normalization.append(
                {
                    "Status": status,
                    "Active CSV Line": row.get("_csv_line", ""),
                    "Title": clean(row.get("Title")),
                    "Artist": clean(row.get("Artist")),
                    "Album": clean(row.get("Album")),
                    "Spotify ID": clean(row.get("Spotify ID")),
                    "Spotify Track ID": clean(row.get("Spotify Track ID")),
                }
            )

    matched_spotify_conflicts: list[dict[str, str]] = []
    for key in unambiguous_keys:
        active = active_by_song[key][0]
        staged = staged_by_song[key][0]
        active_candidates = {
            value for value in [clean(active.get("Spotify ID")), clean(active.get("Spotify Track ID"))] if value
        }
        staged_candidates = {
            value
            for value in [clean(staged.get("Spotify Track ID")), clean(staged.get("Legacy D Music Spotify ID"))]
            if value
        }
        if active_candidates and staged_candidates and active_candidates.isdisjoint(staged_candidates):
            matched_spotify_conflicts.append(
                {
                    "Song Key": " || ".join(key),
                    "Active CSV Line": active.get("_csv_line", ""),
                    "Staged CSV Line": staged.get("_csv_line", ""),
                    "Title": clean(active.get("Title") or staged.get("Title")),
                    "Artist": clean(active.get("Artist") or staged.get("Artist")),
                    "Active Spotify ID": clean(active.get("Spotify ID")),
                    "Active Spotify Track ID": clean(active.get("Spotify Track ID")),
                    "Staged Spotify Track ID": clean(staged.get("Spotify Track ID")),
                    "Staged Legacy D Music Spotify ID": clean(staged.get("Legacy D Music Spotify ID")),
                }
            )

    duplicate_group_rows: list[dict[str, str]] = []
    for key in sorted(set(active_duplicate_keys) | set(staged_duplicate_keys)):
        active_examples = active_by_song.get(key, [])
        staged_examples = staged_by_song.get(key, [])
        duplicate_group_rows.append(
            {
                "Song Key": " || ".join(key),
                "Active Count": str(len(active_examples)),
                "Staged Count": str(len(staged_examples)),
                "Active Lines": "; ".join(row.get("_csv_line", "") for row in active_examples[:20]),
                "Staged Lines": "; ".join(row.get("_csv_line", "") for row in staged_examples[:20]),
                "Active Sample": " | ".join(
                    clean(active_examples[0].get(field)) if active_examples else ""
                    for field in ["Title", "Artist", "Album", "Duration"]
                ),
                "Staged Sample": " | ".join(
                    clean(staged_examples[0].get(field)) if staged_examples else ""
                    for field in ["Title", "Artist", "Album", "Duration"]
                ),
            }
        )

    field_difference_summary = [
        {"Field": field, "Difference Type": dtype, "Count": str(count)}
        for (field, dtype), count in sorted(difference_counts.items())
    ]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUT_DIR / "active_only_rows.csv", active_only_rows)
    write_csv(OUT_DIR / "staged_only_rows.csv", staged_only_rows)
    write_csv(OUT_DIR / "signature_count_differences.csv", signature_count_diffs)
    write_csv(OUT_DIR / "field_differences_unambiguous_song_keys.csv", field_differences)
    write_csv(OUT_DIR / "field_difference_summary.csv", field_difference_summary)
    write_csv(OUT_DIR / "spotify_id_normalization_review.csv", spotify_normalization)
    write_csv(OUT_DIR / "spotify_id_conflicts_between_active_and_staged.csv", matched_spotify_conflicts)
    write_csv(OUT_DIR / "duplicate_song_key_groups.csv", duplicate_group_rows)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "active_csv": str(ACTIVE_CSV),
        "staged_csv": str(STAGED_CSV),
        "active_sha256": sha256(ACTIVE_CSV),
        "staged_sha256": sha256(STAGED_CSV),
        "active_rows": len(active_rows),
        "staged_rows": len(staged_rows),
        "active_columns": len(active_headers),
        "staged_columns": len(staged_headers),
        "active_only_columns": active_only_columns,
        "staged_only_columns": staged_only_columns,
        "row_count_delta_active_minus_staged": len(active_rows) - len(staged_rows),
        "active_only_row_signatures": len(active_only_rows),
        "staged_only_row_signatures": len(staged_only_rows),
        "signature_count_difference_groups": len(signature_count_diffs),
        "unique_song_keys_active": len(active_by_song),
        "unique_song_keys_staged": len(staged_by_song),
        "unambiguous_song_keys_compared": len(unambiguous_keys),
        "song_keys_only_in_active": len(missing_song_keys_active),
        "song_keys_only_in_staged": len(missing_song_keys_staged),
        "active_duplicate_song_key_groups": len(active_duplicate_keys),
        "staged_duplicate_song_key_groups": len(staged_duplicate_keys),
        "duplicate_song_key_groups_total": len(duplicate_group_rows),
        "field_differences_unambiguous": len(field_differences),
        "spotify_status_counts_active": dict(sorted(spotify_status_counts.items())),
        "spotify_id_conflicts_between_active_and_staged": len(matched_spotify_conflicts),
        "outputs": {
            "active_only_rows": str(OUT_DIR / "active_only_rows.csv"),
            "staged_only_rows": str(OUT_DIR / "staged_only_rows.csv"),
            "signature_count_differences": str(OUT_DIR / "signature_count_differences.csv"),
            "field_differences": str(OUT_DIR / "field_differences_unambiguous_song_keys.csv"),
            "field_difference_summary": str(OUT_DIR / "field_difference_summary.csv"),
            "spotify_normalization": str(OUT_DIR / "spotify_id_normalization_review.csv"),
            "spotify_conflicts": str(OUT_DIR / "spotify_id_conflicts_between_active_and_staged.csv"),
            "duplicate_song_key_groups": str(OUT_DIR / "duplicate_song_key_groups.csv"),
            "markdown_report": str(DOC_REPORT),
        },
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    top_field_diffs = sorted(difference_counts.items(), key=lambda item: (-item[1], item[0]))[:20]
    report = [
        "# Active vs Staged MusicDB Review Report",
        "",
        f"Generated: {summary['generated_at']}",
        "",
        "## Files Compared",
        "",
        f"- Active main DB: `{ACTIVE_CSV}`",
        f"- Staged conservative candidate: `{STAGED_CSV}`",
        "",
        "## Snapshot Evidence",
        "",
        f"- Active rows: {len(active_rows):,}",
        f"- Staged rows: {len(staged_rows):,}",
        f"- Active columns: {len(active_headers):,}",
        f"- Staged columns: {len(staged_headers):,}",
        f"- Active SHA256: `{summary['active_sha256']}`",
        f"- Staged SHA256: `{summary['staged_sha256']}`",
        "",
        "## Schema Differences",
        "",
        f"- Active-only columns: {', '.join(active_only_columns) if active_only_columns else 'none'}",
        f"- Staged-only columns: {', '.join(staged_only_columns) if staged_only_columns else 'none'}",
        "",
        "## Row-Level Findings",
        "",
        f"- Row-count delta, active minus staged: {len(active_rows) - len(staged_rows):,}",
        f"- Active-only row signatures: {len(active_only_rows):,}",
        f"- Staged-only row signatures: {len(staged_only_rows):,}",
        f"- Signature count difference groups: {len(signature_count_diffs):,}",
        f"- Song keys only in active: {len(missing_song_keys_active):,}",
        f"- Song keys only in staged: {len(missing_song_keys_staged):,}",
        f"- Active duplicate song-key groups: {len(active_duplicate_keys):,}",
        f"- Staged duplicate song-key groups: {len(staged_duplicate_keys):,}",
        "",
        "## Unambiguous Song-Key Comparison",
        "",
        f"- Unambiguous song keys compared: {len(unambiguous_keys):,}",
        f"- Field differences in unambiguous matches: {len(field_differences):,}",
        "",
        "Top field-difference counts:",
        "",
    ]
    if top_field_diffs:
        report.append("| Field | Difference Type | Count |")
        report.append("| --- | --- | ---: |")
        for (field, dtype), count in top_field_diffs:
            report.append(f"| {field} | {dtype} | {count:,} |")
    else:
        report.append("No field differences found in unambiguous matches.")

    report.extend(
        [
            "",
            "## Spotify ID Review",
            "",
            "| Status | Count |",
            "| --- | ---: |",
        ]
    )
    for status, count in sorted(spotify_status_counts.items()):
        report.append(f"| {status} | {count:,} |")
    report.extend(
        [
            "",
            f"- Spotify ID conflicts between unambiguous active/staged matches: {len(matched_spotify_conflicts):,}",
            "",
            "## Output Tables",
            "",
            f"- `data/exports/active_vs_staged_review/active_only_rows.csv`",
            f"- `data/exports/active_vs_staged_review/staged_only_rows.csv`",
            f"- `data/exports/active_vs_staged_review/signature_count_differences.csv`",
            f"- `data/exports/active_vs_staged_review/field_differences_unambiguous_song_keys.csv`",
            f"- `data/exports/active_vs_staged_review/field_difference_summary.csv`",
            f"- `data/exports/active_vs_staged_review/spotify_id_normalization_review.csv`",
            f"- `data/exports/active_vs_staged_review/spotify_id_conflicts_between_active_and_staged.csv`",
            f"- `data/exports/active_vs_staged_review/duplicate_song_key_groups.csv`",
            f"- `data/exports/active_vs_staged_review/summary.json`",
            "",
            "## Recommendation",
            "",
            "Do not replace the active database with the staged candidate wholesale.",
            "",
            "The active database has more rows and includes a legacy `Spotify ID` column. The staged candidate has more explicit legacy provenance columns and was produced by a more conservative merge. The safest path is to keep the active database as the current source of truth, then apply targeted improvements from this review:",
            "",
            "1. Normalize safe `Spotify ID` values into `Spotify Track ID` where the review marks them safe.",
            "2. Review active-only and staged-only row signatures before deleting or appending anything.",
            "3. Review both-nonblank conflicts for album, duration, year, and Spotify identifiers before promotion.",
            "4. Preserve the staged candidate's legacy provenance columns in the next canonical schema.",
            "",
            "This report is read-only. No database rows were changed.",
            "",
        ]
    )
    DOC_REPORT.write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

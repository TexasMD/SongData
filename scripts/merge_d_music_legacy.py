#!/usr/bin/env python3
"""Build a non-destructive merged SongDB candidate from the D: legacy database."""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import shutil
import unicodedata
from collections import defaultdict
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
CANONICAL_MAIN = PROJECT_DIR / "data" / "processed" / "Main_Song_Database.csv"
LEGACY_MAIN = Path(r"D:\Music\Main_Song_Database\data\processed\Main_Song_Database.csv")
LEGACY_ROOT = Path(r"D:\Music\Main_Song_Database")
STAGING_DIR = PROJECT_DIR / "data" / "staging" / "d_music_legacy_merge"
RAW_ARCHIVE_DIR = PROJECT_DIR / "data" / "raw" / "d_music_legacy"

LEGACY_SOURCE = "D:\\Music\\Main_Song_Database"
LEGACY_COLUMNS = [
    "Legacy D Music Spotify ID",
    "Legacy D Music Verification Notes",
    "Legacy D Music Source Files",
]


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def norm(value: str) -> str:
    value = clean(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[’‘`']", "", value)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"\b(feat|featuring|ft)\.?\b.*$", "", value)
    value = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", value)
    value = re.sub(r"\bthe\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def key(row: dict[str, str]) -> tuple[str, str]:
    return (norm(row.get("Title") or row.get("Base Title")), norm(row.get("Artist")))


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def add_list(existing: str, addition: str) -> str:
    values: list[str] = []
    for value in [existing, addition]:
        for piece in re.split(r"\s*;\s*|\s*,\s*", clean(value)):
            if piece and piece not in values:
                values.append(piece)
    return "; ".join(values)


def verification_notes(row: dict[str, str]) -> str:
    notes = []
    for field in ["Discogs Verified", "Spotify Verified", "MusicBrainz Verified", "iTunes Verified"]:
        value = clean(row.get(field))
        if value:
            notes.append(f"{field}={value}")
    if clean(row.get("Spotify ID")):
        notes.append("Spotify ID present")
    return "; ".join(notes)


def archive_legacy_inputs() -> list[str]:
    copied = []
    RAW_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    candidates = [
        LEGACY_ROOT / "data" / "processed" / "Main_Song_Database.csv",
        LEGACY_ROOT / "docs" / "musical_dna_analysis.md",
    ]
    candidates.extend(sorted((LEGACY_ROOT / "data" / "raw").glob("*.csv")))
    for src in candidates:
        if not src.exists():
            continue
        rel = src.relative_to(LEGACY_ROOT)
        dst = RAW_ARCHIVE_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(str(dst))
    return copied


def main() -> int:
    canonical_headers, canonical_rows = read_csv(CANONICAL_MAIN)
    legacy_headers, legacy_rows = read_csv(LEGACY_MAIN)

    headers = list(canonical_headers)
    for col in LEGACY_COLUMNS:
        if col not in headers:
            headers.append(col)
    for col in legacy_headers:
        if col == "Spotify ID":
            continue
        if col not in headers:
            headers.append(col)

    for row in canonical_rows:
        for col in headers:
            row.setdefault(col, "")

    canonical_index: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    legacy_index: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in canonical_rows:
        canonical_index[key(row)].append(row)
    for row in legacy_rows:
        legacy_index[key(row)].append(row)

    updated_rows = 0
    appended_rows: list[dict[str, str]] = []
    field_updates: dict[str, int] = defaultdict(int)
    ambiguous_matches = []

    for legacy_key, legacy_matches in legacy_index.items():
        canonical_matches = canonical_index.get(legacy_key, [])
        if not canonical_matches:
            for legacy in legacy_matches:
                new_row = {col: "" for col in headers}
                for col in legacy_headers:
                    if col == "Spotify ID":
                        continue
                    new_row[col] = clean(legacy.get(col))
                if clean(legacy.get("Spotify ID")):
                    new_row["Legacy D Music Spotify ID"] = clean(legacy.get("Spotify ID"))
                    if not clean(new_row.get("Spotify Track ID")):
                        new_row["Spotify Track ID"] = clean(legacy.get("Spotify ID"))
                new_row["Source Files"] = add_list(new_row.get("Source Files", ""), LEGACY_SOURCE)
                new_row["Legacy D Music Source Files"] = clean(legacy.get("Source Files"))
                new_row["Legacy D Music Verification Notes"] = verification_notes(legacy)
                appended_rows.append(new_row)
            continue

        if len(canonical_matches) != 1 or len(legacy_matches) != 1:
            ambiguous_matches.append(
                {
                    "key": " | ".join(legacy_key),
                    "canonical_count": len(canonical_matches),
                    "legacy_count": len(legacy_matches),
                    "legacy_sample": f"{legacy_matches[0].get('Title', '')} / {legacy_matches[0].get('Artist', '')}",
                }
            )
            continue

        canonical = canonical_matches[0]
        legacy = legacy_matches[0]
        changed = False

        for col in legacy_headers:
            if col == "Spotify ID":
                continue
            value = clean(legacy.get(col))
            if value and not clean(canonical.get(col)):
                canonical[col] = value
                field_updates[col] += 1
                changed = True

        spotify_id = clean(legacy.get("Spotify ID"))
        if spotify_id:
            if not clean(canonical.get("Spotify Track ID")):
                canonical["Spotify Track ID"] = spotify_id
                field_updates["Spotify Track ID"] += 1
                changed = True
            if not clean(canonical.get("Legacy D Music Spotify ID")):
                canonical["Legacy D Music Spotify ID"] = spotify_id
                field_updates["Legacy D Music Spotify ID"] += 1
                changed = True

        notes = verification_notes(legacy)
        if notes:
            canonical["Legacy D Music Verification Notes"] = add_list(
                canonical.get("Legacy D Music Verification Notes", ""), notes
            )
            field_updates["Legacy D Music Verification Notes"] += 1
            changed = True

        source_files = clean(legacy.get("Source Files"))
        if source_files:
            canonical["Legacy D Music Source Files"] = source_files
            canonical["Source Files"] = add_list(canonical.get("Source Files", ""), LEGACY_SOURCE)
            field_updates["Legacy D Music Source Files"] += 1
            changed = True

        if changed:
            updated_rows += 1

    merged_rows = canonical_rows + appended_rows
    candidate_path = STAGING_DIR / "merged_candidate_Main_Song_Database.csv"
    appended_path = STAGING_DIR / "d_music_only_appended_rows.csv"
    ambiguous_path = STAGING_DIR / "ambiguous_matches.csv"
    summary_path = STAGING_DIR / "merge_summary.json"

    write_csv(candidate_path, headers, merged_rows)
    write_csv(appended_path, headers, appended_rows)
    write_csv(
        ambiguous_path,
        ["key", "canonical_count", "legacy_count", "legacy_sample"],
        ambiguous_matches,
    )
    copied_inputs = archive_legacy_inputs()

    summary = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "canonical_main": str(CANONICAL_MAIN),
        "legacy_main": str(LEGACY_MAIN),
        "canonical_rows": len(canonical_rows),
        "legacy_rows": len(legacy_rows),
        "candidate_rows": len(merged_rows),
        "updated_canonical_rows": updated_rows,
        "appended_legacy_rows": len(appended_rows),
        "ambiguous_key_groups_skipped": len(ambiguous_matches),
        "field_updates": dict(sorted(field_updates.items())),
        "candidate_csv": str(candidate_path),
        "appended_rows_csv": str(appended_path),
        "ambiguous_matches_csv": str(ambiguous_path),
        "archived_legacy_inputs": copied_inputs,
        "legacy_scripts_policy": "D: scripts were not copied into active scripts because one contains hardcoded credentials and brittle absolute paths.",
        "main_database_modified": False,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report = f"""# D Music Legacy Merge Report

Generated: {summary["generated_at"]}

## Decision

Use `C:\\codex_work\\projects\\SongDB` as the canonical project. Treat `D:\\Music\\Main_Song_Database` as a legacy source to mine for missing values and historical analysis.

## Inputs

- Canonical: `{CANONICAL_MAIN}`
- Legacy: `{LEGACY_MAIN}`

## Results

- Canonical rows: {len(canonical_rows)}
- Legacy rows: {len(legacy_rows)}
- Candidate rows: {len(merged_rows)}
- Canonical rows enriched from legacy: {updated_rows}
- Legacy-only rows appended to candidate: {len(appended_rows)}
- Ambiguous duplicate key groups skipped: {len(ambiguous_matches)}

## Outputs

- Candidate CSV: `{candidate_path}`
- Legacy-only appended rows: `{appended_path}`
- Ambiguous matches: `{ambiguous_path}`
- JSON summary: `{summary_path}`

## Safety Notes

The active `Main_Song_Database.csv` was not modified.

The D: scripts were not copied into active scripts. One legacy script contains hardcoded Spotify credentials and brittle absolute paths. Rotate that Spotify app secret before using any related automation again.
"""
    (STAGING_DIR / "README.md").write_text(report, encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

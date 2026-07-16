"""apply-nyov-official-patch command implementation."""

from __future__ import annotations

import csv
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import MusicDBPaths
from src.normalization import normalize_search_text


REQUIRED_COLUMNS = {
    "promotion_id",
    "seed_title",
    "seed_artist",
    "official_match_status",
    "target_column",
    "current_value",
    "promoted_value",
    "patch_action",
}


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        return fieldnames, [dict(row) for row in reader]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _backup_path(path: Path, backup_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return backup_dir / f"{path.stem}_nyov_official_patch_{timestamp}{path.suffix}"


def _approved_patch_rows(path: Path) -> list[dict[str, str]]:
    _, rows = _read_csv(path)
    if rows:
        missing = REQUIRED_COLUMNS - set(rows[0].keys())
        if missing:
            raise ValueError(f"Official patch CSV missing columns: {', '.join(sorted(missing))}")
    return [
        row for row in rows
        if row.get("patch_action") == "update_existing"
        and row.get("official_match_status") == "matched_exact_title_artist"
    ]


def _find_row_index(rows: list[dict[str, str]], patch_row: dict[str, str]) -> int | None:
    title_key = normalize_search_text(patch_row.get("seed_title", ""))
    artist_key = normalize_search_text(patch_row.get("seed_artist", ""))
    matches = [
        index for index, row in enumerate(rows)
        if normalize_search_text(row.get("Title", "")) == title_key
        and normalize_search_text(row.get("Artist", "")) == artist_key
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def apply_official_patch(
    official_csv: Path,
    patch_csv: Path,
    backup_dir: Path,
    *,
    write: bool = False,
) -> dict[str, Any]:
    if not official_csv.exists():
        raise FileNotFoundError(f"Official CSV not found: {official_csv}")
    if not patch_csv.exists():
        raise FileNotFoundError(f"Official patch CSV not found: {patch_csv}")

    official_headers, official_rows = _read_csv(official_csv)
    patch_rows = _approved_patch_rows(patch_csv)
    applied = 0
    skipped = 0
    skipped_reasons: dict[str, int] = {}

    def skip(reason: str) -> None:
        nonlocal skipped
        skipped += 1
        skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1

    for patch_row in patch_rows:
        target_column = patch_row.get("target_column", "")
        if target_column not in official_headers:
            skip("missing_target_column")
            continue
        row_index = _find_row_index(official_rows, patch_row)
        if row_index is None:
            skip("official_match_not_unique")
            continue
        official_row = official_rows[row_index]
        if official_row.get(target_column, "") != patch_row.get("current_value", ""):
            skip("stale_current_value")
            continue
        if official_row.get(target_column, "") == patch_row.get("promoted_value", ""):
            skip("already_current")
            continue
        if write:
            official_row[target_column] = patch_row.get("promoted_value", "")
        applied += 1

    backup = ""
    if write and applied:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = _backup_path(official_csv, backup_dir)
        shutil.copy2(official_csv, backup_path)
        backup = str(backup_path)
        _write_csv(official_csv, official_headers, official_rows)

    return {
        "official_csv": str(official_csv),
        "patch_csv": str(patch_csv),
        "dry_run": not write,
        "candidate_patch_rows": len(patch_rows),
        "applied_rows": applied,
        "skipped_rows": skipped,
        "skipped_reasons": skipped_reasons,
        "backup_path": backup,
    }


def run(
    *,
    write: bool,
    paths: MusicDBPaths,
    official_csv: Path | None = None,
    patch_csv: Path | None = None,
    backup_dir: Path | None = None,
) -> int:
    official_csv = (official_csv or paths.recordings_csv).resolve()
    patch_csv = (
        patch_csv
        or paths.exports_dir / "codex" / "nyov_official_patch" / "official_patch_candidates.csv"
    ).resolve()
    backup_dir = (backup_dir or paths.backups_dir / "nyov_official_patch").resolve()
    summary = apply_official_patch(official_csv, patch_csv, backup_dir, write=write)
    print("apply-nyov-official-patch: dry-run=" + str(not write))
    import json

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0

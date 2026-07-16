"""apply-data-patches command implementation."""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import MusicDBPaths, require_under_root


REQUIRED_COLUMNS = {
    "patch_id",
    "target_file",
    "match_column",
    "match_value",
    "target_column",
    "old_value",
    "new_value",
}


APPEND_REQUIRED_COLUMNS = {
    "patch_id",
    "patch_action",
    "target_file",
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


def _backup_path(target: Path, backup_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return backup_dir / f"{target.stem}_data_patch_{timestamp}{target.suffix}"


def _repo_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _manifest_paths(patch_dir: Path, patch_file: Path | None = None) -> list[Path]:
    if patch_file is not None:
        return [patch_file]
    return sorted(path for path in patch_dir.glob("*.csv") if path.is_file())


def _load_patch_rows(manifest: Path) -> list[dict[str, str]]:
    _, rows = _read_csv(manifest)
    if rows:
        columns = set(rows[0].keys())
        if rows[0].get("patch_action") == "append_row":
            missing = APPEND_REQUIRED_COLUMNS - columns
        else:
            missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"Data patch manifest missing columns: {manifest}: {', '.join(sorted(missing))}")
    for row in rows:
        row["_manifest"] = str(manifest)
    return rows


def _find_match(rows: list[dict[str, str]], match_column: str, match_value: str) -> int | None:
    matches = [
        index for index, row in enumerate(rows)
        if row.get(match_column, "") == match_value
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def apply_data_patches(
    root: Path,
    patch_dir: Path,
    backup_dir: Path,
    *,
    patch_file: Path | None = None,
    write: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    patch_dir = require_under_root(patch_dir, root)
    backup_dir = require_under_root(backup_dir, root)
    if patch_file is not None:
        patch_file = require_under_root(patch_file, root)

    patch_rows: list[dict[str, str]] = []
    manifests = _manifest_paths(patch_dir, patch_file)
    for manifest in manifests:
        patch_rows.extend(_load_patch_rows(manifest))

    target_cache: dict[Path, tuple[list[str], list[dict[str, str]]]] = {}
    applied = 0
    already_applied = 0
    skipped = 0
    skipped_reasons: dict[str, int] = {}
    changed_targets: set[Path] = set()
    backups: dict[str, str] = {}

    def skip(reason: str) -> None:
        nonlocal skipped
        skipped += 1
        skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1

    for patch_row in patch_rows:
        try:
            target = require_under_root(root / patch_row.get("target_file", ""), root)
        except ValueError:
            skip("target_outside_root")
            continue
        if not target.exists():
            skip("missing_target_file")
            continue
        if target not in target_cache:
            target_cache[target] = _read_csv(target)
        headers, target_rows = target_cache[target]

        if patch_row.get("patch_action") == "append_row":
            new_row = {header: patch_row.get(header, "") for header in headers}
            if any(row == new_row for row in target_rows):
                already_applied += 1
                continue
            if write:
                target_rows.append(new_row)
                changed_targets.add(target)
            applied += 1
            continue

        match_column = patch_row.get("match_column", "")
        target_column = patch_row.get("target_column", "")
        if match_column not in headers:
            skip("missing_match_column")
            continue
        if target_column not in headers:
            skip("missing_target_column")
            continue

        row_index = _find_match(target_rows, match_column, patch_row.get("match_value", ""))
        if row_index is None:
            skip("target_match_not_unique")
            continue

        target_row = target_rows[row_index]
        current_value = target_row.get(target_column, "")
        old_value = patch_row.get("old_value", "")
        new_value = patch_row.get("new_value", "")
        if current_value == new_value:
            already_applied += 1
            continue
        if current_value != old_value:
            skip("stale_current_value")
            continue
        if write:
            target_row[target_column] = new_value
            changed_targets.add(target)
        applied += 1

    if write and changed_targets:
        backup_dir.mkdir(parents=True, exist_ok=True)
        for target in sorted(changed_targets):
            backup_path = _backup_path(target, backup_dir)
            shutil.copy2(target, backup_path)
            backups[_repo_path(target, root)] = str(backup_path)
            headers, target_rows = target_cache[target]
            _write_csv(target, headers, target_rows)

    return {
        "dry_run": not write,
        "patch_manifests": [_repo_path(path, root) for path in manifests],
        "patch_rows": len(patch_rows),
        "applied_rows": applied,
        "already_applied_rows": already_applied,
        "skipped_rows": skipped,
        "skipped_reasons": skipped_reasons,
        "backups": backups,
    }


def run(
    *,
    write: bool,
    paths: MusicDBPaths,
    patch_dir: Path | None = None,
    patch_file: Path | None = None,
    backup_dir: Path | None = None,
) -> int:
    patch_dir = (patch_dir or paths.data_dir / "patches").resolve()
    backup_dir = (backup_dir or paths.backups_dir / "data_patches").resolve()
    summary = apply_data_patches(
        paths.root,
        patch_dir,
        backup_dir,
        patch_file=patch_file,
        write=write,
    )
    print("apply-data-patches: dry-run=" + str(not write))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0

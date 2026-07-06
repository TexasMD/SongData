#!/usr/bin/env python3
"""Promote the reviewed Codex patch candidate into the active MusicDB CSV.

Default mode is a dry run. A real promotion requires ``--write`` and only
proceeds after the active CSV and patch candidate match the reviewed hashes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
ACTIVE_CSV = PROJECT_DIR / "data" / "processed" / "Main_Song_Database.csv"
SUMMARY_JSON = PROJECT_DIR / "data" / "exports" / "codex" / "active_main_patch_summary.json"
BACKUP_ROOT = PROJECT_DIR / "data" / "backups" / "codex_promotions"
PROMOTION_REPORT = PROJECT_DIR / "data" / "exports" / "codex" / "active_main_patch_promotion_summary.json"


class PromotionError(RuntimeError):
    """Raised when the patch candidate is not safe to promote."""


@dataclass(frozen=True)
class CsvShape:
    rows: int
    columns: int
    headers: list[str]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_shape(path: Path) -> CsvShape:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        headers = next(reader, [])
        rows = sum(1 for _ in reader)
    return CsvShape(rows=rows, columns=len(headers), headers=headers)


def load_summary(path: Path) -> dict:
    if not path.exists():
        raise PromotionError(f"Missing reviewed patch summary: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_candidate(summary: dict, active_csv: Path) -> dict:
    candidate_csv = Path(summary["patch_candidate_csv"])
    if not active_csv.exists():
        raise PromotionError(f"Missing active CSV: {active_csv}")
    if not candidate_csv.exists():
        raise PromotionError(f"Missing patch candidate CSV: {candidate_csv}")

    active_hash = sha256(active_csv)
    expected_active_hash = summary.get("active_sha_after") or summary.get("active_sha_before")
    if active_hash != expected_active_hash:
        raise PromotionError(
            "Active CSV hash changed since candidate review. "
            f"Expected {expected_active_hash}, found {active_hash}."
        )

    candidate_hash = sha256(candidate_csv)
    expected_candidate_hash = summary.get("patch_candidate_sha256")
    if candidate_hash != expected_candidate_hash:
        raise PromotionError(
            "Patch candidate hash changed since candidate review. "
            f"Expected {expected_candidate_hash}, found {candidate_hash}."
        )

    verification = summary.get("verification") or {}
    if verification.get("overwrite_violations") != 0:
        raise PromotionError("Patch summary reports overwrite violations; manual review required.")
    if verification.get("staged_spotify_track_id_mismatches") != 0:
        raise PromotionError("Patch summary reports Spotify Track ID mismatches; manual review required.")

    active_shape = csv_shape(active_csv)
    candidate_shape = csv_shape(candidate_csv)
    if active_shape.rows != summary.get("active_rows"):
        raise PromotionError(
            f"Active row count changed since review. Expected {summary.get('active_rows')}, found {active_shape.rows}."
        )
    if candidate_shape.rows != summary.get("candidate_rows"):
        raise PromotionError(
            f"Candidate row count changed since review. Expected {summary.get('candidate_rows')}, found {candidate_shape.rows}."
        )

    return {
        "active_csv": str(active_csv),
        "candidate_csv": str(candidate_csv),
        "active_sha256": active_hash,
        "candidate_sha256": candidate_hash,
        "active_rows": active_shape.rows,
        "candidate_rows": candidate_shape.rows,
        "active_columns": active_shape.columns,
        "candidate_columns": candidate_shape.columns,
        "added_columns": [column for column in candidate_shape.headers if column not in active_shape.headers],
        "patch_action_count": summary.get("patch_action_count"),
        "manual_review_count": summary.get("skipped_review_count"),
    }


def write_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def promote(summary_path: Path, active_csv: Path, backup_root: Path, report_path: Path, write: bool) -> dict:
    summary = load_summary(summary_path)
    validation = validate_candidate(summary, active_csv)
    generated_at = datetime.now(timezone.utc).isoformat()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = backup_root / timestamp
    backup_path = backup_dir / active_csv.name

    report = {
        "generated_at": generated_at,
        "mode": "write" if write else "dry_run",
        "active_database_modified": False,
        "backup_path": str(backup_path) if write else "",
        **validation,
    }

    if write:
        backup_dir.mkdir(parents=True, exist_ok=False)
        shutil.copy2(active_csv, backup_path)
        shutil.copy2(validation["candidate_csv"], active_csv)
        report["active_database_modified"] = True
        report["active_sha256_after_write"] = sha256(active_csv)

    write_report(report, report_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote the reviewed Codex MusicDB patch candidate.")
    parser.add_argument("--write", action="store_true", help="Actually replace the active CSV after validation.")
    parser.add_argument("--summary", type=Path, default=SUMMARY_JSON, help="Reviewed patch summary JSON.")
    parser.add_argument("--active-csv", type=Path, default=ACTIVE_CSV, help="Active Main_Song_Database.csv path.")
    parser.add_argument("--backup-root", type=Path, default=BACKUP_ROOT, help="Directory for timestamped backups.")
    parser.add_argument("--report", type=Path, default=PROMOTION_REPORT, help="Promotion summary JSON path.")
    args = parser.parse_args()

    try:
        report = promote(args.summary, args.active_csv, args.backup_root, args.report, args.write)
    except PromotionError as exc:
        print(f"ERROR: {exc}")
        return 2

    print(json.dumps(report, indent=2))
    if not args.write:
        print("Dry run only. Re-run with --write to promote after review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

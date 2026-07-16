"""apply-nyov-promotions command implementation."""

from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import MusicDBPaths


REQUIRED_COLUMNS = {
    "nyov_id",
    "target_table",
    "target_key",
    "target_field",
    "proposed_value",
    "verification_level",
    "supporting_sources",
    "conflicting_sources",
    "review_decision",
    "review_notes",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: object) -> str:
    return str(value or "").strip()


def _promotion_id(row: dict[str, str]) -> str:
    payload = "|".join(
        [
            _clean(row.get("nyov_id")),
            _clean(row.get("target_table")),
            _clean(row.get("target_key")),
            _clean(row.get("target_field")),
            _clean(row.get("proposed_value")),
        ]
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _read_review_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - fieldnames
        if missing:
            raise ValueError(f"Promotion review CSV missing columns: {', '.join(sorted(missing))}")
        return [dict(row) for row in reader]


def _approved_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    approved = []
    for row in rows:
        if _clean(row.get("review_decision")).lower() != "approve":
            continue
        if not _clean(row.get("nyov_id")) or not _clean(row.get("target_field")) or not _clean(row.get("proposed_value")):
            continue
        approved.append(row)
    return approved


def _to_promotion_row(row: dict[str, str], *, promoted_at: str, promoted_by: str) -> tuple[str, ...]:
    evidence = {
        "supporting_sources": _clean(row.get("supporting_sources")),
        "conflicting_sources": _clean(row.get("conflicting_sources")),
        "best_provider": _clean(row.get("best_provider")),
        "best_provider_entity_id": _clean(row.get("best_provider_entity_id")),
        "best_match_score": _clean(row.get("best_match_score")),
        "review_decision": _clean(row.get("review_decision")),
    }
    return (
        _promotion_id(row),
        _clean(row.get("nyov_id")),
        _clean(row.get("target_table")),
        _clean(row.get("target_key")),
        _clean(row.get("target_field")),
        _clean(row.get("proposed_value")),
        _clean(row.get("verification_level")),
        json.dumps(evidence, ensure_ascii=False, sort_keys=True),
        promoted_at,
        promoted_by,
        _clean(row.get("review_notes")),
    )


def apply_promotions(
    db_path: Path,
    review_csv: Path,
    *,
    promoted_by: str = "manual_review",
    write: bool = False,
) -> dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"NYOV database not found: {db_path}")
    if not review_csv.exists():
        raise FileNotFoundError(f"Promotion review CSV not found: {review_csv}")

    rows = _read_review_rows(review_csv)
    approved = _approved_rows(rows)
    promoted_at = _utc_now()
    promotion_rows = [
        _to_promotion_row(row, promoted_at=promoted_at, promoted_by=promoted_by)
        for row in approved
    ]

    if not write:
        return {
            "db_path": str(db_path),
            "review_csv": str(review_csv),
            "dry_run": True,
            "rows_seen": len(rows),
            "approved_rows": len(approved),
            "promotions_written": 0,
        }

    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO nyov_promotions
            (promotion_id, nyov_id, target_table, target_key, target_field, promoted_value,
             verification_level, evidence_json, promoted_at, promoted_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            promotion_rows,
        )
        promotions_total = conn.execute("SELECT COUNT(*) FROM nyov_promotions").fetchone()[0]

    return {
        "db_path": str(db_path),
        "review_csv": str(review_csv),
        "dry_run": False,
        "rows_seen": len(rows),
        "approved_rows": len(approved),
        "promotions_written": len(promotion_rows),
        "promotions_total": promotions_total,
    }


def run(
    *,
    write: bool,
    paths: MusicDBPaths,
    db_path: Path | None = None,
    review_csv: Path | None = None,
    promoted_by: str = "manual_review",
) -> int:
    db_path = (db_path or paths.nyov_db_path).resolve()
    review_csv = (
        review_csv
        or paths.exports_dir / "codex" / "nyov_promotion_review" / "promotion_review_candidates.csv"
    ).resolve()
    summary = apply_promotions(db_path, review_csv, promoted_by=promoted_by, write=write)
    print("apply-nyov-promotions: dry-run=" + str(not write))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0

"""nyov-verification-summary command implementation."""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

from src.config import MusicDBPaths


def _fetch_provider_counts(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT provider, match_status, COUNT(*) AS attempt_count
        FROM nyov_verification_attempts
        GROUP BY provider, match_status
        ORDER BY provider, match_status
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _fetch_entity_summary(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        WITH attempt_rollup AS (
            SELECT
                nyov_id,
                COUNT(*) AS attempt_count,
                COUNT(DISTINCT provider) AS provider_count,
                SUM(CASE WHEN match_status = 'matched' THEN 1 ELSE 0 END) AS matched_attempts,
                SUM(CASE WHEN match_status = 'needs_review' THEN 1 ELSE 0 END) AS needs_review_attempts,
                SUM(CASE WHEN match_status = 'rejected' THEN 1 ELSE 0 END) AS rejected_attempts,
                SUM(CASE WHEN match_status IN ('matched', 'needs_review') AND title_match_status = 'different' THEN 1 ELSE 0 END) AS title_conflicts,
                SUM(CASE WHEN match_status IN ('matched', 'needs_review') AND artist_match_status = 'different' THEN 1 ELSE 0 END) AS artist_conflicts,
                SUM(CASE WHEN match_status IN ('matched', 'needs_review') AND album_match_status = 'different' THEN 1 ELSE 0 END) AS album_conflicts,
                MAX(CAST(match_score AS REAL)) AS best_match_score,
                GROUP_CONCAT(DISTINCT provider) AS providers_checked
            FROM nyov_verification_attempts
            GROUP BY nyov_id
        ),
        best_attempt AS (
            SELECT
                attempt_id,
                nyov_id,
                provider,
                provider_entity_type,
                provider_entity_id,
                provider_url,
                match_status,
                match_score,
                title_match_status,
                artist_match_status,
                album_match_status,
                ROW_NUMBER() OVER (
                    PARTITION BY nyov_id
                    ORDER BY CAST(match_score AS REAL) DESC, match_status, provider
                ) AS rank_number
            FROM nyov_verification_attempts
        )
        SELECT
            e.nyov_id,
            e.seed_title,
            e.seed_artist,
            e.seed_album,
            r.attempt_count,
            r.provider_count,
            r.providers_checked,
            r.matched_attempts,
            r.needs_review_attempts,
            r.rejected_attempts,
            r.title_conflicts,
            r.artist_conflicts,
            r.album_conflicts,
            printf('%.3f', COALESCE(r.best_match_score, 0)) AS best_match_score,
            b.provider AS best_provider,
            b.provider_entity_type AS best_provider_entity_type,
            b.provider_entity_id AS best_provider_entity_id,
            b.provider_url AS best_provider_url,
            b.match_status AS best_match_status,
            b.title_match_status AS best_title_match_status,
            b.artist_match_status AS best_artist_match_status,
            b.album_match_status AS best_album_match_status,
            CASE
                WHEN r.provider_count >= 2
                 AND r.matched_attempts >= 2
                 AND r.title_conflicts = 0
                 AND r.artist_conflicts = 0
                 AND CAST(r.best_match_score AS REAL) >= 0.9
                THEN 'review_candidate_strong_identity'
                WHEN r.title_conflicts > 0 OR r.artist_conflicts > 0
                THEN 'conflict_identity'
                WHEN r.album_conflicts > 0
                THEN 'conflict_album_only'
                WHEN r.matched_attempts >= 1
                 AND r.title_conflicts = 0
                 AND r.artist_conflicts = 0
                THEN 'review_candidate_single_source'
                ELSE 'insufficient_match'
            END AS review_bucket
        FROM attempt_rollup r
        JOIN nyov_entities e ON e.nyov_id = r.nyov_id
        LEFT JOIN best_attempt b ON b.nyov_id = r.nyov_id AND b.rank_number = 1
        ORDER BY
            CASE review_bucket
                WHEN 'review_candidate_strong_identity' THEN 1
                WHEN 'review_candidate_single_source' THEN 2
                WHEN 'conflict_album_only' THEN 3
                WHEN 'conflict_identity' THEN 4
                ELSE 5
            END,
            CAST(best_match_score AS REAL) DESC,
            e.seed_artist,
            e.seed_title
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _fetch_bucket_counts(entity_summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in entity_summary:
        bucket = str(row["review_bucket"])
        counts[bucket] = counts.get(bucket, 0) + 1
    return [{"review_bucket": bucket, "entity_count": count} for bucket, count in sorted(counts.items())]


def build_summary(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"NYOV database not found: {db_path}")
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        total_attempts = conn.execute("SELECT COUNT(*) FROM nyov_verification_attempts").fetchone()[0]
        verified_entities = conn.execute("SELECT COUNT(DISTINCT nyov_id) FROM nyov_verification_attempts").fetchone()[0]
        provider_counts = _fetch_provider_counts(conn)
        entity_summary = _fetch_entity_summary(conn)
    return {
        "database": str(db_path),
        "total_attempts": total_attempts,
        "entities_with_attempts": verified_entities,
        "provider_counts": provider_counts,
        "review_bucket_counts": _fetch_bucket_counts(entity_summary),
        "entity_summary": entity_summary,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["nyov_id"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run(
    *,
    write: bool,
    paths: MusicDBPaths,
    db_path: Path | None = None,
    output_dir: Path | None = None,
) -> int:
    db_path = (db_path or paths.nyov_db_path).resolve()
    output_dir = (output_dir or paths.exports_dir / "codex" / "nyov_verification_summary").resolve()
    summary = build_summary(db_path)

    print("nyov-verification-summary: dry-run=" + str(not write))
    print(f"Input DB: {db_path}")
    print(f"Total attempts: {summary['total_attempts']}")
    print(f"Entities with attempts: {summary['entities_with_attempts']}")
    print("Review buckets:")
    for row in summary["review_bucket_counts"]:
        print(f"  {row['review_bucket']}: {row['entity_count']}")

    summary_path = output_dir / "summary.json"
    entity_summary_path = output_dir / "entity_summary.csv"
    if write:
        output_dir.mkdir(parents=True, exist_ok=True)
        with summary_path.open("w", encoding="utf-8") as handle:
            json.dump({key: value for key, value in summary.items() if key != "entity_summary"}, handle, indent=2, ensure_ascii=False)
        _write_csv(entity_summary_path, summary["entity_summary"])
        print(f"Wrote summary to {summary_path}")
        print(f"Wrote entity summary to {entity_summary_path}")
    else:
        print(f"DRY RUN: Would write summary to {summary_path}")
        print(f"DRY RUN: Would write entity summary to {entity_summary_path}")
    return 0

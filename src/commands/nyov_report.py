"""nyov-report command implementation."""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

from src.config import MusicDBPaths


def _fetch_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = [
        "nyov_source_files",
        "nyov_entities",
        "nyov_source_observations",
        "nyov_identifiers",
        "nyov_verification_attempts",
        "nyov_conflicts",
        "nyov_promotions",
    ]
    return {
        table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in tables
    }


def _fetch_group_counts(conn: sqlite3.Connection, sql: str) -> list[dict[str, Any]]:
    rows = conn.execute(sql).fetchall()
    return [dict(row) for row in rows]


def _fetch_verification_queue(conn: sqlite3.Connection, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        WITH observation_counts AS (
            SELECT
                nyov_id,
                COUNT(*) AS observation_count,
                COUNT(DISTINCT source_file_id) AS source_file_count
            FROM nyov_source_observations
            WHERE nyov_id != ''
            GROUP BY nyov_id
        ),
        identifier_counts AS (
            SELECT
                nyov_id,
                COUNT(*) AS identifier_count,
                GROUP_CONCAT(DISTINCT source_name) AS identifier_sources
            FROM nyov_identifiers
            WHERE nyov_id != ''
            GROUP BY nyov_id
        )
        SELECT
            e.nyov_id,
            e.seed_title,
            e.seed_artist,
            e.seed_album,
            COALESCE(o.observation_count, 0) AS observation_count,
            COALESCE(o.source_file_count, 0) AS source_file_count,
            COALESCE(i.identifier_count, 0) AS identifier_count,
            COALESCE(i.identifier_sources, '') AS identifier_sources,
            CASE
                WHEN COALESCE(i.identifier_sources, '') LIKE '%Spotify%'
                 AND (
                    COALESCE(i.identifier_sources, '') LIKE '%MusicBrainz%'
                    OR COALESCE(i.identifier_sources, '') LIKE '%iTunes%'
                    OR COALESCE(i.identifier_sources, '') LIKE '%YouTube Music%'
                 )
                THEN 'candidate_dual_source_match'
                WHEN COALESCE(i.identifier_sources, '') LIKE '%Spotify%'
                THEN 'candidate_spotify_only'
                WHEN COALESCE(i.identifier_count, 0) > 0
                THEN 'candidate_non_spotify_identifier'
                WHEN COALESCE(o.observation_count, 0) > 1
                THEN 'candidate_local_evidence_only'
                ELSE 'seed_only'
            END AS next_step
        FROM nyov_entities e
        LEFT JOIN observation_counts o ON o.nyov_id = e.nyov_id
        LEFT JOIN identifier_counts i ON i.nyov_id = e.nyov_id
        ORDER BY
            CASE next_step
                WHEN 'candidate_dual_source_match' THEN 1
                WHEN 'candidate_spotify_only' THEN 2
                WHEN 'candidate_non_spotify_identifier' THEN 3
                WHEN 'candidate_local_evidence_only' THEN 4
                ELSE 5
            END,
            identifier_count DESC,
            observation_count DESC,
            e.seed_artist,
            e.seed_title
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def build_report(db_path: Path, *, queue_limit: int = 250) -> dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"NYOV database not found: {db_path}")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        counts = _fetch_counts(conn)
        matched_entities = int(
            conn.execute(
                "SELECT COUNT(DISTINCT nyov_id) FROM nyov_source_observations WHERE nyov_id != ''"
            ).fetchone()[0]
        )
        identifier_source_counts = _fetch_group_counts(
            conn,
            """
            SELECT source_name, COUNT(*) AS identifier_count
            FROM nyov_identifiers
            GROUP BY source_name
            ORDER BY identifier_count DESC, source_name
            """,
        )
        parser_counts = _fetch_group_counts(
            conn,
            """
            SELECT parser, COUNT(*) AS observation_count
            FROM nyov_source_observations
            GROUP BY parser
            ORDER BY observation_count DESC, parser
            """,
        )
        source_file_counts = _fetch_group_counts(
            conn,
            """
            SELECT source_path, parser, COUNT(*) AS observation_count
            FROM nyov_source_observations
            GROUP BY source_path, parser
            ORDER BY observation_count DESC, source_path
            LIMIT 25
            """,
        )
        next_step_counts = _fetch_group_counts(
            conn,
            """
            WITH identifier_counts AS (
                SELECT nyov_id, COUNT(*) AS identifier_count, GROUP_CONCAT(DISTINCT source_name) AS identifier_sources
                FROM nyov_identifiers
                WHERE nyov_id != ''
                GROUP BY nyov_id
            ),
            observation_counts AS (
                SELECT nyov_id, COUNT(*) AS observation_count
                FROM nyov_source_observations
                WHERE nyov_id != ''
                GROUP BY nyov_id
            ),
            classified AS (
                SELECT
                    e.nyov_id,
                    CASE
                        WHEN COALESCE(i.identifier_sources, '') LIKE '%Spotify%'
                         AND (
                            COALESCE(i.identifier_sources, '') LIKE '%MusicBrainz%'
                            OR COALESCE(i.identifier_sources, '') LIKE '%iTunes%'
                            OR COALESCE(i.identifier_sources, '') LIKE '%YouTube Music%'
                         )
                        THEN 'candidate_dual_source_match'
                        WHEN COALESCE(i.identifier_sources, '') LIKE '%Spotify%'
                        THEN 'candidate_spotify_only'
                        WHEN COALESCE(i.identifier_count, 0) > 0
                        THEN 'candidate_non_spotify_identifier'
                        WHEN COALESCE(o.observation_count, 0) > 1
                        THEN 'candidate_local_evidence_only'
                        ELSE 'seed_only'
                    END AS next_step
                FROM nyov_entities e
                LEFT JOIN identifier_counts i ON i.nyov_id = e.nyov_id
                LEFT JOIN observation_counts o ON o.nyov_id = e.nyov_id
            )
            SELECT next_step, COUNT(*) AS entity_count
            FROM classified
            GROUP BY next_step
            ORDER BY entity_count DESC, next_step
            """,
        )
        queue = _fetch_verification_queue(conn, queue_limit)

    return {
        "database": str(db_path),
        "counts": counts,
        "matched_seed_entities": matched_entities,
        "unmatched_seed_entities": counts["nyov_entities"] - matched_entities,
        "identifier_source_counts": identifier_source_counts,
        "parser_counts": parser_counts,
        "top_source_files": source_file_counts,
        "next_step_counts": next_step_counts,
        "verification_queue": queue,
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
    queue_limit: int = 250,
) -> int:
    db_path = (db_path or paths.nyov_db_path).resolve()
    output_dir = (output_dir or paths.exports_dir / "codex" / "nyov_report").resolve()
    report = build_report(db_path, queue_limit=queue_limit)

    print("nyov-report: dry-run=" + str(not write))
    print(f"Input DB: {db_path}")
    print(f"Seed entities: {report['counts']['nyov_entities']}")
    print(f"Matched seed entities: {report['matched_seed_entities']}")
    print(f"Source observations: {report['counts']['nyov_source_observations']}")
    print(f"Identifiers: {report['counts']['nyov_identifiers']}")
    print("Next-step buckets:")
    for row in report["next_step_counts"]:
        print(f"  {row['next_step']}: {row['entity_count']}")

    summary_path = output_dir / "summary.json"
    queue_path = output_dir / "verification_queue.csv"
    if write:
        output_dir.mkdir(parents=True, exist_ok=True)
        with summary_path.open("w", encoding="utf-8") as handle:
            json.dump({key: value for key, value in report.items() if key != "verification_queue"}, handle, indent=2, ensure_ascii=False)
        _write_csv(queue_path, report["verification_queue"])
        print(f"Wrote summary to {summary_path}")
        print(f"Wrote verification queue to {queue_path}")
    else:
        print(f"DRY RUN: Would write summary to {summary_path}")
        print(f"DRY RUN: Would write verification queue to {queue_path}")
    return 0

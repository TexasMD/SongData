from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
from pathlib import Path

import pandas as pd


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_source_query_checks_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_query_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recording_id TEXT NOT NULL,
            source TEXT NOT NULL,
            query_kind TEXT NOT NULL,
            last_checked_at TEXT NOT NULL,
            query_count INTEGER NOT NULL DEFAULT 1,
            last_result_count INTEGER,
            last_query_url TEXT,
            notes TEXT,
            UNIQUE(recording_id, source, query_kind)
        )
        """
    )


def record_source_query_check(
    conn: sqlite3.Connection,
    *,
    recording_id: str,
    source: str,
    query_kind: str,
    last_query_url: str = "",
    last_result_count: int | None = None,
    checked_at: str | None = None,
    notes: str = "",
) -> str:
    checked_at = checked_at or utc_now_iso()
    existing = conn.execute(
        """
        SELECT id, query_count
        FROM source_query_checks
        WHERE recording_id = ? AND source = ? AND query_kind = ?
        """,
        (recording_id, source, query_kind),
    ).fetchone()

    if existing:
        conn.execute(
            """
            UPDATE source_query_checks
            SET last_checked_at = ?,
                query_count = ?,
                last_result_count = ?,
                last_query_url = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                checked_at,
                int(existing[1]) + 1,
                last_result_count,
                last_query_url,
                notes,
                existing[0],
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO source_query_checks (
                recording_id,
                source,
                query_kind,
                last_checked_at,
                query_count,
                last_result_count,
                last_query_url,
                notes
            )
            VALUES (?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                recording_id,
                source,
                query_kind,
                checked_at,
                last_result_count,
                last_query_url,
                notes,
            ),
        )

    conn.commit()
    return checked_at


def export_source_query_checks_csv(conn: sqlite3.Connection, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.read_sql_query("SELECT * FROM source_query_checks", conn).to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

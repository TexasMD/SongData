from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

import pandas as pd

root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.db_access import DEFAULT_DB_PATH

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANTIGRAVITY_STAGE_DIR = PROJECT_ROOT / "data" / "staging" / "antigravity"
JULES_STAGE_DIR = PROJECT_ROOT / "data" / "staging" / "jules"

SOURCE_CSV = ANTIGRAVITY_STAGE_DIR / "cover_relationship_candidates.csv"
SOURCE_CHECKS_CSV = ANTIGRAVITY_STAGE_DIR / "source_query_checks.csv"
STAGED_CSV = JULES_STAGE_DIR / "cover_relationship_candidates.csv"
STAGED_SOURCE_CHECKS_CSV = JULES_STAGE_DIR / "source_query_checks.csv"

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cover_relationship_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_recording_id TEXT,
    title TEXT,
    artist TEXT,
    original_title TEXT,
    original_artist TEXT,
    original_year TEXT,
    musicbrainz_recording_id TEXT,
    source TEXT,
    musicbrainz_last_checked_at TEXT,
    secondhandsongs_last_checked_at TEXT,
    whosampled_last_checked_at TEXT
)
"""

SOURCE_CHECKS_TABLE_SQL = """
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


def ensure_parent_dirs() -> None:
    ANTIGRAVITY_STAGE_DIR.mkdir(parents=True, exist_ok=True)
    JULES_STAGE_DIR.mkdir(parents=True, exist_ok=True)


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing staged CSV: {csv_path}")
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    return df.to_dict(orient="records")


def write_stage_copy(rows: list[dict[str, str]]) -> None:
    with STAGED_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "original_recording_id",
                "title",
                "artist",
                "original_title",
                "original_artist",
                "original_year",
                "musicbrainz_recording_id",
                "source",
                "musicbrainz_last_checked_at",
                "secondhandsongs_last_checked_at",
                "whosampled_last_checked_at",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_source_checks_stage_copy(rows: list[dict[str, str]]) -> None:
    with STAGED_SOURCE_CHECKS_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "recording_id",
                "source",
                "query_kind",
                "last_checked_at",
                "query_count",
                "last_result_count",
                "last_query_url",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def replace_table(conn: sqlite3.Connection, rows: list[dict[str, str]]) -> None:
    conn.execute("DROP TABLE IF EXISTS cover_relationship_candidates")
    conn.execute(TABLE_SQL)
    conn.executemany(
        """
        INSERT INTO cover_relationship_candidates
        (original_recording_id, title, artist, original_title, original_artist, original_year, musicbrainz_recording_id, source, musicbrainz_last_checked_at, secondhandsongs_last_checked_at, whosampled_last_checked_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row.get("original_recording_id", ""),
                row.get("title", ""),
                row.get("artist", ""),
                row.get("original_title", ""),
                row.get("original_artist", ""),
                row.get("original_year", ""),
                row.get("musicbrainz_recording_id", ""),
                row.get("source", ""),
                row.get("musicbrainz_last_checked_at", ""),
                row.get("secondhandsongs_last_checked_at", ""),
                row.get("whosampled_last_checked_at", ""),
            )
            for row in rows
        ],
    )
    conn.commit()


def replace_source_checks_table(conn: sqlite3.Connection, rows: list[dict[str, str]]) -> None:
    conn.execute("DROP TABLE IF EXISTS source_query_checks")
    conn.execute(SOURCE_CHECKS_TABLE_SQL)
    conn.executemany(
        """
        INSERT INTO source_query_checks
        (recording_id, source, query_kind, last_checked_at, query_count, last_result_count, last_query_url, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row.get("recording_id", ""),
                row.get("source", ""),
                row.get("query_kind", ""),
                row.get("last_checked_at", ""),
                row.get("query_count", ""),
                row.get("last_result_count", ""),
                row.get("last_query_url", ""),
                row.get("notes", ""),
            )
            for row in rows
        ],
    )
    conn.commit()


def main() -> int:
    ensure_parent_dirs()
    rows = load_rows(SOURCE_CSV)
    source_check_rows = load_rows(SOURCE_CHECKS_CSV) if SOURCE_CHECKS_CSV.exists() else []
    write_stage_copy(rows)
    if SOURCE_CHECKS_CSV.exists():
        write_source_checks_stage_copy(source_check_rows)

    with sqlite3.connect(DEFAULT_DB_PATH) as conn:
        replace_table(conn, rows)
        if SOURCE_CHECKS_CSV.exists():
            replace_source_checks_table(conn, source_check_rows)

    print(f"Imported {len(rows)} cover candidates into {DEFAULT_DB_PATH}")
    print(f"Wrote staged copy to {STAGED_CSV}")
    if SOURCE_CHECKS_CSV.exists():
        print(f"Wrote staged copy to {STAGED_SOURCE_CHECKS_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

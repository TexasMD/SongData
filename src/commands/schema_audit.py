from __future__ import annotations

import contextlib
import csv
import json
import logging
import sqlite3
from pathlib import Path
from typing import Iterator, Any

from src.config import paths


def get_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return [row[0] for row in cur.fetchall()]


def get_table_schema(conn: sqlite3.Connection, table: str) -> dict[str, Any]:
    pk_cols = [
        row[1] for row in conn.execute(f'PRAGMA table_info("{table}")') if row[5] >= 1
    ]

    fks = []
    for row in conn.execute(f'PRAGMA foreign_key_list("{table}")'):
        fks.append(
            {
                "id": row[0],
                "fk_column": row[3],
                "parent_table": row[2],
                "parent_column": row[4],
            }
        )

    return {"primary_keys": pk_cols, "foreign_keys": fks}


def stream_pk_issues(
    conn: sqlite3.Connection, table: str, pk_cols: list[str]
) -> Iterator[tuple]:
    for pk in pk_cols:
        query = f'SELECT * FROM "{table}" WHERE "{pk}" IS NULL OR "{pk}" = \'\''
        for row in conn.execute(query):
            yield (table, pk, json.dumps(row))


def stream_fk_issues(
    conn: sqlite3.Connection, table: str, fks: list[dict]
) -> Iterator[tuple]:
    for fk in fks:
        fk_col = fk["fk_column"]
        query = f'SELECT "{fk_col}", * FROM "{table}" WHERE "{fk_col}" IS NULL OR "{fk_col}" = \'\''
        for row in conn.execute(query):
            yield (table, fk_col, "", "blank_fk", json.dumps(row[1:]))

    fk_id_map = {fk["id"]: fk["fk_column"] for fk in fks}
    for orphan in conn.execute(f'PRAGMA foreign_key_check("{table}")'):
        _, rowid, parent_table, fkid = orphan
        fk_col = fk_id_map.get(fkid, "unknown_col")

        row_query = f'SELECT "{fk_col}", * FROM "{table}" WHERE rowid = ?'
        failed_row = conn.execute(row_query, (rowid,)).fetchone()

        if failed_row:
            fk_value = failed_row[0]
            actual_row = failed_row[1:]
            yield (table, fk_col, fk_value, "orphan_fk", json.dumps(actual_row))


def command_schema_audit(
    *,
    write_enabled: bool = False,
    db_path: Path | None = None,
    output_dir: Path | None = None,
) -> None:
    p = paths()
    actual_db_path = db_path or p.sqlite_poc_path

    if not actual_db_path.exists():
        logging.error(f"Database not found: {actual_db_path}")
        return

    db_uri = f"file:{actual_db_path.absolute().as_posix()}?mode=ro"
    actual_output_dir = output_dir or (p.exports_dir / "jules" / "sqlite_reports")

    pk_count = 0
    fk_count = 0
    schema_report = {}

    with contextlib.ExitStack() as stack:
        conn = stack.enter_context(
            contextlib.closing(sqlite3.connect(db_uri, uri=True))
        )

        pk_writer = fk_writer = None
        if write_enabled:
            actual_output_dir.mkdir(parents=True, exist_ok=True)

            pk_file = stack.enter_context(
                (actual_output_dir / "pk_issues.csv").open(
                    "w", newline="", encoding="utf-8"
                )
            )
            pk_writer = csv.writer(pk_file)
            pk_writer.writerow(["table", "pk_column", "row"])

            fk_file = stack.enter_context(
                (actual_output_dir / "fk_issues.csv").open(
                    "w", newline="", encoding="utf-8"
                )
            )
            fk_writer = csv.writer(fk_file)
            fk_writer.writerow(["table", "fk_column", "fk_value", "issue", "row"])

        for table in get_tables(conn):
            metadata = get_table_schema(conn, table)
            schema_report[table] = metadata

            for pk_issue in stream_pk_issues(conn, table, metadata["primary_keys"]):
                pk_count += 1
                if pk_writer:
                    pk_writer.writerow(pk_issue)

            for fk_issue in stream_fk_issues(conn, table, metadata["foreign_keys"]):
                fk_count += 1
                if fk_writer:
                    fk_writer.writerow(fk_issue)

        if write_enabled:
            with (actual_output_dir / "schema_report.json").open(
                "w", encoding="utf-8"
            ) as f:
                json.dump(schema_report, f, indent=2)

            logging.info(f"Audit complete. Reports written to: {actual_output_dir}")
            logging.info(f"Schema → {actual_output_dir / 'schema_report.json'}")
            logging.info(f"PK issues → {actual_output_dir / 'pk_issues.csv'}")
            logging.info(f"FK issues → {actual_output_dir / 'fk_issues.csv'}")
        else:
            logging.info(
                f"Audit complete (dry run). Found {pk_count} PK issues and {fk_count} FK issues."
            )

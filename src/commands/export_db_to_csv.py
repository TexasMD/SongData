"""export-db-to-csv command implementation."""

from __future__ import annotations

import sqlite3
import csv
import re
import contextlib
from pathlib import Path


def sanitize_filename(name: str) -> str:
    # Replace characters that are unsafe in filenames
    return re.sub(r'[<>:"/\\|?*\s]+', '_', name).strip('_')


def get_table_names(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
    )
    return [row[0] for row in cur.fetchall()]


def export_table_to_csv(conn: sqlite3.Connection, table_name: str, out_path: Path):
    cur = conn.cursor()
    cur.execute(f'SELECT * FROM "{table_name}";')
    cols = [d[0] for d in cur.description] if cur.description else []
    csv_path = out_path / f"{sanitize_filename(table_name)}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        if cols:
            writer.writerow(cols)
        # Stream rows to avoid high memory usage
        while True:
            rows = cur.fetchmany(1000)
            if not rows:
                break
            writer.writerows(rows)
    print(f"Exported table '{table_name}' -> {csv_path}")


def run(*, write: bool, db_path: Path, output_dir: Path | None = None) -> int:
    if not output_dir:
        output_dir = db_path.parent

    if not write:
        print("export-db-to-csv: dry-run=True")
        print(f"DRY RUN: Would export tables from {db_path} to {output_dir}")
        return 0

    if not db_path.exists():
        print(f"Error: SQLite file not found: {db_path}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Use URI mode for read-only connection
        db_uri = f"file:{db_path.absolute().as_posix()}?mode=ro"
        with contextlib.closing(sqlite3.connect(db_uri, uri=True)) as conn:
            tables = get_table_names(conn)
            if not tables:
                print("No user tables found in the database.")
                return 0
            for t in tables:
                try:
                    export_table_to_csv(conn, t, output_dir)
                except Exception as e:
                    print(f"Failed to export table '{t}': {e}")
                    return 1
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return 1

    return 0

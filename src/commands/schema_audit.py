import sqlite3
import csv
import json
import logging
import contextlib
from pathlib import Path
from src.config import paths


def get_tables(conn):
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cur.fetchall() if row[0] != "sqlite_sequence"]


def get_primary_keys(conn, table):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall() if row[5] == 1]  # row[5] = pk flag


def get_foreign_keys(conn, table):
    cur = conn.execute(f"PRAGMA foreign_key_list({table})")
    fks = []
    for row in cur.fetchall():
        # row columns: id, seq, table, from, to, on_update, on_delete, match
        fks.append(
            {"fk_column": row[3], "parent_table": row[2], "parent_column": row[4]}
        )
    return fks


def get_blank_pk_rows(conn, table, pk_cols):
    if not pk_cols:
        return []
    blanks = []
    for pk in pk_cols:
        cur = conn.execute(f"SELECT * FROM {table} WHERE {pk} IS NULL OR {pk} = ''")
        for row in cur.fetchall():
            blanks.append({"table": table, "pk_column": pk, "row": row})
    return blanks


def get_fk_issues(conn, table, fks):
    issues = []
    for fk in fks:
        fk_col = fk["fk_column"]
        parent_table = fk["parent_table"]
        parent_col = fk["parent_column"]

        # Blank FK values
        cur = conn.execute(
            f"SELECT * FROM {table} WHERE {fk_col} IS NULL OR {fk_col} = ''"
        )
        for row in cur.fetchall():
            issues.append(
                {
                    "table": table,
                    "fk_column": fk_col,
                    "fk_value": "",
                    "issue": "blank_fk",
                    "row": row,
                }
            )

        # FK values that do not exist in parent table
        cur = conn.execute(f"""
            SELECT child.*
            FROM {table} child
            LEFT JOIN {parent_table} parent
            ON child.{fk_col} = parent.{parent_col}
            WHERE child.{fk_col} IS NOT NULL
              AND child.{fk_col} != ''
              AND parent.{parent_col} IS NULL
        """)
        for row in cur.fetchall():
            issues.append(
                {
                    "table": table,
                    "fk_column": fk_col,
                    "fk_value": row[0],
                    "issue": "orphan_fk",
                    "row": row,
                }
            )

    return issues


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

    actual_output_dir = output_dir or (p.exports_dir / "jules" / "sqlite_reports")

    with contextlib.closing(sqlite3.connect(actual_db_path)) as conn:
        tables = get_tables(conn)
        schema = {}

        pk_issues = []
        fk_issues = []

        for table in tables:
            pk_cols = get_primary_keys(conn, table)
            fk_cols = get_foreign_keys(conn, table)

            schema[table] = {"primary_keys": pk_cols, "foreign_keys": fk_cols}

            pk_issues.extend(get_blank_pk_rows(conn, table, pk_cols))
            fk_issues.extend(get_fk_issues(conn, table, fk_cols))

    if write_enabled:
        actual_output_dir.mkdir(parents=True, exist_ok=True)

        # Write schema report
        with (actual_output_dir / "schema_report.json").open(
            "w", encoding="utf-8"
        ) as f:
            json.dump(schema, f, indent=2)

        # Write PK issues
        with (actual_output_dir / "pk_issues.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["table", "pk_column", "row"])
            for issue in pk_issues:
                writer.writerow([issue["table"], issue["pk_column"], issue["row"]])

        # Write FK issues
        with (actual_output_dir / "fk_issues.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["table", "fk_column", "fk_value", "issue", "row"])
            for issue in fk_issues:
                writer.writerow(
                    [
                        issue["table"],
                        issue["fk_column"],
                        issue["fk_value"],
                        issue["issue"],
                        issue["row"],
                    ]
                )
        logging.info("Audit complete. Reports written to: %s", actual_output_dir)
        logging.info("Schema → %s", actual_output_dir / "schema_report.json")
        logging.info("PK issues → %s", actual_output_dir / "pk_issues.csv")
        logging.info("FK issues → %s", actual_output_dir / "fk_issues.csv")
    else:
        logging.info(
            "Audit complete (dry run). Found %d PK issues and %d FK issues.",
            len(pk_issues),
            len(fk_issues),
        )

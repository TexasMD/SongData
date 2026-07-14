import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Sequence

import pandas as pd

DEFAULT_DB_PATH = Path(
    os.environ.get(
        "MUSICDB_SQLITE_PATH",
        r"D:\Music\MusicDB\data\staging\jules\music_antigravity_review.sqlite",
    )
)

def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Gets a read-only connection to the SQLite database."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")

    # Use URI mode for read-only connection
    db_uri = f"file:{db_path.absolute().as_posix()}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn

def is_safe_query(query: str) -> bool:
    """Basic sanity check to ensure the query is a SELECT statement."""
    # Remove leading whitespace and comments for checking
    cleaned = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip().upper()

    if not cleaned.startswith("SELECT"):
        return False

    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "GRANT", "REVOKE", "ATTACH", "PRAGMA", "DETACH", "CREATE", "REPLACE"]
    for word in forbidden:
        if re.search(rf'\b{word}\b', cleaned):
            return False

    return True

def execute_query(
    query: str,
    params: Sequence[Any] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Executes a SQL query and returns a pandas DataFrame."""
    if not is_safe_query(query):
        raise ValueError("Invalid query: Only read-only SELECT queries are allowed.")

    with get_connection(db_path) as conn:
        df = pd.read_sql_query(query, conn, params=params or [])
    return df

def get_schema_summary(db_path: Path = DEFAULT_DB_PATH) -> str:
    """Returns a string describing the database schema for the LLM."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        schema_lines = []
        for (table_name,) in tables:
            # Skip sqlite internal tables
            if table_name.startswith("sqlite_"):
                continue
            schema_lines.append(f"Table: {table_name}")
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            for col in columns:
                schema_lines.append(f"  - {col['name']} ({col['type']})")
            schema_lines.append("") # Empty line between tables

        return "\n".join(schema_lines)

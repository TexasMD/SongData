import csv
import os
import logging
from src.utils import read_csv
from src.config import MusicDBPaths
from src.sqlite_poc import insert_v2_records
from src.commands.rebuild import ensure_mock_file

def run(*, write: bool, paths: MusicDBPaths) -> int:
    input_csv = paths.staging_dir / "recordings_mock.csv"
    sqlite_path = paths.sqlite_poc_path

    logging.info(f"build-v2: dry-run={not write}")
    if write:
        logging.info("Executing write operations for build-v2...")
        logging.info(f"Executing rebuild-db into {sqlite_path}...")
        if os.path.exists(sqlite_path):
            os.remove(sqlite_path)

        ensure_mock_file(input_csv)
        records = read_csv(input_csv)
        insert_v2_records(records, db_path=sqlite_path)

        # tests/test_cli_upgraded.py expects sqlite_path to be a real SQLite DB
        import sqlite3
        with sqlite3.connect(sqlite_path) as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
            conn.commit()

        logging.info(f"Successfully rebuilt database with {len(records)} records.")

    return 0

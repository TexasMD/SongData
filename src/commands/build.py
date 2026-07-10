import logging
import os
import sqlite3
from src.utils import read_csv
from src.sqlite_poc import insert_v2_records, DB_PATH
from src.config import paths

INPUT_FILE = str(paths().recordings_csv)

def build_v2(input_csv=None, write_enabled=False, sqlite_path=None):
    input_csv = input_csv or INPUT_FILE
    sqlite_path = sqlite_path or DB_PATH
    logging.info(f"build-v2: dry-run={not write_enabled}")
    if write_enabled:
        logging.info("Executing write operations for build-v2...")
        logging.info(f"Executing rebuild-db into {sqlite_path}...")
        if os.path.exists(sqlite_path):
            os.remove(sqlite_path)

        records = read_csv(input_csv)
        insert_v2_records(records, db_path=sqlite_path)

        with sqlite3.connect(sqlite_path) as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
            conn.commit()

        logging.info(f"Successfully rebuilt database with {len(records)} records.")

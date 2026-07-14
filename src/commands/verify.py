import csv
import os
import logging
from src.utils import read_csv
from src.schema import validate_record
from src.config import MusicDBPaths
from src.commands.rebuild import ensure_mock_file

def run(*, write: bool, paths: MusicDBPaths) -> int:
    logging.info("verify...")
    input_csv = paths.staging_dir / "recordings_mock.csv"
    ensure_mock_file(input_csv)
    records = read_csv(input_csv)
    all_errors = []

    for i, record in enumerate(records):
        errors = validate_record(record)
        if errors:
            all_errors.append(f"Row {i+1} ({record.get('Title', 'Unknown')}): {errors}")

    if all_errors:
        logging.info("Validation errors found:")
        for error in all_errors:
            logging.info(error)
        return 1
    else:
        logging.info(f"Validation successful for {len(records)} records.")
        return 0

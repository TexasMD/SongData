import logging
from src.utils import read_csv
from src.schema import validate_record
from src.config import paths

INPUT_FILE = str(paths().recordings_csv)

def verify():
    logging.info("verify...")
    records = read_csv(INPUT_FILE)
    all_errors = []

    for i, record in enumerate(records):
        errors = validate_record(record)
        if errors:
            all_errors.append(f"Row {i+1} ({record.get('Title', 'Unknown')}): {errors}")

    if all_errors:
        logging.info("Validation errors found:")
        for error in all_errors:
            logging.info(error)
    else:
        logging.info(f"Validation successful for {len(records)} records.")

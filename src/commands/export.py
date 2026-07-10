import logging
import os
import json
from src.utils import read_csv
from src.config import paths

INPUT_FILE = str(paths().recordings_csv)

def export_view(write_enabled=False):
    logging.info("export-view...")
    export_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "exports", "jules"
    )
    os.makedirs(export_dir, exist_ok=True)
    export_file = os.path.join(export_dir, "export.json")
    records = read_csv(INPUT_FILE)

    if write_enabled:
        with open(export_file, "w") as f:
            json.dump(records, f, indent=2)
        logging.info(f"Exported to {export_file}")
    else:
        logging.info(f"{__name__.split('.')[-1]}: dry-run: Would export to {export_file}")

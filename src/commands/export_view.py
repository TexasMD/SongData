import csv
import os
import logging
import json
from src.utils import read_csv
from src.config import MusicDBPaths
from src.commands.rebuild import ensure_mock_file

def run(*, write: bool, paths: MusicDBPaths) -> int:
    logging.info("export-view...")
    export_dir = paths.exports_dir / "jules"
    os.makedirs(export_dir, exist_ok=True)
    export_file = os.path.join(export_dir, "export.json")

    input_csv = paths.staging_dir / "recordings_mock.csv"
    ensure_mock_file(input_csv)
    records = read_csv(input_csv)

    if write:
        with open(export_file, "w") as f:
            json.dump(records, f, indent=2)
        logging.info(f"Exported to {export_file}")
    else:
        logging.info(f"dry-run: Would export to {export_file}")

    return 0

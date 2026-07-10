import logging
import os
import json
from src.utils import read_csv
from src.quality import generate_quality_report as src_generate_quality_report
from src.config import paths

INPUT_FILE = str(paths().recordings_csv)

def generate_quality_report(input_csv=None, write_enabled=False, export_dir=None):
    input_csv = input_csv or INPUT_FILE
    logging.info(f"quality-report: dry-run={not write_enabled}")
    records = read_csv(input_csv)
    report = src_generate_quality_report(records)

    logging.info("Quality Report Summary:")
    logging.info(f"Total songs: {len(records)}")

    if write_enabled:
        if export_dir is None:
            export_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "exports"
            )
        os.makedirs(export_dir, exist_ok=True)

        json_file = os.path.join(export_dir, "quality_report.json")
        md_file = os.path.join(export_dir, "quality_report.md")

        with open(json_file, "w") as f:
            json.dump(report, f, indent=2)
        logging.info(f"Exported JSON report to {json_file}")

        with open(md_file, "w") as f:
            f.write("# Quality Report\n\n")
            for k, v in report.items():
                f.write(f"- **{k}**: {v}\n")
        logging.info(f"Exported Markdown report to {md_file}")
    else:
        logging.info("Quality Report Summary:")
        logging.info(f"Total songs: {len(records)}")
        logging.info("DRY RUN: Would export JSON and Markdown reports to data/exports")
        logging.info("Report contents:")
        logging.info(json.dumps(report, indent=2))
    return report

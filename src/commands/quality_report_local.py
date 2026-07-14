import csv
import os
import logging
import json
from src.utils import read_csv
from src.config import MusicDBPaths
from src.quality import generate_quality_report as src_generate_quality_report
from src.commands.rebuild import ensure_mock_file

def run(*, write: bool, paths: MusicDBPaths) -> int:
    input_csv = paths.staging_dir / "recordings_mock.csv"

    logging.info(f"quality-report: dry-run={not write}")

    ensure_mock_file(input_csv)
    records = read_csv(input_csv)
    report = src_generate_quality_report(records)

    logging.info("Quality Report Summary:")
    logging.info(f"Total songs: {len(records)}")

    if write:
        export_dir = paths.exports_dir
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

    return 0

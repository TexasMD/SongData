import logging
import os
import csv
from src.utils import read_csv, backup_file
from src.config import paths

INPUT_FILE = str(paths().recordings_csv)

def rebuild(write_enabled=False):
    """
    Rebuilds the compatibility Main_Song_Database.csv from recordings.csv.
    """
    logging.info(f"rebuild: dry-run={not write_enabled}")
    input_file = INPUT_FILE
    output_dir = "data/staging/jules"
    output_file = os.path.join(output_dir, "Main_Song_Database.csv")

    if write_enabled:
        logging.info(f"Rebuilding {output_file} from {input_file}...")
        os.makedirs(output_dir, exist_ok=True)

        if os.path.exists(output_file):
            backup_path = backup_file(output_file)
            if backup_path:
                logging.info(f"Created backup at {backup_path}")

        records_to_export = []
        records = read_csv(input_file)
        for row in records:
            comp_row = {
                "Title": row.get("Title", ""),
                "Artist": row.get("Artist", ""),
                "Version": row.get("Version", ""),
                "Spotify ID": row.get("Spotify Track ID", ""),
                "MBID": row.get("MusicBrainz ID", ""),
                "BPM": row.get("BPM", ""),
                "Key": row.get("Key", ""),
                "Playlists": row.get("Playlists", ""),
                "Notes": f"{row.get('Arrangement', '')} {row.get('SHS Link', '')}".strip(),
            }
            records_to_export.append(comp_row)

        with open(output_file, "w", newline="") as f:
            if records_to_export:
                writer = csv.DictWriter(f, fieldnames=records_to_export[0].keys())
                writer.writeheader()
                writer.writerows(records_to_export)

        logging.info(
            f"Successfully rebuilt {output_file} with {len(records_to_export)} records."
        )
    else:
        logging.info(f"DRY RUN: Would rebuild {output_file} from {input_file}")
        if os.path.exists(output_file):
            logging.info(f"DRY RUN: Would create backup of {output_file}")

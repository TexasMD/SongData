import csv
import os
import logging
from src.utils import backup_file, read_csv
from src.config import MusicDBPaths

def ensure_mock_file(mock_path):
    if not os.path.exists(mock_path):
        os.makedirs(os.path.dirname(mock_path), exist_ok=True)
        with open(mock_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "Recording ID",
                    "Song ID",
                    "Title",
                    "Artist",
                    "Version",
                    "Spotify Track ID",
                    "MusicBrainz ID",
                    "BPM",
                    "Key",
                    "Playlists",
                    "Arrangement",
                    "SHS Link",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Recording ID": "rec1",
                    "Song ID": "song1",
                    "Title": "Test Song",
                    "Artist": "Test Artist",
                    "Version": "",
                    "Spotify Track ID": "sp1",
                    "MusicBrainz ID": "mb1",
                    "BPM": "120",
                    "Key": "C",
                    "Playlists": "Test;Cool",
                    "Arrangement": "Acoustic",
                    "SHS Link": "http://shs.com/1",
                }
            )

def run(*, write: bool, paths: MusicDBPaths) -> int:
    """
    Rebuilds the compatibility Main_Song_Database.csv from recordings.csv.
    """
    input_file = paths.staging_dir / "recordings_mock.csv"
    output_dir = paths.staging_dir / "jules"
    output_file = output_dir / "Main_Song_Database.csv"

    logging.info(f"rebuild: dry-run={not write}")

    ensure_mock_file(input_file)

    if write:
        logging.info(f"Rebuilding {output_file} from {input_file}...")
        os.makedirs(output_dir, exist_ok=True)

        # Backup before writing
        if os.path.exists(output_file):
            backup_path = backup_file(output_file)
            if backup_path:
                logging.info(f"Created backup at {backup_path}")

        records_to_export = []
        records = read_csv(input_file)
        for row in records:
            # Mapping as per docs/SCHEMA_V2.md
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

    return 0

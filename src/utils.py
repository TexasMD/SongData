import os
import csv
import shutil
from datetime import datetime
from typing import List, Dict, Any

def backup_file(filepath: str) -> str:
    """
    Creates a timestamped backup of the given file.
    Returns the backup filepath.
    """
    if not os.path.exists(filepath):
        return ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_name = os.path.dirname(filepath)
    base_name = os.path.basename(filepath)
    name, ext = os.path.splitext(base_name)

    backup_name = f"{name}_{timestamp}.bak{ext}"
    backup_path = os.path.join(dir_name, backup_name)

    shutil.copy2(filepath, backup_path)
    return backup_path

def read_csv(filepath: str) -> List[Dict[str, Any]]:
    """
    Reads a CSV file and returns a list of dictionaries.
    """
    records = []
    if not os.path.exists(filepath):
        return records

    with open(filepath, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records

"""build-v2 command implementation."""

from __future__ import annotations

import subprocess
import sys

from src.config import MusicDBPaths


def run(*, write: bool, paths: MusicDBPaths) -> int:
    script_path = paths.scripts_dir / "build_songdb_v2.py"
    if not script_path.exists():
        print(f"Error: {script_path} not found.")
        return 1

    if not write:
        print("build-v2: dry-run=True")
        print(f"DRY RUN: Would rebuild derived CSVs in {paths.songdb_v2_dir}")
        print("Pass --write to run build_songdb_v2.py.")
        return 0

    print("build-v2: dry-run=False")
    print(f"Executing write operations via {script_path}")
    return subprocess.run([sys.executable, str(script_path)], cwd=paths.root).returncode

"""build-reference-db command implementation."""

from __future__ import annotations

from src.config import MusicDBPaths
from src.reference_db import build_reference_db


def run(*, write: bool, paths: MusicDBPaths) -> int:
    if not write:
        print("build-reference-db: dry-run=True")
        print(f"DRY RUN: Would build {paths.reference_db_path}")
        print("DRY RUN: Would import source registry, source matrix, and identifier crosswalks.")
        return 0

    print("build-reference-db: dry-run=False")
    summary = build_reference_db(paths)
    print(f"Built reference DB at {paths.reference_db_path}")
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0

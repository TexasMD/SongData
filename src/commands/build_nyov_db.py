"""build-nyov-db command implementation."""

from __future__ import annotations

from pathlib import Path

from src.config import MusicDBPaths
from src.nyov_db import build_nyov_db


def run(
    *,
    write: bool,
    paths: MusicDBPaths,
    seed_csv: Path | None = None,
    basket_dir: Path | None = None,
    output_db: Path | None = None,
) -> int:
    seed_csv = seed_csv or paths.basket_dir / "MyMusicBasefiltered_fixed.csv"
    basket_dir = basket_dir or paths.basket_dir
    output_db = output_db or paths.nyov_db_path
    if not write:
        print("build-nyov-db: dry-run=True")
        print(f"Seed CSV: {seed_csv}")
        print(f"Basket dir: {basket_dir}")
        print(f"Output DB: {output_db}")
        print("DRY RUN: Would inventory basket CSV/TXT/XLSX/DOCX/ZIP files into the NYOV evidence database.")
        return 0

    print("build-nyov-db: dry-run=False")
    summary = build_nyov_db(paths, seed_csv=seed_csv, basket_dir=basket_dir, output_db=output_db)
    print(f"Built NYOV DB at {summary['output_db']}")
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0

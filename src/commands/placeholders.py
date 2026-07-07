"""Dry-run-safe placeholder command implementations."""

from __future__ import annotations

from src.config import MusicDBPaths


def review_active_vs_staged(*, paths: MusicDBPaths) -> int:
    print("review-active-vs-staged: dry-run=True")
    print(f"Review artifacts live under {paths.exports_dir / 'active_vs_staged_review'}")
    return 0


def import_playlist(*, write: bool, paths: MusicDBPaths) -> int:
    print(f"import-playlist: dry-run={not write}")
    if write:
        print(f"WRITE MODE placeholder only; no active database write performed at {paths.active_main_csv}.")
    else:
        print("DRY RUN: Would import playlist only through a dedicated reviewed importer.")
    return 0


def verify(*, write: bool, paths: MusicDBPaths) -> int:
    print(f"verify: dry-run={not write}")
    if write:
        print("WRITE MODE placeholder only; no verification writes performed.")
    else:
        print("DRY RUN: Would run external verification without modifying CSVs.")
    return 0


def export_view(*, paths: MusicDBPaths) -> int:
    print("export-view: dry-run=True")
    print(f"Export views should be written under {paths.exports_dir}.")
    return 0

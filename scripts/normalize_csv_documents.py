#!/usr/bin/env python3
"""Normalize compatibility fonts, punctuation, and spacing in generated CSV docs.

The goal is display-safe cleanup: preserve genuine diacritics, fold typographic
noise, and keep the raw source database untouched unless explicitly staged.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Allow direct execution from the repo root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.normalization import normalize_display_text


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = PROJECT_DIR / "data" / "exports" / "codex" / "unicode_normalization"
DEFAULT_TARGETS = [
    PROJECT_DIR / "data" / "processed" / "Main_Song_Database.csv",
    PROJECT_DIR / "data" / "exports" / "codex" / "youtube_music_playlist_videos_deduped.csv",
    PROJECT_DIR / "data" / "exports" / "codex" / "youtube_music_takeout_verified.csv",
    PROJECT_DIR / "data" / "exports" / "codex" / "youtube_music_takeout_unmatched.csv",
    PROJECT_DIR / "SongDB_v2" / "songs.csv",
    PROJECT_DIR / "SongDB_v2" / "recordings.csv",
    PROJECT_DIR / "SongDB_v2" / "external_links.csv",
    PROJECT_DIR / "SongDB_v2" / "playlist_membership.csv",
    PROJECT_DIR / "SongDB_v2" / "youtube_music_takeout_verified.csv",
    PROJECT_DIR / "SongDB_v2" / "youtube_music_takeout_unmatched.csv",
]


@dataclass
class NormalizationStats:
    file: Path
    rows_seen: int = 0
    cells_changed: int = 0
    rows_changed: int = 0


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    normalized_rows: list[dict[str, str]] = []
    incidents: list[dict[str, str]] = []

    for row_index, row in enumerate(rows, start=2):
        changed = False
        new_row: dict[str, str] = {}
        for field, value in row.items():
            cleaned = normalize_display_text(value)
            new_row[field] = cleaned
            if cleaned != (value or ""):
                changed = True
                incidents.append(
                    {
                        "row": str(row_index),
                        "field": field,
                        "before": value or "",
                        "after": cleaned,
                    }
                )
        normalized_rows.append(new_row)
        if changed:
            new_row["_changed"] = "1"

    return normalized_rows, incidents


def normalize_file(path: Path, *, in_place: bool, report_dir: Path) -> NormalizationStats:
    headers, rows = read_csv(path)
    normalized_rows, incidents = normalize_rows(rows)
    stats = NormalizationStats(file=path, rows_seen=len(rows), cells_changed=len(incidents), rows_changed=sum(1 for row in normalized_rows if row.get("_changed")))

    if in_place:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            for row in normalized_rows:
                row.pop("_changed", None)
                writer.writerow(row)
    else:
        out_path = report_dir / path.name
        for row in normalized_rows:
            row.pop("_changed", None)
        write_csv(out_path, headers, normalized_rows)

    incident_path = report_dir / f"{path.stem}.incidents.csv"
    if incidents:
        write_csv(incident_path, ["row", "field", "before", "after"], incidents)
    else:
        incident_path.write_text("row,field,before,after\n", encoding="utf-8")

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize compatibility-font and diacritic issues in generated CSV docs.")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--in-place", action="store_true", help="Rewrite generated CSV docs in place.")
    parser.add_argument("--targets", nargs="*", type=Path, default=DEFAULT_TARGETS)
    args = parser.parse_args()

    report_dir = args.report_dir
    report_dir.mkdir(parents=True, exist_ok=True)

    stats: list[NormalizationStats] = []
    for target in args.targets:
        if not target.exists():
            continue
        stats.append(normalize_file(target, in_place=args.in_place, report_dir=report_dir))

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "in_place": args.in_place,
        "targets_seen": len(args.targets),
        "files_processed": len(stats),
        "rows_seen": sum(item.rows_seen for item in stats),
        "rows_changed": sum(item.rows_changed for item in stats),
        "cells_changed": sum(item.cells_changed for item in stats),
        "report_dir": str(report_dir),
    }
    (report_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

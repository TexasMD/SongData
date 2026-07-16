from __future__ import annotations

import csv
import itertools
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.config import MusicDBPaths


DEFAULT_INPUT_DIR = Path("data/staging/external/million_song_secondhand")
DEFAULT_OUTPUT_DIR = Path("data/staging/codex/msd_secondhand")
DATASET_URL = "http://millionsongdataset.com/secondhand/"
SOURCE_NAME = "Million Song Dataset SecondHandSongs subset"


@dataclass(frozen=True)
class MsdShsPerformance:
    dataset_split: str
    clique_id: str
    clique_title: str
    work_ids: tuple[str, ...]
    msd_track_id: str
    msd_artist_id: str
    shs_performance_id: str
    source_file: str
    source_line: int


def _clean(value: object) -> str:
    return str(value or "").strip()


def _is_known_id(value: str) -> bool:
    return bool(value) and not value.startswith("-")


def _split_name(path: Path) -> str:
    name = path.name.lower()
    if "train" in name:
        return "train"
    if "test" in name:
        return "test"
    return path.stem


def _parse_header(line: str) -> tuple[tuple[str, ...], str]:
    body = line[1:].strip()
    if "," not in body:
        raise ValueError(f"Invalid clique header: {line}")
    parts = [part.strip() for part in body.split(",")]
    title = parts[-1]
    work_ids = tuple(part for part in parts[:-1] if part)
    return work_ids, title


def parse_msd_secondhand_file(path: Path, dataset_split: str | None = None) -> list[MsdShsPerformance]:
    dataset_split = dataset_split or _split_name(path)
    rows: list[MsdShsPerformance] = []
    current_work_ids: tuple[str, ...] = ()
    current_title = ""
    clique_index = 0
    clique_id = ""

    with path.open("r", encoding="utf-8", newline="") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("%"):
                clique_index += 1
                current_work_ids, current_title = _parse_header(line)
                clique_id = f"{dataset_split}_{clique_index:05d}"
                continue

            parts = line.split("<SEP>")
            if len(parts) != 3:
                raise ValueError(f"Invalid performance row at {path}:{line_number}: {line}")
            if not clique_id:
                raise ValueError(f"Performance row before clique header at {path}:{line_number}")
            rows.append(
                MsdShsPerformance(
                    dataset_split=dataset_split,
                    clique_id=clique_id,
                    clique_title=current_title,
                    work_ids=current_work_ids,
                    msd_track_id=_clean(parts[0]),
                    msd_artist_id=_clean(parts[1]),
                    shs_performance_id=_clean(parts[2]),
                    source_file=path.name,
                    source_line=line_number,
                )
            )
    return rows


def parse_input_dir(input_dir: Path) -> list[MsdShsPerformance]:
    paths = [
        input_dir / "shs_dataset_train.txt",
        input_dir / "shs_dataset_test.txt",
    ]
    missing = [path for path in paths if not path.exists()]
    if missing:
        missing_text = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Missing MSD SHS input file(s): {missing_text}")

    rows: list[MsdShsPerformance] = []
    for path in paths:
        rows.extend(parse_msd_secondhand_file(path))
    return rows


def clique_rows(performances: Iterable[MsdShsPerformance]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[MsdShsPerformance]] = {}
    for row in performances:
        grouped.setdefault((row.dataset_split, row.clique_id), []).append(row)

    rows = []
    for (dataset_split, clique_id), items in sorted(grouped.items()):
        first = items[0]
        known_work_ids = [work_id for work_id in first.work_ids if _is_known_id(work_id)]
        rows.append(
            {
                "dataset_split": dataset_split,
                "clique_id": clique_id,
                "clique_title": first.clique_title,
                "shs_work_ids": ";".join(first.work_ids),
                "primary_shs_work_id": known_work_ids[0] if known_work_ids else "",
                "shs_work_urls": ";".join(
                    f"https://secondhandsongs.com/work/{work_id}"
                    for work_id in known_work_ids
                ),
                "track_count": len(items),
                "source": SOURCE_NAME,
                "source_url": DATASET_URL,
            }
        )
    return rows


def performance_rows(performances: Iterable[MsdShsPerformance]) -> list[dict[str, object]]:
    rows = []
    for row in performances:
        known_work_ids = [work_id for work_id in row.work_ids if _is_known_id(work_id)]
        known_performance_id = row.shs_performance_id if _is_known_id(row.shs_performance_id) else ""
        rows.append(
            {
                "dataset_split": row.dataset_split,
                "clique_id": row.clique_id,
                "clique_title": row.clique_title,
                "msd_track_id": row.msd_track_id,
                "msd_artist_id": row.msd_artist_id,
                "shs_performance_id": known_performance_id,
                "shs_performance_url": (
                    f"https://secondhandsongs.com/performance/{known_performance_id}"
                    if known_performance_id
                    else ""
                ),
                "shs_work_ids": ";".join(row.work_ids),
                "shs_work_urls": ";".join(
                    f"https://secondhandsongs.com/work/{work_id}"
                    for work_id in known_work_ids
                ),
                "source_file": row.source_file,
                "source_line": row.source_line,
                "source": SOURCE_NAME,
                "source_url": DATASET_URL,
            }
        )
    return rows


def connection_rows(performances: Iterable[MsdShsPerformance]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[MsdShsPerformance]] = {}
    for row in performances:
        grouped.setdefault((row.dataset_split, row.clique_id), []).append(row)

    rows = []
    for (dataset_split, clique_id), items in sorted(grouped.items()):
        for left, right in itertools.combinations(items, 2):
            rows.append(
                {
                    "dataset_split": dataset_split,
                    "clique_id": clique_id,
                    "clique_title": left.clique_title,
                    "left_msd_track_id": left.msd_track_id,
                    "right_msd_track_id": right.msd_track_id,
                    "left_shs_performance_id": left.shs_performance_id if _is_known_id(left.shs_performance_id) else "",
                    "right_shs_performance_id": right.shs_performance_id if _is_known_id(right.shs_performance_id) else "",
                    "shs_work_ids": ";".join(left.work_ids),
                    "relationship_type": "same_shs_work_clique",
                    "confidence": "dataset_ground_truth",
                    "source": SOURCE_NAME,
                    "source_url": DATASET_URL,
                }
            )
    return rows


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _replace_table(conn: sqlite3.Connection, table: str, rows: list[dict[str, object]]) -> None:
    conn.execute(f"DROP TABLE IF EXISTS {table}")
    if not rows:
        return
    columns = list(rows[0].keys())
    column_sql = ", ".join(f"{column} TEXT" for column in columns)
    conn.execute(f"CREATE TABLE {table} ({column_sql})")
    placeholders = ", ".join(["?"] * len(columns))
    conn.executemany(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        [[row.get(column, "") for column in columns] for row in rows],
    )


def write_outputs(performances: list[MsdShsPerformance], output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cliques = clique_rows(performances)
    performance_records = performance_rows(performances)
    connections = connection_rows(performances)

    cliques_csv = output_dir / "msd_shs_cliques.csv"
    performances_csv = output_dir / "msd_shs_performances.csv"
    connections_csv = output_dir / "msd_shs_connections.csv"
    sqlite_path = output_dir / "msd_secondhand.sqlite"
    summary_json = output_dir / "summary.json"

    _write_csv(cliques_csv, cliques)
    _write_csv(performances_csv, performance_records)
    _write_csv(connections_csv, connections)

    if sqlite_path.exists():
        sqlite_path.unlink()
    with sqlite3.connect(sqlite_path) as conn:
        _replace_table(conn, "msd_shs_cliques", cliques)
        _replace_table(conn, "msd_shs_performances", performance_records)
        _replace_table(conn, "msd_shs_connections", connections)
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_msd_shs_performances_track
                ON msd_shs_performances(msd_track_id);
            CREATE INDEX IF NOT EXISTS idx_msd_shs_performances_performance
                ON msd_shs_performances(shs_performance_id);
            CREATE INDEX IF NOT EXISTS idx_msd_shs_connections_left
                ON msd_shs_connections(left_msd_track_id);
            CREATE INDEX IF NOT EXISTS idx_msd_shs_connections_right
                ON msd_shs_connections(right_msd_track_id);
            """
        )
        conn.commit()

    split_counts: dict[str, int] = {}
    for row in performances:
        split_counts[row.dataset_split] = split_counts.get(row.dataset_split, 0) + 1

    summary = {
        "source": SOURCE_NAME,
        "source_url": DATASET_URL,
        "clique_count": len(cliques),
        "performance_count": len(performance_records),
        "connection_count": len(connections),
        "split_performance_counts": split_counts,
        "known_shs_performance_count": sum(
            1 for row in performances if _is_known_id(row.shs_performance_id)
        ),
        "negative_or_missing_shs_performance_count": sum(
            1 for row in performances if not _is_known_id(row.shs_performance_id)
        ),
        "outputs": {
            "cliques_csv": str(cliques_csv),
            "performances_csv": str(performances_csv),
            "connections_csv": str(connections_csv),
            "sqlite": str(sqlite_path),
        },
    }
    summary_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    summary["outputs"]["summary_json"] = str(summary_json)
    return summary


def build_import(input_dir: Path, output_dir: Path) -> dict[str, object]:
    performances = parse_input_dir(input_dir)
    return write_outputs(performances, output_dir)


def run(
    *,
    write: bool,
    paths: MusicDBPaths,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, object] | None:
    input_dir = input_dir or paths.root / DEFAULT_INPUT_DIR
    output_dir = output_dir or paths.root / DEFAULT_OUTPUT_DIR
    if not write:
        print(f"dry-run: Would import MSD SHS files from {input_dir}")
        print(f"dry-run: Would write normalized outputs to {output_dir}")
        return None

    summary = build_import(input_dir, output_dir)
    print(f"Imported {summary['performance_count']} MSD SHS performances")
    print(f"Grouped into {summary['clique_count']} SHS/MSD cliques")
    print(f"Wrote {summary['connection_count']} pairwise clique connections")
    print(f"SQLite: {summary['outputs']['sqlite']}")
    return summary

from __future__ import annotations

import csv
import itertools
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.config import MusicDBPaths
from src.normalization import normalize_search_text


DEFAULT_INPUT_DIR = Path("data/staging/external/million_song_secondhand")
DEFAULT_OUTPUT_DIR = Path("data/staging/codex/msd_secondhand")
DEFAULT_TRACK_METADATA_DB = Path("data/staging/external/million_song/track_metadata.db")
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


@dataclass(frozen=True)
class MsdTrackMetadata:
    msd_track_id: str
    title: str
    song_id: str
    release: str
    msd_artist_id: str
    artist_mbid: str
    artist_name: str
    duration: str
    year: str
    track_7digitalid: str
    shs_performance_id: str
    shs_work_id: str


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


def _chunked(values: list[str], size: int = 900) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index:index + size]


def load_track_metadata(metadata_db: Path, track_ids: Iterable[str]) -> dict[str, MsdTrackMetadata]:
    ids = sorted({track_id for track_id in track_ids if track_id})
    if not metadata_db.exists():
        raise FileNotFoundError(f"Missing MSD track metadata DB: {metadata_db}")

    rows: dict[str, MsdTrackMetadata] = {}
    with sqlite3.connect(metadata_db) as conn:
        for chunk in _chunked(ids):
            placeholders = ", ".join(["?"] * len(chunk))
            query = f"""
                SELECT
                    track_id,
                    title,
                    song_id,
                    release,
                    artist_id,
                    artist_mbid,
                    artist_name,
                    duration,
                    year,
                    track_7digitalid,
                    shs_perf,
                    shs_work
                FROM songs
                WHERE track_id IN ({placeholders})
            """
            for row in conn.execute(query, chunk):
                rows[row[0]] = MsdTrackMetadata(
                    msd_track_id=_clean(row[0]),
                    title=_clean(row[1]),
                    song_id=_clean(row[2]),
                    release=_clean(row[3]),
                    msd_artist_id=_clean(row[4]),
                    artist_mbid=_clean(row[5]),
                    artist_name=_clean(row[6]),
                    duration=_clean(row[7]),
                    year=_clean(row[8]),
                    track_7digitalid=_clean(row[9]),
                    shs_performance_id="" if not _is_known_id(_clean(row[10])) else _clean(row[10]),
                    shs_work_id="" if not _is_known_id(_clean(row[11])) else _clean(row[11]),
                )
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


def metadata_rows(
    performances: Iterable[MsdShsPerformance],
    metadata: dict[str, MsdTrackMetadata],
) -> list[dict[str, object]]:
    rows = []
    for row in performances:
        item = metadata.get(row.msd_track_id)
        if item is None:
            continue
        known_work_ids = [work_id for work_id in row.work_ids if _is_known_id(work_id)]
        performance_id = row.shs_performance_id if _is_known_id(row.shs_performance_id) else item.shs_performance_id
        rows.append(
            {
                "dataset_split": row.dataset_split,
                "clique_id": row.clique_id,
                "clique_title": row.clique_title,
                "msd_track_id": item.msd_track_id,
                "msd_song_id": item.song_id,
                "title": item.title,
                "artist_name": item.artist_name,
                "release": item.release,
                "year": item.year,
                "duration": item.duration,
                "msd_artist_id": item.msd_artist_id,
                "artist_mbid": item.artist_mbid,
                "track_7digitalid": item.track_7digitalid,
                "shs_performance_id": performance_id,
                "shs_performance_url": (
                    f"https://secondhandsongs.com/performance/{performance_id}"
                    if performance_id
                    else ""
                ),
                "shs_work_ids": ";".join(row.work_ids),
                "shs_work_urls": ";".join(
                    f"https://secondhandsongs.com/work/{work_id}"
                    for work_id in known_work_ids
                ),
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


def _read_musicdb_recordings(recordings_csv: Path) -> list[dict[str, str]]:
    if not recordings_csv.exists():
        return []
    with recordings_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _recording_match_key(row: dict[str, str]) -> tuple[str, str]:
    return (
        normalize_search_text(row.get("Canonical Title") or row.get("Title") or ""),
        normalize_search_text(row.get("Artist") or ""),
    )


def _metadata_match_key(row: dict[str, object]) -> tuple[str, str]:
    return (
        normalize_search_text(str(row.get("title") or "")),
        normalize_search_text(str(row.get("artist_name") or "")),
    )


def musicdb_match_rows(
    enriched_rows: list[dict[str, object]],
    recordings_csv: Path,
) -> list[dict[str, object]]:
    recordings = _read_musicdb_recordings(recordings_csv)
    by_key: dict[tuple[str, str], list[dict[str, str]]] = {}
    for recording in recordings:
        key = _recording_match_key(recording)
        if all(key):
            by_key.setdefault(key, []).append(recording)

    rows = []
    for item in enriched_rows:
        key = _metadata_match_key(item)
        if not all(key):
            continue
        matches = by_key.get(key, [])
        if not matches:
            continue
        match_confidence = "exact_normalized_title_artist"
        if len(matches) > 1:
            match_confidence = "ambiguous_exact_normalized_title_artist"
        for match in matches:
            rows.append(
                {
                    "recording_id": match.get("Recording ID", ""),
                    "song_id": match.get("Song ID", ""),
                    "musicdb_title": match.get("Title", ""),
                    "musicdb_artist": match.get("Artist", ""),
                    "msd_track_id": item.get("msd_track_id", ""),
                    "msd_title": item.get("title", ""),
                    "msd_artist": item.get("artist_name", ""),
                    "clique_id": item.get("clique_id", ""),
                    "clique_title": item.get("clique_title", ""),
                    "shs_performance_id": item.get("shs_performance_id", ""),
                    "shs_performance_url": item.get("shs_performance_url", ""),
                    "shs_work_ids": item.get("shs_work_ids", ""),
                    "match_confidence": match_confidence,
                    "source": SOURCE_NAME,
                }
            )
    return rows


def musicdb_connection_rows(match_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in match_rows:
        clique_id = str(row.get("clique_id") or "")
        if clique_id:
            grouped.setdefault(clique_id, []).append(row)

    rows = []
    seen: set[tuple[str, str, str]] = set()
    for clique_id, items in sorted(grouped.items()):
        for left, right in itertools.combinations(items, 2):
            left_id = str(left.get("recording_id") or "")
            right_id = str(right.get("recording_id") or "")
            if not left_id or not right_id or left_id == right_id:
                continue
            ordered = tuple(sorted([left_id, right_id]))
            key = (clique_id, ordered[0], ordered[1])
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "clique_id": clique_id,
                    "clique_title": left.get("clique_title", ""),
                    "left_recording_id": ordered[0],
                    "right_recording_id": ordered[1],
                    "relationship_type": "same_shs_work_clique",
                    "confidence": "candidate_exact_title_artist_crosswalk",
                    "source": SOURCE_NAME,
                }
            )
    return rows


def _first_by_recording(match_rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    for row in match_rows:
        recording_id = str(row.get("recording_id") or "")
        if recording_id and recording_id not in rows:
            rows[recording_id] = row
    return rows


def _confidence_counts(match_rows: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in match_rows:
        recording_id = str(row.get("recording_id") or "")
        if recording_id:
            counts[recording_id] = counts.get(recording_id, 0) + 1
    return counts


def _review_flags(
    connection: dict[str, object],
    left: dict[str, object],
    right: dict[str, object],
    match_counts: dict[str, int],
) -> str:
    flags: list[str] = []
    left_id = str(connection.get("left_recording_id") or "")
    right_id = str(connection.get("right_recording_id") or "")
    if left_id == right_id:
        flags.append("same_recording")
    if match_counts.get(left_id, 0) > 1 or match_counts.get(right_id, 0) > 1:
        flags.append("multiple_msd_matches_for_recording")
    if not left.get("shs_performance_url") or not right.get("shs_performance_url"):
        flags.append("missing_shs_performance_url")
    if normalize_search_text(str(left.get("musicdb_artist") or "")) == normalize_search_text(
        str(right.get("musicdb_artist") or "")
    ):
        flags.append("same_artist")
    if left.get("match_confidence") != "exact_normalized_title_artist" or right.get("match_confidence") != "exact_normalized_title_artist":
        flags.append("ambiguous_match")
    return ";".join(flags)


def musicdb_connection_review_rows(
    connection_candidates: list[dict[str, object]],
    match_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    match_by_recording = _first_by_recording(match_rows)
    match_counts = _confidence_counts(match_rows)
    rows = []

    for connection in connection_candidates:
        left_id = str(connection.get("left_recording_id") or "")
        right_id = str(connection.get("right_recording_id") or "")
        left = match_by_recording.get(left_id, {})
        right = match_by_recording.get(right_id, {})
        rows.append(
            {
                "review_status": "pending",
                "review_notes": "",
                "review_flags": _review_flags(connection, left, right, match_counts),
                "clique_id": connection.get("clique_id", ""),
                "clique_title": connection.get("clique_title", ""),
                "relationship_type": connection.get("relationship_type", ""),
                "candidate_confidence": connection.get("confidence", ""),
                "left_recording_id": left_id,
                "left_song_id": left.get("song_id", ""),
                "left_musicdb_title": left.get("musicdb_title", ""),
                "left_musicdb_artist": left.get("musicdb_artist", ""),
                "left_msd_track_id": left.get("msd_track_id", ""),
                "left_msd_title": left.get("msd_title", ""),
                "left_msd_artist": left.get("msd_artist", ""),
                "left_shs_performance_id": left.get("shs_performance_id", ""),
                "left_shs_performance_url": left.get("shs_performance_url", ""),
                "right_recording_id": right_id,
                "right_song_id": right.get("song_id", ""),
                "right_musicdb_title": right.get("musicdb_title", ""),
                "right_musicdb_artist": right.get("musicdb_artist", ""),
                "right_msd_track_id": right.get("msd_track_id", ""),
                "right_msd_title": right.get("msd_title", ""),
                "right_msd_artist": right.get("msd_artist", ""),
                "right_shs_performance_id": right.get("shs_performance_id", ""),
                "right_shs_performance_url": right.get("shs_performance_url", ""),
                "shs_work_ids": left.get("shs_work_ids") or right.get("shs_work_ids", ""),
                "source": SOURCE_NAME,
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _replace_table(
    conn: sqlite3.Connection,
    table: str,
    rows: list[dict[str, object]],
    columns: list[str] | None = None,
) -> None:
    conn.execute(f"DROP TABLE IF EXISTS {table}")
    columns = columns or (list(rows[0].keys()) if rows else [])
    if not columns:
        return
    column_sql = ", ".join(f"{column} TEXT" for column in columns)
    conn.execute(f"CREATE TABLE {table} ({column_sql})")
    if not rows:
        return
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


def add_metadata_outputs(
    summary: dict[str, object],
    performances: list[MsdShsPerformance],
    output_dir: Path,
    metadata_db: Path,
    recordings_csv: Path,
) -> dict[str, object]:
    metadata = load_track_metadata(metadata_db, [row.msd_track_id for row in performances])
    enriched = metadata_rows(performances, metadata)
    matches = musicdb_match_rows(enriched, recordings_csv)
    musicdb_connections = musicdb_connection_rows(matches)

    metadata_csv = output_dir / "msd_shs_track_metadata.csv"
    matches_csv = output_dir / "msd_shs_musicdb_matches.csv"
    musicdb_connections_csv = output_dir / "msd_shs_musicdb_connections.csv"
    musicdb_review_csv = output_dir / "msd_shs_musicdb_connection_review.csv"
    sqlite_path = Path(str(summary["outputs"]["sqlite"]))
    match_columns = [
        "recording_id",
        "song_id",
        "musicdb_title",
        "musicdb_artist",
        "msd_track_id",
        "msd_title",
        "msd_artist",
        "clique_id",
        "clique_title",
        "shs_performance_id",
        "shs_performance_url",
        "shs_work_ids",
        "match_confidence",
        "source",
    ]
    musicdb_connection_columns = [
        "clique_id",
        "clique_title",
        "left_recording_id",
        "right_recording_id",
        "relationship_type",
        "confidence",
        "source",
    ]
    review_columns = [
        "review_status",
        "review_notes",
        "review_flags",
        "clique_id",
        "clique_title",
        "relationship_type",
        "candidate_confidence",
        "left_recording_id",
        "left_song_id",
        "left_musicdb_title",
        "left_musicdb_artist",
        "left_msd_track_id",
        "left_msd_title",
        "left_msd_artist",
        "left_shs_performance_id",
        "left_shs_performance_url",
        "right_recording_id",
        "right_song_id",
        "right_musicdb_title",
        "right_musicdb_artist",
        "right_msd_track_id",
        "right_msd_title",
        "right_msd_artist",
        "right_shs_performance_id",
        "right_shs_performance_url",
        "shs_work_ids",
        "source",
    ]
    review_rows = musicdb_connection_review_rows(musicdb_connections, matches)

    _write_csv(metadata_csv, enriched)
    _write_csv(matches_csv, matches, match_columns)
    _write_csv(musicdb_connections_csv, musicdb_connections, musicdb_connection_columns)
    _write_csv(musicdb_review_csv, review_rows, review_columns)

    with sqlite3.connect(sqlite_path) as conn:
        _replace_table(conn, "msd_shs_track_metadata", enriched)
        _replace_table(conn, "msd_shs_musicdb_matches", matches, match_columns)
        _replace_table(conn, "msd_shs_musicdb_connections", musicdb_connections, musicdb_connection_columns)
        _replace_table(conn, "msd_shs_musicdb_connection_review", review_rows, review_columns)
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_msd_shs_track_metadata_title_artist
                ON msd_shs_track_metadata(title, artist_name);
            CREATE INDEX IF NOT EXISTS idx_msd_shs_musicdb_matches_recording
                ON msd_shs_musicdb_matches(recording_id);
            CREATE INDEX IF NOT EXISTS idx_msd_shs_musicdb_matches_track
                ON msd_shs_musicdb_matches(msd_track_id);
            CREATE INDEX IF NOT EXISTS idx_msd_shs_musicdb_connection_review_left
                ON msd_shs_musicdb_connection_review(left_recording_id);
            CREATE INDEX IF NOT EXISTS idx_msd_shs_musicdb_connection_review_right
                ON msd_shs_musicdb_connection_review(right_recording_id);
            """
        )
        conn.commit()

    summary["metadata_db"] = str(metadata_db)
    summary["metadata_enriched_count"] = len(enriched)
    summary["musicdb_match_count"] = len(matches)
    summary["musicdb_connection_count"] = len(musicdb_connections)
    summary["musicdb_connection_review_count"] = len(review_rows)
    summary["outputs"]["track_metadata_csv"] = str(metadata_csv)
    summary["outputs"]["musicdb_matches_csv"] = str(matches_csv)
    summary["outputs"]["musicdb_connections_csv"] = str(musicdb_connections_csv)
    summary["outputs"]["musicdb_connection_review_csv"] = str(musicdb_review_csv)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def build_import(
    input_dir: Path,
    output_dir: Path,
    metadata_db: Path | None = None,
    recordings_csv: Path | None = None,
) -> dict[str, object]:
    performances = parse_input_dir(input_dir)
    summary = write_outputs(performances, output_dir)
    if metadata_db is not None and recordings_csv is not None:
        summary = add_metadata_outputs(summary, performances, output_dir, metadata_db, recordings_csv)
    return summary


def run(
    *,
    write: bool,
    paths: MusicDBPaths,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    track_metadata_db: Path | None = None,
) -> dict[str, object] | None:
    input_dir = input_dir or paths.root / DEFAULT_INPUT_DIR
    output_dir = output_dir or paths.root / DEFAULT_OUTPUT_DIR
    track_metadata_db = track_metadata_db or paths.root / DEFAULT_TRACK_METADATA_DB
    if not write:
        print(f"dry-run: Would import MSD SHS files from {input_dir}")
        print(f"dry-run: Would write normalized outputs to {output_dir}")
        print(f"dry-run: Would enrich from MSD track metadata DB at {track_metadata_db} if present")
        return None

    metadata_db = track_metadata_db if track_metadata_db.exists() else None
    summary = build_import(input_dir, output_dir, metadata_db, paths.recordings_csv if metadata_db else None)
    print(f"Imported {summary['performance_count']} MSD SHS performances")
    print(f"Grouped into {summary['clique_count']} SHS/MSD cliques")
    print(f"Wrote {summary['connection_count']} pairwise clique connections")
    if metadata_db:
        print(f"Enriched {summary['metadata_enriched_count']} MSD SHS performances with track metadata")
        print(f"Matched {summary['musicdb_match_count']} rows to MusicDB recordings")
        print(f"Wrote {summary['musicdb_connection_count']} MusicDB same-clique connection candidates")
        print(f"Wrote {summary['musicdb_connection_review_count']} MusicDB connection review rows")
    else:
        print(f"Skipped metadata enrichment; missing {track_metadata_db}")
    print(f"SQLite: {summary['outputs']['sqlite']}")
    return summary

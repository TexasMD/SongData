from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.cover_scraper import scrape_covers
from src.db_access import execute_query
from src.source_checks import ensure_source_query_checks_table, export_source_query_checks_csv, record_source_query_check

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODEx_STAGE_ROOT = PROJECT_ROOT / "data" / "staging" / "codex"


@dataclass
class CoverUpdateResult:
    run_id: str
    run_dir: Path
    recordings: list[dict[str, Any]]
    covers: list[dict[str, Any]]
    source_query_checks: list[dict[str, Any]]


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_recordings(recording_ids: list[str]) -> list[dict[str, Any]]:
    placeholders = ",".join(["?"] * len(recording_ids))
    rows = execute_query(
        f"""
        SELECT recording_id, title, artist, album, version, release_year
        FROM recordings
        WHERE recording_id IN ({placeholders})
        ORDER BY artist, title
        """,
        recording_ids,
    )
    return rows.to_dict(orient="records")


def _ensure_run_dir() -> Path:
    run_dir = CODEx_STAGE_ROOT / "cover_updates" / _utc_run_id()
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _write_cover_rows(run_dir: Path, rows: list[dict[str, Any]]) -> Path:
    output = run_dir / "cover_relationship_candidates.csv"
    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "original_recording_id",
                "title",
                "artist",
                "original_title",
                "original_artist",
                "original_year",
                "musicbrainz_recording_id",
                "source",
                "musicbrainz_last_checked_at",
                "coverinfo_last_checked_at",
                "secondhandsongs_last_checked_at",
                "whosampled_last_checked_at",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return output


def _sanitize_cover_row(row: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "original_recording_id",
        "title",
        "artist",
        "original_title",
        "original_artist",
        "original_year",
        "musicbrainz_recording_id",
        "source",
        "musicbrainz_last_checked_at",
        "coverinfo_last_checked_at",
        "secondhandsongs_last_checked_at",
        "whosampled_last_checked_at",
    }
    return {key: row.get(key, "") for key in allowed}


def _write_manifest(run_dir: Path, payload: dict[str, Any]) -> Path:
    manifest = run_dir / "cover_update_manifest.json"
    manifest.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def run_cover_update(recording_ids: list[str]) -> CoverUpdateResult:
    recording_ids = [recording_id for recording_id in dict.fromkeys(recording_ids) if recording_id]
    if not recording_ids:
        raise ValueError("Select at least one recording")

    recordings = _load_recordings(recording_ids)
    if not recordings:
        raise ValueError("No recordings found")

    run_dir = _ensure_run_dir()
    source_checks_conn = sqlite3.connect(":memory:")
    ensure_source_query_checks_table(source_checks_conn)
    latest_source_checks: dict[tuple[str, str], str] = {}

    def on_source_checked(
        source: str,
        query_kind: str,
        query_url: str,
        result_count: int | None,
        checked_at: str,
        recording_id: str,
    ) -> None:
        record_source_query_check(
            source_checks_conn,
            recording_id=recording_id,
            source=source,
            query_kind=query_kind,
            last_query_url=query_url,
            last_result_count=result_count,
            checked_at=checked_at,
        )
        latest_source_checks[(recording_id, source)] = checked_at

    covers: list[dict[str, Any]] = []
    for recording in recordings:
        rec_id = str(recording.get("recording_id") or "")
        title = str(recording.get("title") or "")
        artist = str(recording.get("artist") or "")
        original_year = "" if recording.get("release_year") is None else str(recording.get("release_year"))

        def callback(
            source: str,
            query_kind: str,
            query_url: str,
            result_count: int | None,
            checked_at: str,
        ) -> None:
            on_source_checked(source, query_kind, query_url, result_count, checked_at, rec_id)

        rows = scrape_covers(title, artist, original_year, on_source_checked=callback)
        for row in rows:
            enriched = _sanitize_cover_row(row)
            enriched["original_recording_id"] = rec_id
            enriched["musicbrainz_last_checked_at"] = latest_source_checks.get((rec_id, "MusicBrainz"), "")
            enriched["coverinfo_last_checked_at"] = latest_source_checks.get((rec_id, "cover.info"), "")
            enriched["secondhandsongs_last_checked_at"] = latest_source_checks.get((rec_id, "SecondHandSongs"), "")
            enriched["whosampled_last_checked_at"] = latest_source_checks.get((rec_id, "WhoSampled"), "")
            covers.append(enriched)

    cover_csv = _write_cover_rows(run_dir, covers)
    source_checks_csv = run_dir / "source_query_checks.csv"
    export_source_query_checks_csv(source_checks_conn, source_checks_csv)

    source_checks_rows = pd.read_sql_query(
        "SELECT * FROM source_query_checks ORDER BY recording_id, source, query_kind",
        source_checks_conn,
    ).to_dict(orient="records")
    manifest = _write_manifest(
        run_dir,
        {
            "run_id": run_dir.name,
            "recording_ids": recording_ids,
            "recording_count": len(recordings),
            "candidate_count": len(covers),
            "cover_csv": str(cover_csv),
            "source_query_checks_csv": str(source_checks_csv),
        },
    )

    source_checks_conn.close()
    return CoverUpdateResult(
        run_id=run_dir.name,
        run_dir=run_dir,
        recordings=recordings,
        covers=covers,
        source_query_checks=source_checks_rows,
    )

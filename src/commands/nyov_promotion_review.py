"""nyov-promotion-review command implementation."""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

from src.commands.nyov_verification_summary import build_summary
from src.config import MusicDBPaths


REVIEW_BUCKET = "review_candidate_strong_identity"


def _fetch_supporting_attempts(conn: sqlite3.Connection, nyov_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            provider,
            provider_entity_type,
            provider_entity_id,
            provider_url,
            result_json,
            match_status,
            match_score,
            title_match_status,
            artist_match_status,
            album_match_status,
            isrc_match_status,
            queried_at
        FROM nyov_verification_attempts
        WHERE nyov_id = ?
          AND match_status IN ('matched', 'needs_review')
        ORDER BY CAST(match_score AS REAL) DESC, provider
        """,
        (nyov_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _raw_value(attempt: dict[str, Any], *keys: str) -> str:
    try:
        raw = json.loads(str(attempt.get("result_json") or "{}"))
    except json.JSONDecodeError:
        raw = {}
    for key in keys:
        value = raw.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _raw_nested_value(attempt: dict[str, Any], *keys: str) -> str:
    try:
        value: Any = json.loads(str(attempt.get("result_json") or "{}"))
    except json.JSONDecodeError:
        return ""
    for key in keys:
        if not isinstance(value, dict):
            return ""
        value = value.get(key)
    return "" if value in (None, "") else str(value)


def _provider_id_field(provider: str) -> str:
    if provider == "Spotify":
        return "spotify_track_id"
    if provider == "MusicBrainz":
        return "musicbrainz_recording_id"
    if provider == "iTunes":
        return "itunes_track_id"
    return f"{provider.lower()}_entity_id"


def _supporting_sources(attempts: list[dict[str, Any]], *, field_status: str | None = None) -> str:
    providers = []
    for attempt in attempts:
        if field_status and attempt.get(field_status) not in {"exact", "partial", "present"}:
            continue
        provider = str(attempt.get("provider") or "")
        entity_id = str(attempt.get("provider_entity_id") or "")
        if provider and entity_id:
            providers.append(f"{provider}:{entity_id}")
    return " | ".join(dict.fromkeys(providers))


def _conflicting_sources(attempts: list[dict[str, Any]], *, field_status: str) -> str:
    providers = []
    for attempt in attempts:
        if attempt.get(field_status) != "different":
            continue
        provider = str(attempt.get("provider") or "")
        entity_id = str(attempt.get("provider_entity_id") or "")
        if provider and entity_id:
            providers.append(f"{provider}:{entity_id}")
    return " | ".join(dict.fromkeys(providers))


def _review_row(
    entity: dict[str, Any],
    *,
    target_field: str,
    proposed_value: str,
    verification_level: str,
    supporting_sources: str,
    conflicting_sources: str = "",
    notes: str = "",
) -> dict[str, str]:
    return {
        "nyov_id": str(entity["nyov_id"]),
        "seed_title": str(entity["seed_title"]),
        "seed_artist": str(entity["seed_artist"]),
        "seed_album": str(entity["seed_album"]),
        "review_bucket": str(entity["review_bucket"]),
        "target_table": "recordings",
        "target_key": str(entity["nyov_id"]),
        "target_field": target_field,
        "proposed_value": proposed_value,
        "verification_level": verification_level,
        "supporting_sources": supporting_sources,
        "conflicting_sources": conflicting_sources,
        "best_provider": str(entity.get("best_provider") or ""),
        "best_provider_entity_id": str(entity.get("best_provider_entity_id") or ""),
        "best_match_score": str(entity.get("best_match_score") or ""),
        "review_decision": "",
        "review_notes": notes,
    }


def _is_identity_matched(attempt: dict[str, Any]) -> bool:
    return (
        attempt.get("match_status") == "matched"
        and attempt.get("title_match_status") in {"exact", "partial"}
        and attempt.get("artist_match_status") in {"exact", "partial"}
    )


def _dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (row["nyov_id"], row["target_field"], row["proposed_value"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def build_promotion_review(db_path: Path) -> list[dict[str, str]]:
    summary = build_summary(db_path)
    strong_entities = [row for row in summary["entity_summary"] if row["review_bucket"] == REVIEW_BUCKET]
    review_rows: list[dict[str, str]] = []

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        for entity in strong_entities:
            attempts = _fetch_supporting_attempts(conn, str(entity["nyov_id"]))
            title_sources = _supporting_sources(attempts, field_status="title_match_status")
            artist_sources = _supporting_sources(attempts, field_status="artist_match_status")
            album_sources = _supporting_sources(attempts, field_status="album_match_status")
            review_rows.append(
                _review_row(
                    entity,
                    target_field="title",
                    proposed_value=str(entity["seed_title"]),
                    verification_level="verified_strong",
                    supporting_sources=title_sources,
                    conflicting_sources=_conflicting_sources(attempts, field_status="title_match_status"),
                )
            )
            review_rows.append(
                _review_row(
                    entity,
                    target_field="artist",
                    proposed_value=str(entity["seed_artist"]),
                    verification_level="verified_strong",
                    supporting_sources=artist_sources,
                    conflicting_sources=_conflicting_sources(attempts, field_status="artist_match_status"),
                )
            )
            if int(entity.get("album_conflicts") or 0) == 0 and str(entity.get("seed_album") or ""):
                review_rows.append(
                    _review_row(
                        entity,
                        target_field="album",
                        proposed_value=str(entity["seed_album"]),
                        verification_level="verified_supported",
                        supporting_sources=album_sources,
                        conflicting_sources=_conflicting_sources(attempts, field_status="album_match_status"),
                    )
                )
            provider_id_seen: set[str] = set()
            for attempt in attempts:
                if not _is_identity_matched(attempt):
                    continue
                provider = str(attempt.get("provider") or "")
                if provider in provider_id_seen:
                    continue
                entity_id = str(attempt.get("provider_entity_id") or "")
                if entity_id:
                    provider_id_seen.add(provider)
                    review_rows.append(
                        _review_row(
                            entity,
                            target_field=_provider_id_field(provider),
                            proposed_value=entity_id,
                            verification_level="verified_supported",
                            supporting_sources=f"{provider}:{entity_id}",
                            notes=str(attempt.get("provider_url") or ""),
                        )
                    )
                isrc = _raw_value(attempt, "isrc")
                if not isrc and provider == "Spotify":
                    isrc = _raw_nested_value(attempt, "external_ids", "isrc")
                if isrc:
                    review_rows.append(
                        _review_row(
                            entity,
                            target_field="isrc",
                            proposed_value=isrc,
                            verification_level="verified_supported",
                            supporting_sources=f"{provider}:{entity_id}",
                        )
                    )
    return _dedupe_rows(review_rows)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else [
        "nyov_id",
        "seed_title",
        "seed_artist",
        "seed_album",
        "review_bucket",
        "target_table",
        "target_key",
        "target_field",
        "proposed_value",
        "verification_level",
        "supporting_sources",
        "conflicting_sources",
        "best_provider",
        "best_provider_entity_id",
        "best_match_score",
        "review_decision",
        "review_notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run(
    *,
    write: bool,
    paths: MusicDBPaths,
    db_path: Path | None = None,
    output_dir: Path | None = None,
) -> int:
    db_path = (db_path or paths.nyov_db_path).resolve()
    output_dir = (output_dir or paths.exports_dir / "codex" / "nyov_promotion_review").resolve()
    rows = build_promotion_review(db_path)
    output_path = output_dir / "promotion_review_candidates.csv"

    print("nyov-promotion-review: dry-run=" + str(not write))
    print(f"Input DB: {db_path}")
    print(f"Review rows: {len(rows)}")
    if write:
        _write_csv(output_path, rows)
        print(f"Wrote promotion review candidates to {output_path}")
    else:
        print(f"DRY RUN: Would write promotion review candidates to {output_path}")
    return 0

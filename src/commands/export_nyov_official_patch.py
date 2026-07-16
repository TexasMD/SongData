"""export-nyov-official-patch command implementation."""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

from src.config import MusicDBPaths
from src.normalization import normalize_search_text


FIELD_TO_OFFICIAL_COLUMNS = {
    "title": ["Title"],
    "artist": ["Artist"],
    "album": ["Album"],
    "spotify_track_id": ["Spotify Track ID", "Spotify ID"],
    "musicbrainz_recording_id": ["MusicBrainz Recording ID", "MusicBrainz ID", "Spotify MusicBrainz ID"],
    "itunes_track_id": ["iTunes Track ID"],
    "isrc": ["Spotify ISRC", "ISRC"],
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _fetch_promotions(db_path: Path) -> list[dict[str, Any]]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                p.promotion_id,
                p.nyov_id,
                e.seed_title,
                e.seed_artist,
                e.seed_album,
                p.target_table,
                p.target_key,
                p.target_field,
                p.promoted_value,
                p.verification_level,
                p.evidence_json,
                p.promoted_at,
                p.promoted_by,
                p.notes
            FROM nyov_promotions p
            LEFT JOIN nyov_entities e ON e.nyov_id = p.nyov_id
            ORDER BY e.seed_artist, e.seed_title, p.target_field
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _find_official_match(promotion: dict[str, Any], rows: list[dict[str, str]]) -> tuple[str, dict[str, str] | None]:
    title_key = normalize_search_text(promotion.get("seed_title", ""))
    artist_key = normalize_search_text(promotion.get("seed_artist", ""))
    title_matches = [
        row for row in rows
        if normalize_search_text(row.get("Title", "")) == title_key
    ]
    exact = [
        row for row in title_matches
        if normalize_search_text(row.get("Artist", "")) == artist_key
    ]
    if len(exact) == 1:
        return "matched_exact_title_artist", exact[0]
    if len(exact) > 1:
        return "ambiguous_multiple_title_artist_matches", exact[0]
    if len(title_matches) == 1:
        return "matched_title_only", title_matches[0]
    if len(title_matches) > 1:
        return "ambiguous_multiple_title_matches", title_matches[0]
    return "not_found", None


def _target_column(target_field: str, official_row: dict[str, str] | None) -> str:
    candidates = FIELD_TO_OFFICIAL_COLUMNS.get(target_field, [target_field])
    if official_row:
        for candidate in candidates:
            if candidate in official_row:
                return candidate
    return candidates[0]


def _current_value(target_column: str, official_row: dict[str, str] | None) -> str:
    if not official_row:
        return ""
    return str(official_row.get(target_column, "") or "")


def _evidence_field(evidence_json: str, field: str) -> str:
    try:
        evidence = json.loads(evidence_json or "{}")
    except json.JSONDecodeError:
        return ""
    return str(evidence.get(field, "") or "")


def build_official_patch(db_path: Path, official_csv: Path) -> list[dict[str, str]]:
    if not db_path.exists():
        raise FileNotFoundError(f"NYOV database not found: {db_path}")
    official_rows = _read_csv(official_csv)
    promotions = _fetch_promotions(db_path)
    patch_rows: list[dict[str, str]] = []
    for promotion in promotions:
        match_status, official_row = _find_official_match(promotion, official_rows)
        target_field = str(promotion.get("target_field") or "")
        target_column = _target_column(target_field, official_row)
        current_value = _current_value(target_column, official_row)
        promoted_value = str(promotion.get("promoted_value") or "")
        action = "no_change" if current_value == promoted_value and current_value else "update_existing"
        if not official_row:
            action = "manual_match_required"
        elif match_status.startswith("ambiguous"):
            action = "manual_match_required"
        patch_rows.append(
            {
                "promotion_id": str(promotion.get("promotion_id") or ""),
                "nyov_id": str(promotion.get("nyov_id") or ""),
                "seed_title": str(promotion.get("seed_title") or ""),
                "seed_artist": str(promotion.get("seed_artist") or ""),
                "seed_album": str(promotion.get("seed_album") or ""),
                "official_csv": str(official_csv),
                "official_match_status": match_status,
                "target_field": target_field,
                "target_column": target_column,
                "current_value": current_value,
                "promoted_value": promoted_value,
                "patch_action": action,
                "verification_level": str(promotion.get("verification_level") or ""),
                "supporting_sources": _evidence_field(str(promotion.get("evidence_json") or ""), "supporting_sources"),
                "conflicting_sources": _evidence_field(str(promotion.get("evidence_json") or ""), "conflicting_sources"),
                "promoted_at": str(promotion.get("promoted_at") or ""),
                "promoted_by": str(promotion.get("promoted_by") or ""),
                "notes": str(promotion.get("notes") or ""),
            }
        )
    return patch_rows


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else [
        "promotion_id",
        "nyov_id",
        "seed_title",
        "seed_artist",
        "seed_album",
        "official_csv",
        "official_match_status",
        "target_field",
        "target_column",
        "current_value",
        "promoted_value",
        "patch_action",
        "verification_level",
        "supporting_sources",
        "conflicting_sources",
        "promoted_at",
        "promoted_by",
        "notes",
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
    official_csv: Path | None = None,
    output_dir: Path | None = None,
) -> int:
    db_path = (db_path or paths.nyov_db_path).resolve()
    official_csv = (official_csv or paths.recordings_csv).resolve()
    output_dir = (output_dir or paths.exports_dir / "codex" / "nyov_official_patch").resolve()
    rows = build_official_patch(db_path, official_csv)
    output_path = output_dir / "official_patch_candidates.csv"
    print("export-nyov-official-patch: dry-run=" + str(not write))
    print(f"Input DB: {db_path}")
    print(f"Official CSV: {official_csv}")
    print(f"Patch rows: {len(rows)}")
    if write:
        _write_csv(output_path, rows)
        print(f"Wrote official patch candidates to {output_path}")
    else:
        print(f"DRY RUN: Would write official patch candidates to {output_path}")
    return 0

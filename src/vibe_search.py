from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from src.normalization import normalize_search_text


TEXT_COLUMNS = [
    "title",
    "artist",
    "album",
    "genre",
    "genre_detail",
    "mood_tags",
    "event_tags",
    "situation_tags",
    "setlist_role",
    "crowd_energy",
    "playlists",
    "data_quality_notes",
]

SEARCH_INDEX_COLUMNS = {"title", "artist", "album"}


def _terms(query: str) -> list[str]:
    query = normalize_search_text(query)
    return [
        term.lower()
        for term in re.findall(r"[^\W_]+(?:'[^\W_]+)*", query, flags=re.UNICODE)
        if len(term) > 1
    ][:8]


def _recordings_have_search_columns(db_path: str | Path) -> bool:
    try:
        with sqlite3.connect(db_path) as conn:
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(recordings)").fetchall()
            }
    except sqlite3.Error:
        return False

    return {"title_search", "artist_search", "album_search"}.issubset(columns)


def build_vibe_query(
    vibe_query: str,
    limit: int = 100,
    *,
    use_search_columns: bool = False,
) -> tuple[str, list[Any]]:
    """
    Build a deterministic, read-only SQLite query for conversational search.

    This deliberately maps plain English to LIKE predicates over known local
    fields instead of asking an LLM to invent criteria. Richer LLM planning can
    be layered on later as a reviewed suggestion source.
    """
    terms = _terms(vibe_query)
    columns = ", ".join([
        "recording_id",
        "title",
        "artist",
        "album",
        "release_year",
        "duration",
        "genre",
        "genre_detail",
        "bpm",
        "key",
        "mood_tags",
        "event_tags",
        "situation_tags",
        "playlists",
        "spotify_track_id",
        "musicbrainz_recording_id",
    ])

    if not terms:
        return (
            f"SELECT {columns} FROM recordings ORDER BY artist, title LIMIT ?",
            [limit],
        )

    predicates: list[str] = []
    params: list[Any] = []
    for term in terms:
        per_term = [
            (
                f"LOWER(COALESCE({column}_search, '')) LIKE ?"
                if use_search_columns and column in SEARCH_INDEX_COLUMNS
                else f"NORMALIZE_SEARCH_TEXT(COALESCE({column}, '')) LIKE ?"
            )
            for column in TEXT_COLUMNS
        ]
        predicates.append("(" + " OR ".join(per_term) + ")")
        params.extend([f"%{term}%"] * len(TEXT_COLUMNS))

    sql = (
        f"SELECT {columns} FROM recordings "
        f"WHERE {' AND '.join(predicates)} "
        "ORDER BY artist, title LIMIT ?"
    )
    params.append(limit)
    return sql, params


def search_by_vibe(
    vibe_query: str,
    limit: int = 100,
    *,
    db_path: str | Path | None = None,
) -> tuple[str, list[Any]]:
    use_search_columns = bool(db_path) and _recordings_have_search_columns(db_path)
    return build_vibe_query(vibe_query, limit=limit, use_search_columns=use_search_columns)

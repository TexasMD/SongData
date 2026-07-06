from __future__ import annotations

import re
from typing import Any


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


def _terms(query: str) -> list[str]:
    return [
        term.lower()
        for term in re.findall(r"[A-Za-z0-9']+", query)
        if len(term) > 1
    ][:8]


def build_vibe_query(vibe_query: str, limit: int = 100) -> tuple[str, list[Any]]:
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
        per_term = [f"LOWER(COALESCE({column}, '')) LIKE ?" for column in TEXT_COLUMNS]
        predicates.append("(" + " OR ".join(per_term) + ")")
        params.extend([f"%{term}%"] * len(TEXT_COLUMNS))

    sql = (
        f"SELECT {columns} FROM recordings "
        f"WHERE {' AND '.join(predicates)} "
        "ORDER BY artist, title LIMIT ?"
    )
    params.append(limit)
    return sql, params


def search_by_vibe(vibe_query: str, limit: int = 100) -> tuple[str, list[Any]]:
    return build_vibe_query(vibe_query, limit=limit)

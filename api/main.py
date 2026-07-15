from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.db_access import DEFAULT_DB_PATH, execute_query
from src.cover_update_service import run_cover_update
from src.config import paths as musicdb_paths
from src.normalization import normalize_display_row
from src.similarity_engine import find_similar_recordings
from src.vibe_search import search_by_vibe

app = FastAPI(
    title="MusicDB API",
    description="Read-only SQLite API for the MusicDB Pro Console.",
)

MUSICDB_PATHS = musicdb_paths()
DEFAULT_REFERENCE_DB_PATH = MUSICDB_PATHS.reference_db_path

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class VibeRequest(BaseModel):
    query: str


class SqlRequest(BaseModel):
    query: str


class CommonalitiesRequest(BaseModel):
    recording_ids: list[str]


class CoverRequest(BaseModel):
    recording_id: str


class CoverUpdateRequest(BaseModel):
    recording_ids: list[str]


def records_from_query(
    query: str,
    params: list[Any] | tuple[Any, ...] | None = None,
    *,
    db_path=DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    df = execute_query(query, params=params, db_path=db_path)
    rows = json.loads(df.to_json(orient="records"))
    return [normalize_display_row(row) for row in rows]


def sanitize_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_display_row(record) for record in records]


def _reference_db_ready() -> None:
    if not DEFAULT_REFERENCE_DB_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Reference database not found at {DEFAULT_REFERENCE_DB_PATH}. Build it first.",
        )


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok", "database": str(DEFAULT_DB_PATH)}


@app.get("/api/recordings")
def get_recordings(
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict[str, list[dict[str, Any]]]:
    query = """
        SELECT
            recording_id,
            title,
            artist,
            album,
            version,
            release_year,
            duration,
            genre,
            genre_detail,
            bpm,
            key,
            mood_tags,
            event_tags,
            situation_tags,
            playlists,
            crowd_energy,
            spotify_track_id,
            musicbrainz_recording_id
        FROM recordings
        ORDER BY artist, title
        LIMIT ? OFFSET ?
    """
    try:
        return {"results": records_from_query(query, [limit, offset])}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/reference/sources")
def get_reference_sources(
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict[str, list[dict[str, Any]]]:
    _reference_db_ready()
    query = """
        SELECT source, kind, credential_required, credential_environment_variables, used_by, status, notes
        FROM source_registry
        ORDER BY source
        LIMIT ? OFFSET ?
    """
    try:
        return {"results": records_from_query(query, [limit, offset], db_path=DEFAULT_REFERENCE_DB_PATH)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/reference/matrix")
def get_reference_matrix(
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict[str, list[dict[str, Any]]]:
    _reference_db_ready()
    query = """
        SELECT source, primary_metadata, identifier_fields, best_match_keys, default_confidence, notes
        FROM source_metadata_matrix
        ORDER BY source
        LIMIT ? OFFSET ?
    """
    try:
        return {"results": records_from_query(query, [limit, offset], db_path=DEFAULT_REFERENCE_DB_PATH)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/reference/entities")
def get_reference_entities(
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict[str, list[dict[str, Any]]]:
    _reference_db_ready()
    query = """
        SELECT *
        FROM reference_entities
        ORDER BY entity_kind, display_name
        LIMIT ? OFFSET ?
    """
    try:
        return {"results": records_from_query(query, [limit, offset], db_path=DEFAULT_REFERENCE_DB_PATH)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/reference/identifiers")
def get_reference_identifiers(
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict[str, list[dict[str, Any]]]:
    _reference_db_ready()
    query = """
        SELECT entity_kind, entity_id, entity_label, source, field_name, field_value, value_kind, source_url, verified_status, notes
        FROM reference_identifiers
        ORDER BY source, entity_kind, entity_id, field_name
        LIMIT ? OFFSET ?
    """
    try:
        return {"results": records_from_query(query, [limit, offset], db_path=DEFAULT_REFERENCE_DB_PATH)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/reference/source-observations")
def get_reference_source_observations(
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict[str, list[dict[str, Any]]]:
    _reference_db_ready()
    query = """
        SELECT row_number, source_name, title, artist, album, field_name, field_value, value_kind, notes
        FROM source_observations
        ORDER BY source_name, row_number, field_name
        LIMIT ? OFFSET ?
    """
    try:
        return {"results": records_from_query(query, [limit, offset], db_path=DEFAULT_REFERENCE_DB_PATH)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/vibe_search")
def api_vibe_search(request: VibeRequest) -> dict[str, Any]:
    try:
        sql, params = search_by_vibe(request.query, db_path=DEFAULT_DB_PATH)
        return {"sql": sql, "results": records_from_query(sql, params)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/sql")
def api_execute_sql(request: SqlRequest) -> dict[str, list[dict[str, Any]]]:
    try:
        return {"results": records_from_query(request.query)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/similarity/{recording_id}")
def api_similarity(
    recording_id: str,
    limit: int = Query(30, ge=1, le=100),
) -> dict[str, list[dict[str, Any]]]:
    try:
        results = find_similar_recordings(recording_id, str(DEFAULT_DB_PATH), limit=limit)
        return {"results": sanitize_records(results)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/covers")
def api_covers(request: CoverRequest) -> dict[str, list[dict[str, Any]]]:
    try:
        target_rows = records_from_query(
            "SELECT title, artist FROM recordings WHERE recording_id = ?",
            [request.recording_id],
        )
        if not target_rows:
            raise HTTPException(status_code=404, detail="Recording not found")

        target = target_rows[0]
        title = target.get("title")
        artist = target.get("artist")
        if not title:
            return {"covers": []}

        covers = records_from_query(
            """
            SELECT
                recording_id,
                title,
                artist,
                album,
                version,
                release_year,
                genre,
                bpm,
                key,
                mood_tags,
                playlists
            FROM recordings
            WHERE NORMALIZE_SEARCH_TEXT(title) = NORMALIZE_SEARCH_TEXT(?)
              AND NORMALIZE_SEARCH_TEXT(COALESCE(artist, '')) != NORMALIZE_SEARCH_TEXT(COALESCE(?, ''))
            ORDER BY artist, album
            LIMIT 100
            """,
            [title, artist],
        )
        return {"covers": sanitize_records(covers)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/cover_updates")
def api_cover_updates(request: CoverUpdateRequest) -> dict[str, Any]:
    try:
        result = run_cover_update(request.recording_ids)
        return {
            "run_id": result.run_id,
            "stage_dir": str(result.run_dir),
            "recordings": result.recordings,
            "covers": result.covers,
            "source_query_checks": result.source_query_checks,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/commonalities")
def api_commonalities(request: CommonalitiesRequest) -> dict[str, Any]:
    if len(request.recording_ids) < 2:
        raise HTTPException(status_code=400, detail="Select at least two recordings")

    placeholders = ",".join(["?"] * len(request.recording_ids))
    rows = records_from_query(
        f"""
        SELECT recording_id, title, artist, genre, bpm, key, mood_tags, event_tags, playlists
        FROM recordings
        WHERE recording_id IN ({placeholders})
        """,
        request.recording_ids,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No recordings found")

    shared: dict[str, Any] = {}
    for field in ["artist", "genre", "key"]:
        values = {row.get(field) for row in rows if row.get(field)}
        if len(values) == 1:
            shared[field] = next(iter(values))

    bpms = [row.get("bpm") for row in rows if isinstance(row.get("bpm"), (int, float))]
    if bpms:
        shared["bpm_range"] = [min(bpms), max(bpms)]

    return {"count": len(rows), "commonalities": shared, "records": sanitize_records(rows)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)

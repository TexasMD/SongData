from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.db_access import DEFAULT_DB_PATH, execute_query
from src.cover_update_service import run_cover_update
from src.similarity_engine import find_similar_recordings
from src.vibe_search import search_by_vibe

app = FastAPI(
    title="MusicDB API",
    description="Read-only SQLite API for the MusicDB Pro Console.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"],
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


def records_from_query(query: str, params: list[Any] | tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    df = execute_query(query, params=params)
    return json.loads(df.to_json(orient="records"))


@app.get("/api/health")
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


@app.post("/api/vibe_search")
def api_vibe_search(request: VibeRequest) -> dict[str, Any]:
    try:
        sql, params = search_by_vibe(request.query)
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
        return {"results": results}
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
            WHERE LOWER(title) = LOWER(?)
              AND COALESCE(artist, '') != COALESCE(?, '')
            ORDER BY artist, album
            LIMIT 100
            """,
            [title, artist],
        )
        return {"covers": covers}
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

    return {"count": len(rows), "commonalities": shared, "records": rows}


# --- Static Files Serving ---
# Resolve frontend build path correctly for both dev and PyInstaller environments
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Running in PyInstaller bundle
    frontend_dist_path = Path(sys._MEIPASS) / "frontend" / "dist"
else:
    # Running locally
    frontend_dist_path = root_dir / "frontend" / "dist"

if frontend_dist_path.exists() and frontend_dist_path.is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_dist_path / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        file_path = frontend_dist_path / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        # Fallback to index.html for SPA routing
        return FileResponse(frontend_dist_path / "index.html")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)

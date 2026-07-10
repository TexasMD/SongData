from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from typing import Any, Callable

import requests

logger = logging.getLogger(__name__)

SourceCheckCallback = Callable[[str, str, str, int | None, str], None]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit_checked(
    callback: SourceCheckCallback | None,
    *,
    source: str,
    query_kind: str,
    query_url: str,
    result_count: int | None,
) -> None:
    if callback is None:
        return
    callback(source, query_kind, query_url, result_count, _utc_now_iso())


def _normalize(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _artist_name(song: dict[str, Any]) -> str:
    artists = song.get("artists") or []
    names: list[str] = []
    for artist_entry in artists:
        artist = artist_entry.get("artist") or {}
        artist_names = artist.get("names") or []
        if artist_names:
            name = artist_names[0].get("name")
            if name:
                names.append(str(name))
    return " and ".join(names)


def _candidate_matches(candidate: dict[str, Any], title: str, artist: str) -> bool:
    candidate_title = _normalize(candidate.get("title"))
    if candidate_title != _normalize(title):
        return False
    if not artist:
        return True
    artist_norm = _normalize(artist)
    candidate_artist = _normalize(_artist_name(candidate))
    return artist_norm == candidate_artist


class CoverInfoClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})

    def search_song(
        self,
        title: str,
        artist: str,
        *,
        callback: SourceCheckCallback | None = None,
        recording_id: str = "",
    ) -> dict[str, Any] | None:
        url = "https://cover.info/api/song/find"
        params = {"input": f"{title} {artist}".strip(), "exact": True}
        resp = self.session.get(url, params=params, timeout=20)
        results: list[dict[str, Any]] = []
        if resp.status_code == 200:
            try:
                payload = resp.json()
                if isinstance(payload, list):
                    results = [item for item in payload if isinstance(item, dict)]
            except ValueError:
                results = []
        _emit_checked(
            callback,
            source="cover.info",
            query_kind="song_find",
            query_url=resp.url if resp is not None else url,
            result_count=len(results),
        )
        if not results:
            return None

        for candidate in results:
            if _candidate_matches(candidate, title, artist):
                return candidate
        return results[0]

    def get_detailed(
        self,
        song_id: str,
        *,
        callback: SourceCheckCallback | None = None,
        recording_id: str = "",
    ) -> dict[str, Any] | None:
        url = "https://cover.info/api/song/get-detailed"
        resp = self.session.post(url, json={"id": song_id}, timeout=20)
        data: dict[str, Any] | None = None
        if resp.status_code == 200:
            try:
                payload = resp.json()
                if isinstance(payload, dict):
                    data = payload
            except ValueError:
                data = None

        result_count = 0
        if data:
            result_count = len(data.get("covers") or []) + len(data.get("originals") or [])

        _emit_checked(
            callback,
            source="cover.info",
            query_kind="song_get_detailed",
            query_url=resp.url if resp is not None else url,
            result_count=result_count,
        )
        return data

    def extract_covers(
        self,
        title: str,
        artist: str,
        *,
        original_year: str = "",
        callback: SourceCheckCallback | None = None,
        recording_id: str = "",
    ) -> list[dict[str, Any]]:
        candidate = self.search_song(title, artist, callback=callback, recording_id=recording_id)
        if not candidate:
            return []

        detailed = self.get_detailed(candidate.get("_id", ""), callback=callback, recording_id=recording_id)
        if not detailed:
            return []

        source_title = str(detailed.get("title") or title).strip()
        source_artist = _artist_name(detailed) or artist
        source_year = str(detailed.get("release_date") or original_year or "").strip()

        rows: list[dict[str, Any]] = []
        for relation in detailed.get("covers") or []:
            song = relation.get("song") or {}
            rows.append(
                {
                    "title": str(song.get("title") or "").strip(),
                    "artist": _artist_name(song),
                    "musicbrainz_recording_id": None,
                    "cover_song": "Yes",
                    "original_title": source_title,
                    "original_artist": source_artist,
                    "original_year": source_year,
                    "source": "cover.info",
                }
            )

        for relation in detailed.get("originals") or []:
            song = relation.get("song") or {}
            rows.append(
                {
                    "title": source_title,
                    "artist": source_artist,
                    "musicbrainz_recording_id": None,
                    "cover_song": "Yes",
                    "original_title": str(song.get("title") or "").strip(),
                    "original_artist": _artist_name(song),
                    "original_year": str(song.get("release_date") or "").strip() or source_year,
                    "source": "cover.info",
                }
            )

        return rows


client = CoverInfoClient()


def scrape_cover_info(
    title: str,
    artist: str,
    original_year: str = "",
    *,
    callback: SourceCheckCallback | None = None,
    recording_id: str = "",
) -> list[dict[str, Any]]:
    return client.extract_covers(
        title,
        artist,
        original_year=original_year,
        callback=callback,
        recording_id=recording_id,
    )

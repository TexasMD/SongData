from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
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


def _normalize_artist(text: str | None) -> str:
    normalized = _normalize(text)
    return normalized[3:] if normalized.startswith("the") and len(normalized) > 3 else normalized


class SecondHandSongsClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.session = requests.Session()
        self.base_url = "https://api.secondhandsongs.com"
        self.session.headers.update({"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
        api_key = api_key or os.environ.get("SECONDHANDSONGS_API_KEY", "")
        if api_key:
            self.session.headers.update({"X-API-Key": api_key})

    def _search_page(
        self,
        title: str,
        *,
        performer: str = "",
        page: int = 0,
        page_size: int = 100,
        callback: SourceCheckCallback | None = None,
        recording_id: str = "",
    ) -> dict[str, Any]:
        params = {"title": title, "page": page, "pageSize": page_size}
        if performer:
            params["performer"] = performer
        resp = self.session.get(f"{self.base_url}/search/performance", params=params, timeout=30)
        payload: dict[str, Any] = {}
        if resp.status_code == 200:
            try:
                data = resp.json()
                if isinstance(data, dict):
                    payload = data
            except ValueError:
                payload = {}
        results = payload.get("resultPage") or []
        _emit_checked(
            callback,
            source="SecondHandSongs",
            query_kind="search_performance",
            query_url=resp.url if resp is not None else f"{self.base_url}/search/performance",
            result_count=len(results),
        )
        return payload

    def search_performances(
        self,
        title: str,
        *,
        performer: str = "",
        callback: SourceCheckCallback | None = None,
        recording_id: str = "",
        page_size: int = 100,
        max_pages: int = 20,
    ) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        for page in range(max_pages):
            payload = self._search_page(
                title,
                performer=performer,
                page=page,
                page_size=page_size,
                callback=callback,
                recording_id=recording_id,
            )
            results = payload.get("resultPage") or []
            if not results:
                break
            collected.extend([item for item in results if isinstance(item, dict)])
            total_results = int(payload.get("totalResults") or 0)
            skipped_results = int(payload.get("skippedResults") or page * page_size)
            if total_results and skipped_results + len(results) >= total_results:
                break
            if len(results) < page_size:
                break
        return collected

    def extract_covers(
        self,
        title: str,
        artist: str,
        *,
        original_year: str = "",
        callback: SourceCheckCallback | None = None,
        recording_id: str = "",
    ) -> list[dict[str, Any]]:
        title_norm = _normalize(title)
        artist_norm = _normalize_artist(artist)

        exact_results = self.search_performances(
            title,
            performer=artist,
            callback=callback,
            recording_id=recording_id,
            page_size=25,
            max_pages=1,
        )
        all_results = self.search_performances(
            title,
            callback=callback,
            recording_id=recording_id,
            page_size=100,
        )

        exact_matches = [
            item
            for item in all_results
            if _normalize(item.get("title")) == title_norm
        ]
        if not exact_matches:
            exact_matches = exact_results

        target = None
        for item in exact_matches:
            performer_name = _normalize_artist((item.get("performer") or {}).get("name"))
            if _normalize(item.get("title")) == title_norm and performer_name == artist_norm:
                target = item
                break
        if target is None and exact_results:
            target = exact_results[0]
        if target is None and exact_matches:
            target = exact_matches[0]
        if target is None:
            return []

        source_is_original = bool(target.get("isOriginal"))
        source_title = str(target.get("title") or title).strip()
        source_artist = str((target.get("performer") or {}).get("name") or artist).strip()

        rows: list[dict[str, Any]] = []
        for item in exact_matches:
            performer_name = str((item.get("performer") or {}).get("name") or "").strip()
            item_title = str(item.get("title") or "").strip()
            if not item_title:
                continue
            if item.get("uri") == target.get("uri"):
                continue

            if source_is_original:
                rows.append(
                    {
                        "title": item_title,
                        "artist": performer_name,
                        "musicbrainz_recording_id": None,
                        "cover_song": "Yes",
                        "original_title": source_title,
                        "original_artist": source_artist,
                        "original_year": original_year,
                        "source": "SecondHandSongs",
                    }
                )
            else:
                if performer_name and performer_name == source_artist:
                    continue
                rows.append(
                    {
                        "title": source_title,
                        "artist": source_artist,
                        "musicbrainz_recording_id": None,
                        "cover_song": "Yes",
                        "original_title": item_title,
                        "original_artist": performer_name,
                        "original_year": original_year,
                        "source": "SecondHandSongs",
                    }
                )

        return rows


client = SecondHandSongsClient()


def scrape_secondhandsongs(
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

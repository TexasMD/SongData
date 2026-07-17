from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
import re
from urllib.parse import urlparse
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

    def _get_json(
        self,
        path_or_url: str,
        *,
        callback: SourceCheckCallback | None = None,
        query_kind: str,
    ) -> dict[str, Any]:
        url = path_or_url if path_or_url.startswith("http") else f"{self.base_url}{path_or_url}"
        resp = self.session.get(url, timeout=30)
        payload: dict[str, Any] = {}
        if resp.status_code == 200:
            try:
                data = resp.json()
                if isinstance(data, dict):
                    payload = data
            except ValueError:
                payload = {}
        result_count = 0
        if payload:
            result_count = sum(
                len(payload.get(key) or [])
                for key in ("covers", "originals", "derivedWorks", "sampledBy", "usesSamplesFrom")
            )
        _emit_checked(
            callback,
            source="SecondHandSongs",
            query_kind=query_kind,
            query_url=resp.url if resp is not None else url,
            result_count=result_count,
        )
        return payload

    @staticmethod
    def _api_path(uri: str | None) -> str:
        if not uri:
            return ""
        parsed = urlparse(uri)
        return parsed.path if parsed.scheme else uri

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

    def search_works(
        self,
        title: str,
        *,
        callback: SourceCheckCallback | None = None,
        page_size: int = 100,
        max_pages: int = 20,
    ) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        for page in range(max_pages):
            params = {"title": title, "page": page, "pageSize": page_size}
            resp = self.session.get(f"{self.base_url}/search/work", params=params, timeout=30)
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
                query_kind="search_work",
                query_url=resp.url if resp is not None else f"{self.base_url}/search/work",
                result_count=len(results),
            )
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

    def get_performance(
        self,
        uri_or_id: str,
        *,
        callback: SourceCheckCallback | None = None,
    ) -> dict[str, Any]:
        path = uri_or_id if uri_or_id.startswith("/performance/") else self._api_path(uri_or_id)
        if not path.startswith("/performance/"):
            path = f"/performance/{uri_or_id}"
        return self._get_json(path, callback=callback, query_kind="performance_detail")

    def get_work(
        self,
        uri_or_id: str,
        *,
        callback: SourceCheckCallback | None = None,
    ) -> dict[str, Any]:
        path = uri_or_id if uri_or_id.startswith("/work/") else self._api_path(uri_or_id)
        if not path.startswith("/work/"):
            path = f"/work/{uri_or_id}"
        return self._get_json(path, callback=callback, query_kind="work_detail")

    @staticmethod
    def _performer_name(item: dict[str, Any]) -> str:
        return str((item.get("performer") or {}).get("name") or "").strip()

    def _rows_from_performance_detail(
        self,
        detail: dict[str, Any],
        *,
        fallback_title: str,
        fallback_artist: str,
        original_year: str,
    ) -> list[dict[str, Any]]:
        source_title = str(detail.get("title") or fallback_title).strip()
        source_artist = self._performer_name(detail) or fallback_artist
        rows: list[dict[str, Any]] = []

        if detail.get("isOriginal"):
            for cover in detail.get("covers") or []:
                rows.append(
                    {
                        "title": str(cover.get("title") or "").strip(),
                        "artist": self._performer_name(cover),
                        "musicbrainz_recording_id": None,
                        "cover_song": "Yes",
                        "original_title": source_title,
                        "original_artist": source_artist,
                        "original_year": original_year,
                        "source": "SecondHandSongs",
                    }
                )
            return [row for row in rows if row["title"]]

        for original in detail.get("originals") or []:
            original_perf = original.get("original") or {}
            original_title = str(original_perf.get("title") or original.get("title") or "").strip()
            original_artist = self._performer_name(original_perf)
            rows.append(
                {
                    "title": source_title,
                    "artist": source_artist,
                    "musicbrainz_recording_id": None,
                    "cover_song": "Yes",
                    "original_title": original_title,
                    "original_artist": original_artist,
                    "original_year": original_year,
                    "source": "SecondHandSongs",
                }
            )
        return [row for row in rows if row["title"] and row["original_title"]]

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

        detail = self.get_performance(
            str(target.get("uri") or ""),
            callback=callback,
        )
        detail_rows = self._rows_from_performance_detail(
            detail,
            fallback_title=title,
            fallback_artist=artist,
            original_year=original_year,
        )
        if detail_rows:
            return detail_rows

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

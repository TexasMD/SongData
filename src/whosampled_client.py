import logging
import os
import requests
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)

SourceCheckCallback = Callable[[str, str, str, int | None, str], None]

PARSE_API_KEY = os.environ.get("PARSE_API_KEY", "")
PARSE_API_BASE = "https://api.parse.bot/scraper/3d45f4b3-3ed5-4004-9759-c15b7b9b34a7"

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _emit_checked(callback: SourceCheckCallback | None, query_kind: str, query_url: str, result_count: int | None) -> None:
    if callback is None:
        return
    callback("WhoSampled", query_kind, query_url, result_count, _utc_now_iso())

class WhoSampledClient:
    def __init__(self) -> None:
        self.api_key = PARSE_API_KEY

    def _get_headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key}

    def scrape_whosampled_deep(self, title: str, artist: str, *, callback: SourceCheckCallback | None = None, recording_id: str = "") -> list[dict[str, Any]]:
        if not self.api_key:
            logger.warning("[WhoSampled] PARSE_API_KEY is not set. Skipping API query.")
            return []

        # 1. Search for the track
        query = f"{title} {artist}"
        search_url = f"{PARSE_API_BASE}/search?query={query}"

        try:
            resp = requests.get(search_url, headers=self._get_headers(), timeout=15)
            if resp.status_code != 200:
                _emit_checked(callback, "track_search", search_url, None)
                logger.warning(f"[WhoSampled] Search failed with status {resp.status_code}: {resp.text}")
                return []

            search_data = resp.json().get("data", {})
            _emit_checked(callback, "track_search", search_url, len(search_data.get("tracks", [])))

            top_hit = search_data.get("top_hit")
            tracks = search_data.get("tracks", [])

            best_track_url = None

            # Helper to check if URL is a track URL (contains two slugs: artist and track)
            # Format: https://www.whosampled.com/Artist-Name/Track-Name/
            def is_track_url(url: str) -> bool:
                parts = [p for p in url.strip("/").split("/") if p]
                return len(parts) >= 3 and parts[0] == "www.whosampled.com"

            if top_hit and top_hit.get("url") and "/search/" not in top_hit["url"]:
                best_track_url = top_hit["url"]
            elif tracks:
                best_track_url = tracks[0]["url"]

            if not best_track_url:
                logger.info(f"[WhoSampled] No matching track found for {title} by {artist}")
                return []

            # Extract artist_slug and track_slug
            # Example: https://www.whosampled.com/Daft-Punk/Harder,-Better,-Faster,-Stronger/
            parts = [p for p in best_track_url.strip("/").split("/") if p]
            if len(parts) < 3: # Need at least domain, artist, track
                logger.warning(f"[WhoSampled] Unrecognized URL format: {best_track_url}")
                return []

            # Parts could be ['https:', 'www.whosampled.com', 'Daft-Punk', 'Harder,-Better,-Faster,-Stronger']
            # Find the index of www.whosampled.com
            domain_idx = -1
            for i, p in enumerate(parts):
                if p == "www.whosampled.com":
                    domain_idx = i
                    break

            if domain_idx == -1 or domain_idx + 2 >= len(parts):
                logger.warning(f"[WhoSampled] Could not extract slugs from {best_track_url}")
                return []

            artist_slug = parts[domain_idx + 1]
            track_slug = parts[domain_idx + 2]

            # 2. Get track details to find covers
            detail_url = f"{PARSE_API_BASE}/get_track_detail?artist_slug={artist_slug}&track_slug={track_slug}"

            resp = requests.get(detail_url, headers=self._get_headers(), timeout=15)
            if resp.status_code != 200:
                _emit_checked(callback, "track_detail", detail_url, None)
                logger.warning(f"[WhoSampled] Detail fetch failed with status {resp.status_code}: {resp.text}")
                return []

            detail_data = resp.json().get("data", {})
            connections = detail_data.get("connections_summary", [])
            _emit_checked(callback, "track_detail", detail_url, len(connections))

            original_title = detail_data.get("title", title)
            original_artist = detail_data.get("artist", artist)
            original_year = detail_data.get("year", "")

            rows = []
            for conn in connections:
                section = conn.get("section", "").lower()
                action = conn.get("action", "").lower() # Sometimes API has 'action', sometimes we infer from section

                is_cover = False
                if "was covered in" in section or "covers of" in section or action == "was covered in":
                    is_cover = True

                # Check the other direction - if this track IS a cover of something else
                # We could add the original, but the scraper function seems focused on finding covers OF the given song.
                # In the old code, it returned both. Let's return both for completeness.
                is_cover_of = False
                if "is a cover of" in section or action == "is a cover of":
                    is_cover_of = True

                if is_cover:
                    rows.append({
                        "title": conn.get("name", ""),
                        "artist": conn.get("artist", ""),
                        "musicbrainz_recording_id": None,
                        "cover_song": "Yes",
                        "original_title": original_title,
                        "original_artist": original_artist,
                        "original_year": conn.get("year", ""), # conn['year'] is the year of the cover
                        "source": "WhoSampled",
                        "cover_genre": conn.get("tag", ""),
                    })
                elif is_cover_of:
                     rows.append({
                        "title": original_title,
                        "artist": original_artist,
                        "musicbrainz_recording_id": None,
                        "cover_song": "Yes",
                        "original_title": conn.get("name", ""),
                        "original_artist": conn.get("artist", ""),
                        "original_year": original_year,
                        "source": "WhoSampled",
                        "cover_genre": "",
                    })

            # The API doesn't seem to paginate connections_summary in get_track_detail.
            # If we needed to, we could use the new `get_artist_covered_by` endpoint, but we only have `title` and `artist`.
            # We would need to fetch all pages of `get_artist_covered_by` and find our track.
            # `connections_summary` is usually sufficient for a single track's direct connections.

            return rows

        except Exception as e:
            logger.error(f"[WhoSampled] Exception during API fetch: {e}")
            return []

client = WhoSampledClient()

def scrape_whosampled(title: str, artist: str, *, callback: SourceCheckCallback | None = None, recording_id: str = "") -> list:
    return client.scrape_whosampled_deep(title, artist, callback=callback, recording_id=recording_id)

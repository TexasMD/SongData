import time
import random
import requests
import logging
import re
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import quote_plus

from src.cover_info_client import scrape_cover_info
from src.secondhandsongs_client import scrape_secondhandsongs as scrape_secondhandsongs_client
from src.whosampled_client import scrape_whosampled as scrape_whosampled_client

logger = logging.getLogger(__name__)

USER_AGENT = "MusicDB_Bot/1.0 ( antigravity@example.com )"

BROWSER_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0"
]

SourceCheckCallback = Callable[[str, str, str, int | None, str], None]
SourceScrapeFn = Callable[[str, str, str, SourceCheckCallback | None], list[dict]]
CROSS_SOURCE_EMPTY_RETRY_THRESHOLD = 10
RELATIONSHIP_COVER_SOURCES = ("cover.info", "SecondHandSongs", "WhoSampled")

def get_random_headers():
    return {
        "User-Agent": random.choice(BROWSER_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
    }


def _emit_checked(
    on_source_checked: SourceCheckCallback | None,
    *,
    source: str,
    query_kind: str,
    query_url: str,
    result_count: int | None,
) -> None:
    if on_source_checked is None:
        return
    on_source_checked(
        source,
        query_kind,
        query_url,
        result_count,
        datetime.now(timezone.utc).isoformat(),
    )


def fetch_work_id_for_recording(
    title: str,
    artist: str,
    on_source_checked: SourceCheckCallback | None = None,
) -> str:
    """Finds the MusicBrainz Work ID for a given title and artist."""
    url = "https://musicbrainz.org/ws/2/recording/"
    params = {
        "query": f'recording:"{title}" AND artist:"{artist}"',
        "fmt": "json",
    }
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            _emit_checked(on_source_checked, source="MusicBrainz", query_kind="recording_search", query_url=resp.url if resp is not None else url, result_count=0)
            return None

        data = resp.json()
        recordings = data.get("recordings", [])
        _emit_checked(on_source_checked, source="MusicBrainz", query_kind="recording_search", query_url=resp.url, result_count=len(recordings))
        if not recordings:
            return None

        # Get the first recording's work relations
        rec_id = recordings[0]["id"]
        time.sleep(1.1)  # Respect rate limit

        lookup_url = f"https://musicbrainz.org/ws/2/recording/{rec_id}"
        lookup_params = {"inc": "work-rels", "fmt": "json"}
        lookup_resp = requests.get(lookup_url, params=lookup_params, headers=headers, timeout=10)

        if lookup_resp.status_code == 200:
            rec_data = lookup_resp.json()
            relations = rec_data.get("relations", [])
            for rel in relations:
                if rel.get("target-type") == "work" and rel.get("work"):
                    _emit_checked(on_source_checked, source="MusicBrainz", query_kind="work_lookup", query_url=lookup_resp.url, result_count=len(relations))
                    return rel["work"]["id"]
            _emit_checked(on_source_checked, source="MusicBrainz", query_kind="work_lookup", query_url=lookup_resp.url, result_count=len(relations))
            return None
        _emit_checked(on_source_checked, source="MusicBrainz", query_kind="work_lookup", query_url=lookup_resp.url if lookup_resp is not None else lookup_url, result_count=0)
    except Exception as e:
        logger.error(f"Error fetching work ID: {e}")

    return None

def fetch_covers_for_work(
    work_id: str,
    original_title: str,
    original_artist: str,
    original_year: str = "",
    on_source_checked: SourceCheckCallback | None = None,
) -> list:
    """Fetches covers (recordings) for a given Work ID."""
    url = "https://musicbrainz.org/ws/2/recording"
    params = {
        "work": work_id,
        "inc": "artists",
        "fmt": "json",
        "limit": 100
    }
    headers = {"User-Agent": USER_AGENT}
    covers = []
    try:
        time.sleep(1.1)
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            recordings = data.get("recordings", [])
            for rec in recordings:
                title = rec.get("title")
                mbid = rec.get("id")
                artist_credit = rec.get("artist-credit", [])
                artist_name = artist_credit[0].get("name", "Unknown") if artist_credit else "Unknown"

                if artist_name.lower() != original_artist.lower():
                    covers.append({
                        "title": title,
                        "artist": artist_name,
                        "musicbrainz_recording_id": mbid,
                        "cover_song": "Yes",
                        "original_title": original_title,
                        "original_artist": original_artist,
                        "original_year": original_year,
                        "source": "MusicBrainz"
                    })
            _emit_checked(on_source_checked, source="MusicBrainz", query_kind="work_covers", query_url=resp.url, result_count=len(recordings))
        else:
            _emit_checked(on_source_checked, source="MusicBrainz", query_kind="work_covers", query_url=resp.url if resp is not None else url, result_count=0)
    except Exception as e:
        logger.error(f"Error fetching covers for work {work_id}: {e}")

    return covers

def scrape_secondhandsongs(
    title: str,
    artist: str,
    original_year: str = "",
    on_source_checked: SourceCheckCallback | None = None,
) -> list:
    return scrape_secondhandsongs_client(
        title,
        artist,
        original_year,
        callback=on_source_checked,
    )

def scrape_whosampled(
    title: str,
    artist: str,
    original_year: str = "",
    on_source_checked: SourceCheckCallback | None = None,
) -> list:
    return scrape_whosampled_client(
        title,
        artist,
        callback=on_source_checked,
        recording_id="",
    )


def _scrape_musicbrainz(
    title: str,
    artist: str,
    original_year: str,
    on_source_checked: SourceCheckCallback | None = None,
) -> list[dict]:
    work_id = fetch_work_id_for_recording(title, artist, on_source_checked=on_source_checked)
    if not work_id:
        return []
    return fetch_covers_for_work(work_id, title, artist, original_year, on_source_checked=on_source_checked)


def _scrape_cover_info_source(
    title: str,
    artist: str,
    original_year: str,
    on_source_checked: SourceCheckCallback | None = None,
) -> list[dict]:
    return scrape_cover_info(title, artist, original_year, callback=on_source_checked)


def _retry_suspicious_empty_sources(
    source_rows: dict[str, list[dict]],
    source_fns: dict[str, SourceScrapeFn],
    title: str,
    artist: str,
    original_year: str,
    on_source_checked: SourceCheckCallback | None,
) -> None:
    best_source_count = max((len(rows) for rows in source_rows.values()), default=0)
    if best_source_count < CROSS_SOURCE_EMPTY_RETRY_THRESHOLD:
        return

    for source, rows in list(source_rows.items()):
        if rows:
            continue
        retry_rows = _scrape_source(
            source,
            source_fns[source],
            title,
            artist,
            original_year,
            on_source_checked,
        )
        source_rows[source] = retry_rows
        _emit_checked(
            on_source_checked,
            source=source,
            query_kind="cross_source_empty_retry",
            query_url="internal://cross-source-empty-retry",
            result_count=len(retry_rows),
        )


def _scrape_source(
    source: str,
    scrape_fn: SourceScrapeFn,
    title: str,
    artist: str,
    original_year: str,
    on_source_checked: SourceCheckCallback | None,
) -> list[dict]:
    try:
        return scrape_fn(title, artist, original_year, on_source_checked)
    except Exception as exc:  # noqa: BLE001 - keep other cover sources running.
        logger.exception("Cover source %s failed for %s by %s", source, title, artist)
        _emit_checked(
            on_source_checked,
            source=source,
            query_kind="source_error",
            query_url=f"internal://source-error/{source}",
            result_count=0,
        )
        return []


def scrape_covers(
    title: str,
    artist: str,
    original_year: str = "",
    on_source_checked: SourceCheckCallback | None = None,
) -> list:
    """Scrape covers from all relationship sources and deduplicate.

    cover.info, SecondHandSongs, and WhoSampled are always attempted. MusicBrainz
    is an additional open relationship source, not a substitute for those three.
    """
    source_fns: dict[str, SourceScrapeFn] = {
        "MusicBrainz": _scrape_musicbrainz,
        "cover.info": _scrape_cover_info_source,
        "SecondHandSongs": scrape_secondhandsongs,
        "WhoSampled": scrape_whosampled,
    }
    source_rows = {
        source: _scrape_source(source, scrape_fn, title, artist, original_year, on_source_checked)
        for source, scrape_fn in source_fns.items()
    }
    _retry_suspicious_empty_sources(source_rows, source_fns, title, artist, original_year, on_source_checked)
    covers = [cover for rows in source_rows.values() for cover in rows]

    # Deduplicate based on title and artist
    unique_covers = {}
    for cover in covers:
        key = f"{cover['title'].lower()}|{cover['artist'].lower()}"
        if key not in unique_covers:
            unique_covers[key] = cover
        else:
            # Merge sources if not already included
            existing_source = unique_covers[key].get("source", "")
            new_source = cover.get("source", "")
            if new_source and new_source not in existing_source:
                unique_covers[key]["source"] = f"{existing_source}, {new_source}"

            # Retain MBID if one has it and the other doesn't
            if cover.get("musicbrainz_recording_id") and not unique_covers[key].get("musicbrainz_recording_id"):
                unique_covers[key]["musicbrainz_recording_id"] = cover["musicbrainz_recording_id"]

            for field in ("original_title", "original_artist", "original_year"):
                if cover.get(field) and not unique_covers[key].get(field):
                    unique_covers[key][field] = cover[field]

    return list(unique_covers.values())

if __name__ == "__main__":
    # Test script
    print("Testing scrape_covers with Hallelujah by Leonard Cohen...")
    res = scrape_covers("Hallelujah", "Leonard Cohen")
    print(f"Found {len(res)} unique covers:")
    for c in res[:5]:
        print(f"- {c['title']} by {c['artist']} ({c.get('source')})")

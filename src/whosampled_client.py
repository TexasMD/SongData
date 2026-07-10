from __future__ import annotations

from datetime import datetime, timezone
import logging
import random
import re
import time
from urllib.parse import quote_plus, urljoin
from typing import Any, Callable

import cloudscraper
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SourceCheckCallback = Callable[[str, str, str, int | None, str], None]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit_checked(callback, query_kind: str, query_url: str, result_count: int | None) -> None:
    if callback is None:
        return
    callback("WhoSampled", query_kind, query_url, result_count, _utc_now_iso())


def _clean(text: str) -> str:
    return " ".join(text.split()).strip()


class WhoSampledClient:
    def __init__(self) -> None:
        self.session = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        self.base_delay = 4.0

    def _rotate_user_agent(self) -> None:
        pass

    def _wait(self) -> None:
        jitter = random.uniform(-1.0, 3.5)
        delay = max(2.5, self.base_delay + jitter)
        print(f"    [WhoSampled] Waiting {delay:.2f}s...")
        time.sleep(delay)

    def fetch(
        self,
        url: str,
        *,
        callback=None,
        recording_id: str = "",
        query_kind: str = "lookup",
    ) -> BeautifulSoup | None:
        for attempt in range(3):
            self._wait()
            try:
                resp = self.session.get(url, timeout=15)
                if resp.status_code == 200:
                    _emit_checked(callback, query_kind, resp.url, 0)
                    return BeautifulSoup(resp.text, "html.parser")
                if resp.status_code in (403, 429):
                    print(f"    [WhoSampled] Blocked (Status {resp.status_code}). Backing off...")
                    self.base_delay *= 2
                    self._rotate_user_agent()
                else:
                    print(f"    [WhoSampled] Error status {resp.status_code}")
                    return None
            except Exception as exc:
                print(f"    [WhoSampled] Request failed: {exc}")
                self.base_delay += 2
        return None

    @staticmethod
    def _normalize(text: str | None) -> str:
        if not text:
            return ""
        return re.sub(r"[^a-z0-9]+", "", text.lower())

    @classmethod
    def _extract_artist_from_title(cls, title_attr: str) -> tuple[str, str]:
        title_attr = title_attr.strip()
        match = re.match(r"^(?P<artist>.+?)\s+by\s+(?P<song>.+)$", title_attr, re.IGNORECASE)
        if not match:
            return "", ""
        return match.group("artist").strip(), match.group("song").strip()

    def _parse_track_card(self, item: BeautifulSoup) -> tuple[str, str, str]:
        track_title = ""
        track_artist = ""
        track_year = ""

        track_h3 = item.select_one("h3.trackName")
        track_title_node = item.select_one('h3.trackName a span[itemprop="name"]') or item.select_one("h3.trackName a")
        if track_title_node:
            track_title = track_title_node.get_text(" ", strip=True).strip()
        elif track_h3:
            track_title = re.sub(r"\s*\(\d{4}\)$", "", track_h3.get_text(" ", strip=True)).strip()

        track_cover = item.select_one("a.trackCover")
        if track_cover:
            title_attr = track_cover.get("title", "").strip()
            artist_text, song_text = self._extract_artist_from_title(title_attr)
            if artist_text:
                track_artist = artist_text
            if not track_title and song_text:
                track_title = song_text

        if not track_artist:
            artist_h1 = item.find_parent("article")
            if artist_h1:
                artist_node = artist_h1.select_one("h1.artistName")
                if artist_node:
                    track_artist = artist_node.get_text(" ", strip=True).strip()

        year_node = item.select_one("span.trackYear")
        if year_node:
            track_year = year_node.get_text(" ", strip=True).strip("()")

        return track_title, track_artist, track_year

    def _parse_connection_rows(self, soup: BeautifulSoup, original_title: str, original_artist: str) -> list[dict[str, Any]]:
        rows: list[dict] = []

        for header in soup.find_all(["h2", "h3"]):
            header_text = _clean(header.get_text(" ", strip=True))
            section = header.find_parent(["section", "div", "article"])
            if not section:
                continue

            if header_text.startswith("Covered in ") or header_text.startswith("Is a cover of "):
                for table in section.find_all("table"):
                    for tr in table.select("tbody tr"):
                        cells = tr.find_all("td")
                        if len(cells) < 3:
                            continue
                        song_link = tr.select_one("a.trackName")
                        if not song_link:
                            continue

                        song_text = _clean(song_link.get_text(" ", strip=True))
                        artist_link = cells[2].find("a")
                        artist_text = _clean(artist_link.get_text(" ", strip=True)) if artist_link else _clean(cells[2].get_text(" ", strip=True))
                        year_text = _clean(cells[3].get_text(" ", strip=True)) if len(cells) > 3 else ""
                        genre_text = _clean(cells[4].get_text(" ", strip=True)) if len(cells) > 4 else ""

                        if header_text.startswith("Covered in "):
                            rows.append(
                                {
                                    "title": song_text,
                                    "artist": artist_text,
                                    "musicbrainz_recording_id": None,
                                    "cover_song": "Yes",
                                    "original_title": original_title,
                                    "original_artist": original_artist,
                                    "original_year": year_text,
                                    "source": "WhoSampled",
                                    "cover_genre": genre_text,
                                }
                            )
                        else:
                            rows.append(
                                {
                                    "title": original_title,
                                    "artist": original_artist,
                                    "musicbrainz_recording_id": None,
                                    "cover_song": "Yes",
                                    "original_title": song_text,
                                    "original_artist": artist_text,
                                    "original_year": year_text,
                                    "source": "WhoSampled",
                                    "cover_genre": genre_text,
                                }
                            )

            elif header_text.startswith("Covers of"):
                links = [a.get_text(" ", strip=True).strip() for a in header.find_all("a")]
                if len(links) >= 2:
                    original_artist = links[0]
                    original_title = links[1]
                    for table in section.find_all("table"):
                        for tr in table.select("tbody tr"):
                            cells = tr.find_all("td")
                            if len(cells) < 3:
                                continue
                            song_link = tr.select_one("a.trackName")
                            if not song_link:
                                continue
                            song_text = _clean(song_link.get_text(" ", strip=True))
                            artist_link = cells[2].find("a")
                            artist_text = _clean(artist_link.get_text(" ", strip=True)) if artist_link else _clean(cells[2].get_text(" ", strip=True))
                            year_text = _clean(cells[3].get_text(" ", strip=True)) if len(cells) > 3 else ""
                            genre_text = _clean(cells[4].get_text(" ", strip=True)) if len(cells) > 4 else ""
                            rows.append(
                                {
                                    "title": song_text,
                                    "artist": artist_text,
                                    "musicbrainz_recording_id": None,
                                    "cover_song": "Yes",
                                    "original_title": original_title,
                                    "original_artist": original_artist,
                                    "original_year": year_text,
                                    "source": "WhoSampled",
                                    "cover_genre": genre_text,
                                }
                            )

        for item in soup.select("section.trackItem"):
            track_song, track_artist, track_year = self._parse_track_card(item)
            if not track_song:
                continue

            for conn in item.select("div.trackConnections div.track-connection"):
                action = conn.select_one("span.sampleAction")
                li = conn.find("li")
                if not action or li is None:
                    continue

                action_text = _clean(action.get_text(" ", strip=True)).lower()
                if action_text == "is a cover of":
                    original_link = li.select_one("a.connectionName")
                    if not original_link:
                        continue
                    original_song = _clean(original_link.get_text(" ", strip=True))
                    artist_links = []
                    for a in li.find_all("a"):
                        href = a.get("href", "")
                        if href.startswith("/cover/") or a is original_link:
                            continue
                        artist_links.append(_clean(a.get_text(" ", strip=True)))
                    original_artist = ", ".join([a for a in artist_links if a])
                    rows.append(
                        {
                            "title": track_song,
                            "artist": track_artist,
                            "musicbrainz_recording_id": None,
                            "cover_song": "Yes",
                            "original_title": original_song,
                            "original_artist": original_artist,
                            "original_year": track_year,
                            "source": "WhoSampled",
                            "cover_genre": "",
                        }
                    )

                elif action_text == "was covered in":
                    cover_link = li.select_one("a.connectionName")
                    if not cover_link:
                        continue
                    cover_song = _clean(cover_link.get_text(" ", strip=True))
                    performing_artist = ""
                    year_text = ""
                    text = _clean(li.get_text(" ", strip=True))
                    match = re.search(r"by\s+(.*?)(?:\s*\((\d{4})\))?$", text)
                    if match:
                        performing_artist = match.group(1).strip()
                        year_text = match.group(2) or ""
                    rows.append(
                        {
                            "title": cover_song,
                            "artist": performing_artist,
                            "musicbrainz_recording_id": None,
                            "cover_song": "Yes",
                            "original_title": track_song,
                            "original_artist": track_artist,
                            "original_year": year_text,
                            "source": "WhoSampled",
                            "cover_genre": "",
                        }
                    )

        return rows

    def search_song_url(self, title: str, artist: str, *, callback=None, recording_id: str = "") -> str | None:
        query = quote_plus(f"{title} {artist}")
        search_url = f"https://www.whosampled.com/search/tracks/?q={query}"
        print(f"    [WhoSampled] Searching: {search_url}")
        soup = self.fetch(search_url, callback=callback, recording_id=recording_id, query_kind="track_search")
        if not soup:
            return None

        desired_title = self._normalize(title)
        desired_artist = self._normalize(artist)

        matches: list[str] = []
        for item in soup.select("li.listEntry.trackEntry"):
            title_el = item.select_one(".trackName")
            artist_el = item.select_one(".trackArtist a")
            if not title_el or not artist_el:
                continue
            href = title_el.get("href")
            item_title = self._normalize(title_el.get_text(" ", strip=True))
            item_artist = self._normalize(artist_el.get_text(" ", strip=True))
            if href and item_title == desired_title and item_artist == desired_artist:
                return urljoin("https://www.whosampled.com", href)
            if href and item_title == desired_title:
                matches.append(urljoin("https://www.whosampled.com", href))

        return matches[0] if matches else None

    def extract_covers_from_page(self, soup: BeautifulSoup, original_title: str, original_artist: str) -> list[dict[str, Any]]:
        return self._parse_connection_rows(soup, original_title, original_artist)

    def scrape_whosampled_deep(self, title: str, artist: str, *, callback=None, recording_id: str = "") -> list[dict[str, Any]]:
        song_url = self.search_song_url(title, artist, callback=callback, recording_id=recording_id)
        if not song_url:
            return []

        page_urls = [song_url]
        if not song_url.endswith("/covered/"):
            page_urls.append(urljoin(song_url, "covered/"))

        covers: list[dict] = []
        seen_urls: set[str] = set()
        for start_url in page_urls:
            current_url = start_url
            page_num = 1
            while current_url and current_url not in seen_urls:
                seen_urls.add(current_url)
                print(f"    [WhoSampled] Fetching page {page_num}: {current_url}")
                query_kind = "track_page" if not current_url.endswith("/covered/") else "cover_page"
                soup = self.fetch(current_url, callback=callback, recording_id=recording_id, query_kind=query_kind)
                if not soup:
                    break

                page_covers = self.extract_covers_from_page(soup, title, artist)
                covers.extend(page_covers)
                print(f"    [WhoSampled] Found {len(page_covers)} covers on page {page_num}")

                next_link = None
                pagination = soup.select_one("span.next a")
                if pagination and pagination.get("href"):
                    next_href = pagination.get("href")
                    if next_href and not next_href.startswith("#"):
                        next_link = urljoin(current_url, next_href)

                current_url = next_link
                page_num += 1

        return covers


client = WhoSampledClient()


def scrape_whosampled(title: str, artist: str, *, callback=None, recording_id: str = "") -> list:
    return client.scrape_whosampled_deep(title, artist, callback=callback, recording_id=recording_id)

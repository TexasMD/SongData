#!/usr/bin/env python3
"""Verify unverified songs against external music services.

Credentials are read from environment variables:
- SPOTIFY_CLIENT_ID
- SPOTIFY_CLIENT_SECRET
- DISCOGS_TOKEN
- MUSICBRAINZ_USER_AGENT

By default this script is a dry run. Pass --write to save changes.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB = PROJECT_DIR / "data" / "processed" / "Main_Song_Database.csv"
DEFAULT_LOG = PROJECT_DIR / "data" / "logs" / "verification_pass.log"


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line, flush=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def fmt_ms(value: object) -> str:
    value = clean(value)
    if not value:
        return ""
    try:
        seconds = int(float(value)) // 1000
    except ValueError:
        return ""
    return f"{seconds // 60}:{seconds % 60:02d}"


def session() -> requests.Session:
    s = requests.Session()
    retry = Retry(connect=3, read=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


def spotify_token(s: requests.Session, log_path: Path) -> str | None:
    client_id = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        log(log_path, "Spotify credentials not configured; Spotify verification disabled.")
        return None
    try:
        response = s.post(
            "https://accounts.spotify.com/api/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        log(log_path, f"Spotify auth failed with HTTP {response.status_code}.")
    except requests.RequestException as exc:
        log(log_path, f"Spotify auth error: {exc}")
    return None


def apply_metadata(row: dict[str, str], metadata: dict[str, str]) -> int:
    changed = 0
    for field in ["Album", "Genre", "Year", "Duration"]:
        value = clean(metadata.get(field))
        if value and not clean(row.get(field)):
            row[field] = value
            changed += 1
    return changed


def bounded_retry_after(response: requests.Response, max_retry_after: int) -> bool:
    wait = int(response.headers.get("Retry-After", "0") or "0")
    if wait <= 0 or wait > max_retry_after:
        return False
    time.sleep(wait)
    return True


def check_spotify(
    s: requests.Session,
    token: str | None,
    title: str,
    artist: str,
    max_retry_after: int,
) -> dict[str, str] | None:
    if not token:
        return None
    q = f"track:{title} artist:{artist}"
    try:
        response = s.get(
            f"https://api.spotify.com/v1/search?q={quote(q)}&type=track&limit=3",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if response.status_code == 429 and bounded_retry_after(response, max_retry_after):
            return check_spotify(s, token, title, artist, max_retry_after)
        if response.status_code != 200:
            return None
        for track in response.json().get("tracks", {}).get("items", []):
            track_name = track.get("name", "").lower()
            artists = [a.get("name", "").lower() for a in track.get("artists", [])]
            if (artist.lower() in artists or any(artist.lower()[:8] in a for a in artists)) and (
                title.lower() in track_name or track_name in title.lower() or title.lower()[:10] in track_name
            ):
                album = track.get("album", {})
                release_date = album.get("release_date", "")
                return {
                    "Album": album.get("name", ""),
                    "Year": release_date[:4] if re.match(r"^\d{4}", release_date) else "",
                    "Duration": fmt_ms(track.get("duration_ms")),
                    "Genre": "",
                    "Spotify Track ID": track.get("id", ""),
                }
    except requests.RequestException:
        return None
    return None


def check_itunes(s: requests.Session, title: str, artist: str) -> dict[str, str] | None:
    try:
        response = s.get(
            f"https://itunes.apple.com/search?term={quote(f'{artist} {title}')}&media=music&limit=3",
            timeout=10,
        )
        if response.status_code != 200:
            return None
        for result in response.json().get("results", []):
            result_artist = result.get("artistName", "").lower()
            result_title = result.get("trackName", "").lower()
            if (artist.lower() in result_artist or artist.lower()[:8] in result_artist) and (
                title.lower() in result_title or result_title in title.lower() or title.lower()[:10] in result_title
            ):
                release_date = result.get("releaseDate", "")
                year = re.match(r"^(\d{4})", release_date)
                return {
                    "Album": result.get("collectionName", ""),
                    "Genre": result.get("primaryGenreName", ""),
                    "Year": year.group(1) if year else "",
                    "Duration": fmt_ms(result.get("trackTimeMillis")),
                }
    except requests.RequestException:
        return None
    return None


def check_discogs(
    s: requests.Session,
    title: str,
    artist: str,
    max_retry_after: int,
    log_path: Path,
) -> dict[str, str] | None:
    token = os.getenv("DISCOGS_TOKEN", "").strip()
    if not token:
        return None
    try:
        response = s.get(
            "https://api.discogs.com/database/search"
            f"?track={quote(title)}&artist={quote(artist)}&token={quote(token)}",
            headers={"User-Agent": "MusicDBVerifier/1.0"},
            timeout=15,
        )
        if response.status_code == 429 and bounded_retry_after(response, max_retry_after):
            return check_discogs(s, title, artist, max_retry_after, log_path)
        if response.status_code != 200:
            return None
        results = response.json().get("results", [])
        if not results:
            return None
        result = results[0]
        title_value = result.get("title", "")
        return {
            "Album": title_value.split(" - ")[-1] if " - " in title_value else "",
            "Genre": result.get("genre", [""])[0] if result.get("genre") else "",
            "Year": str(result.get("year", "") or ""),
            "Duration": "",
        }
    except requests.RequestException as exc:
        log(log_path, f"Discogs error: {exc}")
    return None


def check_musicbrainz(
    s: requests.Session,
    title: str,
    artist: str,
    max_retry_after: int,
    log_path: Path,
) -> dict[str, str] | None:
    user_agent = os.getenv("MUSICBRAINZ_USER_AGENT", "MusicDBVerifier/1.0").strip()
    query = f'recording:"{title}" AND artist:"{artist}"'
    try:
        response = s.get(
            f"https://musicbrainz.org/ws/2/recording/?query={quote(query)}&fmt=json",
            headers={"User-Agent": user_agent},
            timeout=15,
        )
        if response.status_code in {429, 503} and bounded_retry_after(response, max_retry_after):
            return check_musicbrainz(s, title, artist, max_retry_after, log_path)
        if response.status_code != 200:
            return None
        recordings = response.json().get("recordings", [])
        if not recordings:
            return None
        first = recordings[0]
        releases = first.get("releases", [])
        year = ""
        for release in releases:
            match = re.search(r"\b(19\d{2}|20[0-2]\d)\b", release.get("date", ""))
            if match and (not year or int(match.group(1)) < int(year)):
                year = match.group(1)
        tags = first.get("tags", [])
        return {
            "Album": releases[0].get("title", "") if releases else "",
            "Genre": tags[0].get("name", "") if tags else "",
            "Year": year,
            "Duration": fmt_ms(first.get("length")),
            "MusicBrainz Recording ID": first.get("id", ""),
        }
    except requests.RequestException as exc:
        log(log_path, f"MusicBrainz error: {exc}")
    return None


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Verify unverified SongDB rows.")
    parser.add_argument("--main", type=Path, default=DEFAULT_DB)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--limit", type=int, default=0, help="Maximum rows to process; 0 means no limit.")
    parser.add_argument("--max-retry-after", type=int, default=60)
    parser.add_argument("--write", action="store_true", help="Write changes to the database.")
    args = parser.parse_args()

    with args.main.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]

    for field in ["Spotify Track ID", "Spotify Verified", "iTunes Verified", "Discogs Verified", "MusicBrainz Verified", "MusicBrainz Recording ID"]:
        if field not in headers:
            headers.append(field)
        for row in rows:
            row.setdefault(field, "")

    s = session()
    token = spotify_token(s, args.log)
    processed = verified = metadata_filled = 0

    for row in rows:
        if args.limit and processed >= args.limit:
            break
        if any(clean(row.get(field)) == "Yes" for field in ["Spotify Verified", "iTunes Verified", "MusicBrainz Verified", "Discogs Verified"]):
            continue
        title = clean(row.get("Title"))
        artist = clean(row.get("Artist"))
        if not title or not artist:
            continue
        processed += 1
        lookup_artist = re.split(r"\s+(?:feat|ft|featuring)\s+", artist, flags=re.I)[0].strip()

        result = check_spotify(s, token, title, lookup_artist, args.max_retry_after)
        if result:
            row["Spotify Verified"] = "Yes"
            if result.get("Spotify Track ID") and not clean(row.get("Spotify Track ID")):
                row["Spotify Track ID"] = result["Spotify Track ID"]
            verified += 1
            metadata_filled += apply_metadata(row, result)
            continue

        result = check_itunes(s, title, lookup_artist)
        if result:
            row["iTunes Verified"] = "Yes"
            verified += 1
            metadata_filled += apply_metadata(row, result)
            continue

        result = check_discogs(s, title, lookup_artist, args.max_retry_after, args.log)
        if result:
            row["Discogs Verified"] = "Yes"
            verified += 1
            metadata_filled += apply_metadata(row, result)
            continue

        result = check_musicbrainz(s, title, lookup_artist, args.max_retry_after, args.log)
        if result:
            row["MusicBrainz Verified"] = "Yes"
            if result.get("MusicBrainz Recording ID") and not clean(row.get("MusicBrainz Recording ID")):
                row["MusicBrainz Recording ID"] = result["MusicBrainz Recording ID"]
            verified += 1
            metadata_filled += apply_metadata(row, result)

    log(args.log, f"Processed={processed}; verified={verified}; metadata_filled={metadata_filled}; write={args.write}")
    if args.write:
        with args.main.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

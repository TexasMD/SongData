#!/usr/bin/env python3
"""Clean obvious artist-name noise and optionally verify rows safely.

Credentials are read from environment variables:
- SPOTIFY_CLIENT_ID
- SPOTIFY_CLIENT_SECRET

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

try:
    import emoji
except ImportError:  # Keep the script usable without optional emoji package.
    emoji = None


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB = PROJECT_DIR / "data" / "processed" / "Main_Song_Database.csv"
DEFAULT_LOG = PROJECT_DIR / "data" / "logs" / "cleanup_and_verify.log"


def log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line, flush=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def clean_artist_name(artist: str) -> str:
    artist = clean(artist)
    if emoji:
        artist = emoji.replace_emoji(artist, replace="")
    artist = re.sub(r"^(?:\d{1,3}|[IVXLCDM]+)\s*\.\s*", "", artist, flags=re.I)
    artist = re.sub(r"^[\-\*\|_~]\s*", "", artist)
    artist = re.sub(r"^Songs Like\s+", "", artist, flags=re.I)
    return clean(artist)


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
        log(log_path, "Spotify credentials not configured; skipping Spotify verification.")
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


def check_spotify(s: requests.Session, token: str, title: str, artist: str, max_retry_after: int) -> str | None:
    q = f"track:{title} artist:{artist}"
    try:
        response = s.get(
            f"https://api.spotify.com/v1/search?q={quote(q)}&type=track&limit=5",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if response.status_code == 429:
            wait = int(response.headers.get("Retry-After", "0") or "0")
            if wait > max_retry_after:
                return None
            time.sleep(wait)
            return check_spotify(s, token, title, artist, max_retry_after)
        if response.status_code != 200:
            return None
        for track in response.json().get("tracks", {}).get("items", []):
            artists = [a.get("name", "").lower() for a in track.get("artists", [])]
            if artist.lower() in artists or any(artist.lower()[:8] in a for a in artists):
                return track.get("id")
    except requests.RequestException:
        return None
    return None


def check_itunes(s: requests.Session, title: str, artist: str) -> bool:
    try:
        response = s.get(
            f"https://itunes.apple.com/search?term={quote(f'{artist} {title}')}&media=music&limit=3",
            timeout=10,
        )
        if response.status_code != 200:
            return False
        for result in response.json().get("results", []):
            result_artist = result.get("artistName", "").lower()
            if artist.lower() in result_artist or artist.lower()[:8] in result_artist:
                return True
    except requests.RequestException:
        return False
    return False


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Clean and verify obvious unverified SongDB rows.")
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

    s = session()
    token = spotify_token(s, args.log)
    cleaned_count = 0
    verified_count = 0
    processed = 0

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
        cleaned_artist = clean_artist_name(artist)
        if cleaned_artist and cleaned_artist != artist:
            row["Artist"] = cleaned_artist
            cleaned_count += 1
            log(args.log, f"Cleaned artist: {artist!r} -> {cleaned_artist!r}")
        if token:
            spotify_id = check_spotify(s, token, title, cleaned_artist or artist, args.max_retry_after)
            if spotify_id:
                row["Spotify Verified"] = "Yes"
                if not clean(row.get("Spotify Track ID")):
                    row["Spotify Track ID"] = spotify_id
                verified_count += 1
                continue
        if check_itunes(s, title, cleaned_artist or artist):
            row["iTunes Verified"] = "Yes"
            verified_count += 1
        time.sleep(0.1)

    log(args.log, f"Processed {processed} unverified rows; cleaned={cleaned_count}; verified={verified_count}; write={args.write}")
    if args.write:
        with args.main.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

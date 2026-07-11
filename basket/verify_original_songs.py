from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "basket" / "original_songs.csv"
DEFAULT_OUTPUT = ROOT / "basket" / "original_songs_verified.csv"
DEFAULT_LOG = ROOT / "data" / "logs" / "verify_original_songs.log"


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def normalize(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean(value).lower())


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line, flush=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


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
        log(log_path, "Spotify credentials not configured; Spotify checks disabled.")
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
            timeout=15,
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        log(log_path, f"Spotify auth failed with HTTP {response.status_code}.")
    except requests.RequestException as exc:
        log(log_path, f"Spotify auth error: {exc}")
    return None


def parse_title_candidates(row: dict[str, str]) -> list[str]:
    candidates = []
    for field in ["Base Title", "Title"]:
        value = clean(row.get(field))
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def parse_artist_candidates(row: dict[str, str]) -> list[str]:
    artist = clean(row.get("Artist"))
    if not artist:
        return []
    base = re.split(r"\s+(?:feat\.?|ft\.?|featuring)\s+", artist, flags=re.I)[0].strip()
    candidates = [base or artist]
    if artist not in candidates:
        candidates.append(artist)
    return candidates


def bounded_retry_after(response: requests.Response, max_retry_after: int) -> bool:
    wait = int(response.headers.get("Retry-After", "0") or "0")
    if wait <= 0 or wait > max_retry_after:
        return False
    time.sleep(wait)
    return True


def spotify_search(
    s: requests.Session,
    token: str | None,
    title: str,
    artist: str,
    max_retry_after: int,
) -> dict[str, Any] | None:
    if not token:
        return None
    q = f'track:"{title}" artist:"{artist}"'
    try:
        response = s.get(
            f"https://api.spotify.com/v1/search?q={quote(q)}&type=track&limit=10",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if response.status_code == 429 and bounded_retry_after(response, max_retry_after):
            return spotify_search(s, token, title, artist, max_retry_after)
        if response.status_code != 200:
            return None
        return response.json()
    except requests.RequestException:
        return None


def spotify_track_by_id(
    s: requests.Session,
    token: str | None,
    track_id: str,
    max_retry_after: int,
) -> dict[str, Any] | None:
    if not token or not track_id:
        return None
    try:
        response = s.get(
            f"https://api.spotify.com/v1/tracks/{quote(track_id)}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if response.status_code == 429 and bounded_retry_after(response, max_retry_after):
            return spotify_track_by_id(s, token, track_id, max_retry_after)
        if response.status_code != 200:
            return None
        return response.json()
    except requests.RequestException:
        return None


def spotify_match(row: dict[str, str], s: requests.Session, token: str | None, max_retry_after: int) -> dict[str, str]:
    row_title = clean(row.get("Title"))
    row_artist = clean(row.get("Artist"))
    row_album = clean(row.get("Album"))
    title_candidates = parse_title_candidates(row)
    artist_candidates = parse_artist_candidates(row)

    best: dict[str, str] | None = None
    best_score = -1

    for title in title_candidates:
        for artist in artist_candidates:
            payload = spotify_search(s, token, title, artist, max_retry_after)
            if not payload:
                continue
            for track in payload.get("tracks", {}).get("items", []):
                track_name = clean(track.get("name"))
                track_artists = [clean(a.get("name")) for a in track.get("artists", [])]
                album = track.get("album", {}) or {}
                album_name = clean(album.get("name"))
                release_date = clean(album.get("release_date"))

                title_score = 0
                if normalize(track_name) == normalize(title):
                    title_score += 6
                elif normalize(title) in normalize(track_name) or normalize(track_name) in normalize(title):
                    title_score += 4

                artist_score = 0
                if any(normalize(artist) == normalize(a) for a in track_artists):
                    artist_score += 6
                elif any(normalize(artist) and normalize(artist) in normalize(a) for a in track_artists):
                    artist_score += 4

                album_score = 0
                if row_album and normalize(row_album) == normalize(album_name):
                    album_score += 2

                score = title_score + artist_score + album_score
                if score > best_score:
                    best_score = score
                    best = {
                        "spotify_verified": "Yes" if score >= 10 else "No",
                        "spotify_track_id": clean(track.get("id")),
                        "spotify_matched_title": track_name,
                        "spotify_matched_artist": ", ".join(track_artists),
                        "spotify_matched_album": album_name,
                        "spotify_release_date": release_date[:10] if release_date else "",
                        "spotify_match_score": str(score),
                    }

    if not best:
        return {
            "spotify_verified": "No",
            "spotify_track_id": "",
            "spotify_matched_title": "",
            "spotify_matched_artist": "",
            "spotify_matched_album": "",
            "spotify_release_date": "",
            "spotify_match_score": "0",
        }
    return best


def itunes_search(s: requests.Session, title: str, artist: str) -> dict[str, Any] | None:
    try:
        response = s.get(
            f"https://itunes.apple.com/search?term={quote(f'{artist} {title}')}&media=music&limit=10",
            timeout=15,
        )
        if response.status_code != 200:
            return None
        return response.json()
    except requests.RequestException:
        return None


def source_file_mode(row: dict[str, str]) -> str:
    source_files = clean(row.get("Source Files")).lower()
    if "ytmusic" in source_files or "youtube and youtube music" in source_files:
        return "ytmusic_source"
    return ""


def itunes_match(row: dict[str, str], s: requests.Session) -> dict[str, str]:
    row_title = clean(row.get("Title"))
    row_artist = clean(row.get("Artist"))
    row_album = clean(row.get("Album"))
    title_candidates = parse_title_candidates(row)
    artist_candidates = parse_artist_candidates(row)

    best: dict[str, str] | None = None
    best_score = -1

    for title in title_candidates:
        for artist in artist_candidates:
            payload = itunes_search(s, title, artist)
            if not payload:
                continue
            for result in payload.get("results", []):
                result_title = clean(result.get("trackName"))
                result_artist = clean(result.get("artistName"))
                collection = clean(result.get("collectionName"))
                release_date = clean(result.get("releaseDate"))

                title_score = 0
                if normalize(result_title) == normalize(title):
                    title_score += 6
                elif normalize(title) in normalize(result_title) or normalize(result_title) in normalize(title):
                    title_score += 4

                artist_score = 0
                if normalize(result_artist) == normalize(artist):
                    artist_score += 6
                elif normalize(artist) in normalize(result_artist):
                    artist_score += 4

                album_score = 0
                if row_album and normalize(row_album) == normalize(collection):
                    album_score += 2

                score = title_score + artist_score + album_score
                if score > best_score:
                    best_score = score
                    best = {
                        "secondary_service": "iTunes",
                        "secondary_verified": "Yes" if score >= 10 else "No",
                        "secondary_track_id": clean(result.get("trackId")),
                        "secondary_matched_title": result_title,
                        "secondary_matched_artist": result_artist,
                        "secondary_matched_album": collection,
                        "secondary_release_date": release_date[:10] if release_date else "",
                        "secondary_match_score": str(score),
                    }

    if not best:
        return {
            "secondary_service": "iTunes",
            "secondary_verified": "No",
            "secondary_track_id": "",
            "secondary_matched_title": "",
            "secondary_matched_artist": "",
            "secondary_matched_album": "",
            "secondary_release_date": "",
            "secondary_match_score": "0",
        }
    return best


def verify_row(
    row: dict[str, str],
    s: requests.Session,
    token: str | None,
    max_retry_after: int,
    spotify_cache: dict[tuple[str, str], dict[str, str]],
    itunes_cache: dict[tuple[str, str], dict[str, str]],
) -> dict[str, str]:
    spotify_track_id = clean(row.get("Spotify Track ID"))
    spotify_mode = ""
    spotify = {
        "spotify_verified": "No",
        "spotify_track_id": spotify_track_id,
        "spotify_matched_title": "",
        "spotify_matched_artist": "",
        "spotify_matched_album": "",
        "spotify_release_date": "",
        "spotify_match_score": "0",
    }
    if spotify_track_id:
        track = spotify_track_by_id(s, token, spotify_track_id, max_retry_after)
        if track:
            track_name = clean(track.get("name"))
            track_artists = [clean(a.get("name")) for a in track.get("artists", [])]
            album = track.get("album", {}) or {}
            spotify = {
                "spotify_verified": "Yes"
                if normalize(track_name) == normalize(row.get("Base Title") or row.get("Title"))
                or normalize(track_name) == normalize(row.get("Title"))
                else "No",
                "spotify_track_id": spotify_track_id,
                "spotify_matched_title": track_name,
                "spotify_matched_artist": ", ".join(track_artists),
                "spotify_matched_album": clean(album.get("name")),
                "spotify_release_date": clean(album.get("release_date"))[:10],
                "spotify_match_score": "12" if normalize(track_name) in {normalize(row.get("Base Title")), normalize(row.get("Title"))} else "8",
            }
            spotify_mode = "spotify_id_check"
    if spotify_mode == "":
        existing_spotify_flag = clean(row.get("Spotify Verified")).lower() == "yes"
        if existing_spotify_flag:
            spotify = {
                "spotify_verified": "Yes",
                "spotify_track_id": spotify_track_id,
                "spotify_matched_title": clean(row.get("Base Title") or row.get("Title")),
                "spotify_matched_artist": clean(row.get("Artist")),
                "spotify_matched_album": clean(row.get("Album")),
                "spotify_release_date": clean(row.get("Year")),
                "spotify_match_score": "existing",
            }
            spotify_mode = "spotify_existing_flag"
        else:
            spotify_key = (normalize(row.get("Base Title") or row.get("Title")), normalize(row.get("Artist")))
            if spotify_key not in spotify_cache:
                spotify_cache[spotify_key] = spotify_match(row, s, token, max_retry_after)
            spotify = spotify_cache[spotify_key]
            spotify_mode = "spotify_search"

    secondary_mode = source_file_mode(row)
    itunes = {
        "secondary_service": "iTunes" if secondary_mode != "ytmusic_source" else "YouTube Music",
        "secondary_verified": "No",
        "secondary_track_id": "",
        "secondary_matched_title": "",
        "secondary_matched_artist": "",
        "secondary_matched_album": "",
        "secondary_release_date": "",
        "secondary_match_score": "0",
    }
    if secondary_mode == "ytmusic_source":
        itunes["secondary_verified"] = "Yes"
        itunes["secondary_match_score"] = "source"
    elif clean(row.get("iTunes Verified")).lower() == "yes":
        itunes["secondary_verified"] = "Yes"
        itunes["secondary_matched_title"] = clean(row.get("Base Title") or row.get("Title"))
        itunes["secondary_matched_artist"] = clean(row.get("Artist"))
        itunes["secondary_matched_album"] = clean(row.get("Album"))
        itunes["secondary_release_date"] = clean(row.get("Year"))
        itunes["secondary_match_score"] = "existing"
        secondary_mode = "itunes_existing_flag"
    else:
        itunes_key = (normalize(row.get("Base Title") or row.get("Title")), normalize(row.get("Artist")))
        if itunes_key not in itunes_cache:
            itunes_cache[itunes_key] = itunes_match(row, s)
        itunes = itunes_cache[itunes_key]
        secondary_mode = "itunes_search"

    verified = spotify.get("spotify_verified") == "Yes" and itunes.get("secondary_verified") == "Yes"
    status = "Verified" if verified else "Needs Review"
    return {
        **row,
        **spotify,
        **itunes,
        "spotify_check_mode": spotify_mode,
        "secondary_check_mode": secondary_mode,
        "verification_status": status,
        "verified_at_utc": utc_now_iso() if verified else "",
    }


def ensure_columns(headers: list[str]) -> list[str]:
    extras = [
        "spotify_verified",
        "spotify_track_id",
        "spotify_matched_title",
        "spotify_matched_artist",
        "spotify_matched_album",
        "spotify_release_date",
        "spotify_match_score",
        "spotify_check_mode",
        "secondary_service",
        "secondary_verified",
        "secondary_track_id",
        "secondary_matched_title",
        "secondary_matched_artist",
        "secondary_matched_album",
        "secondary_release_date",
        "secondary_match_score",
        "secondary_check_mode",
        "verification_status",
        "verified_at_utc",
    ]
    for field in extras:
        if field not in headers:
            headers.append(field)
    return headers


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Verify original songs against Spotify and iTunes.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--start", type=int, default=0, help="Zero-based start row index.")
    parser.add_argument("--stop", type=int, default=0, help="Zero-based stop row index (exclusive); 0 means all rows.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum rows to process; 0 means no limit.")
    parser.add_argument("--max-retry-after", type=int, default=60)
    args = parser.parse_args()

    with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = ensure_columns(list(reader.fieldnames or []))
        rows = [dict(row) for row in reader]

    s = session()
    token = spotify_token(s, args.log)

    start = max(0, args.start)
    stop = len(rows) if args.stop <= 0 else min(len(rows), args.stop)
    if stop < start:
        raise ValueError("--stop must be greater than or equal to --start")

    verified_rows: list[dict[str, str]] = []
    checked = verified = 0
    spotify_cache: dict[tuple[str, str], dict[str, str]] = {}
    itunes_cache: dict[tuple[str, str], dict[str, str]] = {}

    for row in rows[start:stop]:
        if args.limit and checked >= args.limit:
            break
        checked += 1
        matched = verify_row(row, s, token, args.max_retry_after, spotify_cache, itunes_cache)
        if matched.get("verification_status") == "Verified":
            verified += 1
        verified_rows.append(matched)
        if checked % 250 == 0:
            log(args.log, f"Progress checked={checked}; verified={verified}; cached_spotify={len(spotify_cache)}; cached_itunes={len(itunes_cache)}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_header = not args.output.exists() or start == 0
    with args.output.open("a" if args.output.exists() and start > 0 else "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(verified_rows)

    log(args.log, f"Checked={checked}; verified={verified}; output_rows={len(verified_rows)}; start={start}; stop={stop}")
    print(f"CHECKED\t{checked}")
    print(f"VERIFIED\t{verified}")
    print(f"OUTPUT\t{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

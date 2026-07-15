#!/usr/bin/env python3
"""Verify YouTube Music Takeout rows against Spotify and iTunes.

This builds a reviewable canonical CSV for Takeout rows with title/artist
metadata, preferring conservative matches and keeping unmatched rows separate.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scripts.verification_pass import spotify_token
from src.normalization import normalize_display_text


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_DIR / "data" / "exports" / "codex" / "youtube_music_playlist_videos_deduped.csv"
DEFAULT_OUTPUT = PROJECT_DIR / "data" / "exports" / "codex" / "youtube_music_takeout_verified.csv"
DEFAULT_UNMATCHED = PROJECT_DIR / "data" / "exports" / "codex" / "youtube_music_takeout_unmatched.csv"
DEFAULT_SUMMARY = PROJECT_DIR / "data" / "exports" / "codex" / "youtube_music_takeout_verification_summary.json"
DEFAULT_CACHE = PROJECT_DIR / "data" / "exports" / "codex" / "youtube_music_takeout_verification_cache.json"
DEFAULT_LOG = PROJECT_DIR / "data" / "logs" / "youtube_music_takeout_verification.log"
MIN_MATCH_SCORE = 0.9

_thread_local = threading.local()


NOISE_TITLE_TOKENS = (
    "official",
    "video",
    "lyric",
    "tutorial",
    "channel",
    "hd",
    "4k",
    "remaster",
    "remastered",
    "audio",
    "preview",
    "playlist",
    "topic",
)


@dataclass(frozen=True)
class Candidate:
    title: str
    artist: str
    note: str


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def strip_noise_parenthetical(match: re.Match[str]) -> str:
    text = match.group(1)
    if any(tok in text.lower() for tok in NOISE_TITLE_TOKENS):
        return " "
    return f" {text} "


def normalize_for_match(value: object) -> str:
    value = clean(value).lower()
    value = value.replace("&", " and ")
    value = value.replace("\u2019", "'")
    value = re.sub(r"\b(feat|featuring|ft)\.?\b.*$", "", value)
    value = re.sub(r"\[[^\]]*\]", " ", value)
    value = re.sub(r"\(([^)]*)\)", strip_noise_parenthetical, value)
    value = re.sub(r"\b(the|a|an)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_title_for_match(value: object) -> str:
    value = clean(value).lower()
    value = re.sub(r"\s*[-\u2013\u2014]\s*(?:radio edit|edit|live|remaster(?:ed)?|remix|acoustic|instrumental|mono|stereo)\b.*$", "", value)
    value = re.sub(r"\s*\(([^)]*(?:radio edit|edit|live|remaster(?:ed)?|remix|acoustic|instrumental|mono|stereo)[^)]*)\)", " ", value)
    value = re.sub(r"\s*\[[^\]]*(?:radio edit|edit|live|remaster(?:ed)?|remix|acoustic|instrumental|mono|stereo)[^\]]*\]", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value.replace("&", " and ").replace("\u2019", "'"))
    return re.sub(r"\s+", " ", value).strip()


def similarity(left: object, right: object) -> float:
    left_norm = normalize_for_match(left)
    right_norm = normalize_for_match(right)
    if not left_norm or not right_norm:
        return 0.0
    return difflib.SequenceMatcher(None, left_norm, right_norm).ratio()


def title_similarity(left: object, right: object) -> float:
    left_core = normalize_title_for_match(left)
    right_core = normalize_title_for_match(right)
    if not left_core or not right_core:
        return 0.0
    if left_core == right_core:
        return 1.0
    if left_core in right_core or right_core in left_core:
        return 0.99
    return difflib.SequenceMatcher(None, left_core, right_core).ratio()


def session() -> requests.Session:
    current = requests.Session()
    retry = Retry(connect=3, read=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    current.mount("http://", adapter)
    current.mount("https://", adapter)
    return current


def _worker_session():
    current = getattr(_thread_local, "session", None)
    if current is None:
        current = session()
        _thread_local.session = current
    return current


def query_spotify(s: requests.Session, token: str, title: str, artist: str) -> list[dict[str, str]]:
    query = f"track:{title}"
    if artist:
        query = f"{query} artist:{artist}"
    response = s.get(
        "https://api.spotify.com/v1/search",
        params={"q": query, "type": "track", "limit": 5},
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if response.status_code != 200:
        return []
    results: list[dict[str, str]] = []
    for item in response.json().get("tracks", {}).get("items", []):
        artist_names = ", ".join(artist.get("name", "") for artist in item.get("artists", []))
        album = item.get("album", {})
        release_date = album.get("release_date", "")
        year = release_date[:4] if re.match(r"^\d{4}", release_date or "") else ""
        results.append(
            {
                "service": "Spotify",
                "title": item.get("name", ""),
                "artist": artist_names,
                "album": album.get("name", ""),
                "release_date": release_date,
                "year": year,
                "duration_ms": str(item.get("duration_ms", "") or ""),
                "track_id": item.get("id", ""),
                "url": item.get("external_urls", {}).get("spotify", ""),
            }
        )
    return results


def query_itunes(s: requests.Session, title: str, artist: str) -> list[dict[str, str]]:
    term = f"{artist} {title}".strip() if artist else title
    response = s.get(
        "https://itunes.apple.com/search",
        params={"term": term, "media": "music", "limit": 5},
        timeout=15,
    )
    if response.status_code != 200:
        return []
    results: list[dict[str, str]] = []
    for item in response.json().get("results", []):
        if item.get("wrapperType") != "track":
            continue
        release_date = item.get("releaseDate", "")
        year = release_date[:4] if re.match(r"^\d{4}", release_date or "") else ""
        results.append(
            {
                "service": "iTunes",
                "title": item.get("trackName", ""),
                "artist": item.get("artistName", ""),
                "album": item.get("collectionName", ""),
                "genre": item.get("primaryGenreName", ""),
                "release_date": release_date,
                "year": year,
                "duration_ms": str(item.get("trackTimeMillis", "") or ""),
                "track_id": str(item.get("trackId", "") or ""),
                "url": item.get("trackViewUrl", ""),
            }
        )
    return results


def clean_title(text: str) -> str:
    text = clean(text)
    text = re.sub(r"\s*\[[^\]]*(?:official|video|lyric|channel|topic|hd|4k|audio|preview)[^\]]*\]", "", text, flags=re.I)
    text = re.sub(r"\s*\(([^)]*(?:official|video|lyric|channel|topic|hd|4k|audio|preview)[^)]*)\)", "", text, flags=re.I)
    text = re.sub(r"\s*[-\u2013\u2014]\s*(?:official|video|lyric|audio)\b.*$", "", text, flags=re.I)
    text = re.sub(r"\s*\|\s*(?:official|video|lyric|audio|channel|topic).*$", "", text, flags=re.I)
    text = re.sub(r"\s+\#\S+.*$", "", text)
    return clean(text)


def clean_artist(text: str) -> str:
    text = clean(text)
    text = re.sub(r"\s*\|\s*.*$", "", text)
    text = re.sub(r"\s*\(.*?(?:official|video|channel|topic|music|remix).*$", "", text, flags=re.I)
    text = re.sub(r"\s+(?:actual life|junos 365 sessions|disney channel animation|volume \d+|official|topic).*$", "", text, flags=re.I)
    return clean(text)


def split_title_pairs(title: str) -> list[tuple[str, str, str]]:
    pairs: list[tuple[str, str, str]] = []
    title = clean(title)
    for sep in [" - ", " | ", " : "]:
        if sep not in title:
            continue
        left, right = [clean(part) for part in title.split(sep, 1)]
        if left and right:
            pairs.append((left, right, f"split:{sep}:left=artist"))
            pairs.append((right, left, f"split:{sep}:left=title"))
    feat_match = re.search(r"\s+(?:feat\.?|featuring|ft\.?)(?:\s+|\b)", title, flags=re.I)
    if feat_match:
        left = clean(title[: feat_match.start()])
        right = clean(title[feat_match.end() :])
        if left and right:
            pairs.append((left, right, "feat_split"))
            pairs.append((right, left, "feat_split_reversed"))
    return pairs


def title_candidates(row: dict[str, str]) -> list[Candidate]:
    raw_title = clean(row.get("Title"))
    raw_artist = clean(row.get("Artist"))
    cleaned_title = clean_title(raw_title)
    cleaned_artist = clean_artist(raw_artist)
    candidates: list[Candidate] = []

    def add(title: str, artist: str, note: str) -> None:
        title = clean(title)
        artist = clean(artist)
        if not title:
            return
        candidate = Candidate(title=title, artist=artist, note=note)
        if candidate not in candidates:
            candidates.append(candidate)

    add(cleaned_title, cleaned_artist, "current_cleaned")
    add(raw_title, cleaned_artist, "raw_title_cleaned_artist")
    add(cleaned_title, raw_artist, "cleaned_title_raw_artist")

    for title_part, artist_part, note in split_title_pairs(raw_title):
        add(clean_title(title_part), clean_artist(artist_part), note)
        add(clean_title(title_part), artist_part, f"{note}_artist_raw")
        add(title_part, clean_artist(artist_part), f"{note}_title_raw")

    if cleaned_title != raw_title:
        add(cleaned_title, cleaned_artist, "title_noise_stripped")

    return candidates


def best_match(query: Candidate, results: Iterable[dict[str, str]]) -> tuple[dict[str, str] | None, float]:
    best: dict[str, str] | None = None
    best_score = 0.0
    for result in results:
        title_score = title_similarity(query.title, result.get("title", ""))
        if query.artist:
            query_artist_norm = normalize_for_match(query.artist)
            result_artist_norm = normalize_for_match(result.get("artist", ""))
            artist_score = similarity(query.artist, result.get("artist", ""))
            if query_artist_norm and result_artist_norm:
                if query_artist_norm == result_artist_norm:
                    artist_score = 1.0
                elif query_artist_norm in result_artist_norm or result_artist_norm in query_artist_norm:
                    artist_score = max(artist_score, 0.95)
        else:
            artist_score = 0.5
        score = (0.72 * title_score) + (0.28 * artist_score)
        if title_score > 0.97:
            score += 0.04
        if artist_score > 0.9:
            score += 0.03
        if query.artist and normalize_for_match(query.artist) == normalize_for_match(result.get("artist", "")):
            score += 0.05
        if score > best_score:
            best = result
            best_score = min(score, 1.0)
    return best, best_score


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: normalize_display_text(value) for key, value in row.items()})


def load_cache(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_cache(path: Path, cache: dict[str, dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, indent=2, ensure_ascii=False, sort_keys=True)


def _normalize_result_text(value: object) -> str:
    return normalize_for_match(value)


def _choose_metadata(
    candidate: Candidate,
    spotify_results: list[dict[str, str]],
    itunes_results: list[dict[str, str]],
) -> dict[str, str] | None:
    spotify_best, spotify_score = best_match(candidate, spotify_results)
    itunes_best, itunes_score = best_match(candidate, itunes_results)

    selected: dict[str, str] | None = None
    selected_service = ""
    selected_score = 0.0

    if spotify_best and (spotify_score >= itunes_score or not itunes_best):
        selected = spotify_best
        selected_service = "Spotify"
        selected_score = spotify_score
    if itunes_best and itunes_score > selected_score:
        selected = itunes_best
        selected_service = "iTunes"
        selected_score = itunes_score

    if not selected:
        return None

    metadata_source = selected_service
    genre = selected.get("genre", "")

    if spotify_best and itunes_best:
        spotify_text = (
            _normalize_result_text(spotify_best.get("title")),
            _normalize_result_text(spotify_best.get("artist")),
        )
        itunes_text = (
            _normalize_result_text(itunes_best.get("title")),
            _normalize_result_text(itunes_best.get("artist")),
        )
        if spotify_text == itunes_text:
            metadata_source = "Spotify+iTunes"
            if not genre:
                genre = itunes_best.get("genre", "")

    if selected_service == "Spotify" and itunes_best and not genre:
        if (
            _normalize_result_text(selected.get("title")) == _normalize_result_text(itunes_best.get("title"))
            and _normalize_result_text(selected.get("artist")) == _normalize_result_text(itunes_best.get("artist"))
        ):
            genre = itunes_best.get("genre", "")
            metadata_source = "Spotify+iTunes"

    if selected_service == "iTunes" and spotify_best:
        if (
            _normalize_result_text(selected.get("title")) == _normalize_result_text(spotify_best.get("title"))
            and _normalize_result_text(selected.get("artist")) == _normalize_result_text(spotify_best.get("artist"))
        ):
            metadata_source = "Spotify+iTunes"

    release_date = selected.get("release_date", "")
    year = selected.get("year", "")
    if not year and release_date[:4].isdigit():
        year = release_date[:4]

    return {
        "title": clean(selected.get("title")),
        "artist": clean(selected.get("artist")),
        "album": clean(selected.get("album")),
        "year": clean(year),
        "genre": clean(genre),
        "metadata_source": metadata_source,
        "match_score": f"{selected_score:.3f}",
        "spotify_track_id": clean(selected.get("track_id")) if selected_service == "Spotify" else clean(spotify_best.get("track_id")) if spotify_best else "",
        "spotify_url": clean(selected.get("url")) if selected_service == "Spotify" else clean(spotify_best.get("url")) if spotify_best else "",
        "itunes_track_id": clean(selected.get("track_id")) if selected_service == "iTunes" else clean(itunes_best.get("track_id")) if itunes_best else "",
        "itunes_url": clean(selected.get("url")) if selected_service == "iTunes" else clean(itunes_best.get("url")) if itunes_best else "",
    }


def verify_row(row: dict[str, str], token: str | None) -> tuple[dict[str, str], dict[str, str] | None]:
    source_title = clean(row.get("title"))
    source_artist = clean(row.get("artist"))
    source_album = clean(row.get("album"))
    source_year = clean(row.get("year"))
    source_genre = clean(row.get("genre"))

    lookup_row = {"Title": source_title, "Artist": source_artist}
    best_match_row: dict[str, str] | None = None
    best_score = 0.0
    best_note = ""

    for candidate in title_candidates(lookup_row):
        session = _worker_session()
        itunes_results = query_itunes(session, candidate.title, candidate.artist)
        itunes_best, itunes_score = best_match(candidate, itunes_results)
        if itunes_best and itunes_score >= MIN_MATCH_SCORE:
            chosen = _choose_metadata(candidate, [], itunes_results)
            if chosen and itunes_score > best_score:
                best_match_row = chosen
                best_score = itunes_score
                best_note = candidate.note
            if best_score >= 0.97:
                break
            continue

        if token:
            spotify_results = query_spotify(session, token, candidate.title, candidate.artist)
            spotify_best, spotify_score = best_match(candidate, spotify_results)
            if spotify_best and spotify_score >= MIN_MATCH_SCORE:
                chosen = _choose_metadata(candidate, spotify_results, [])
                if chosen and spotify_score > best_score:
                    best_match_row = chosen
                    best_score = spotify_score
                    best_note = candidate.note
                if best_score >= 0.97:
                    break

    verified = {
        "videoID": clean(row.get("videoID")),
        "title": source_title,
        "artist": source_artist,
        "year": source_year,
        "album": source_album,
        "genre": source_genre,
        "metadata_source": "",
        "match_score": "",
        "match_status": "unmatched",
        "source_title": source_title,
        "source_artist": source_artist,
        "source_year": source_year,
        "source_album": source_album,
        "source_genre": source_genre,
        "source_release_date": clean(row.get("release_date")),
        "source_upload_date": clean(row.get("upload_date")),
        "duration_seconds": clean(row.get("duration_seconds")),
        "channel": clean(row.get("channel")),
        "uploader": clean(row.get("uploader")),
        "categories": clean(row.get("categories")),
        "tags": clean(row.get("tags")),
        "description": clean(row.get("description")),
        "webpage_url": clean(row.get("webpage_url")),
        "metadata_lookup_url": clean(row.get("metadata_lookup_url")),
        "metadata_lookup_status": clean(row.get("metadata_lookup_status")),
        "source_playlist_count": clean(row.get("source_playlist_count")),
        "source_playlists": clean(row.get("source_playlists")),
        "source_files": clean(row.get("source_files")),
        "first_seen_playlist_video_creation_timestamp": clean(row.get("first_seen_playlist_video_creation_timestamp")),
        "last_seen_playlist_video_creation_timestamp": clean(row.get("last_seen_playlist_video_creation_timestamp")),
        "occurrence_count": clean(row.get("occurrence_count")),
        "verified_candidate_note": best_note,
    }

    if best_match_row:
        verified.update(best_match_row)
        verified["match_status"] = "matched"
        if not verified["year"]:
            verified["year"] = clean(best_match_row.get("year"))
        if not verified["album"]:
            verified["album"] = clean(best_match_row.get("album"))
        if not verified["genre"]:
            verified["genre"] = clean(best_match_row.get("genre"))

    return verified, None if best_match_row else {
        "videoID": verified["videoID"],
        "title": verified["title"],
        "artist": verified["artist"],
        "year": verified["year"],
        "album": verified["album"],
        "genre": verified["genre"],
        "source_playlists": verified["source_playlists"],
        "metadata_lookup_status": verified["metadata_lookup_status"],
        "match_status": verified["match_status"],
    }


def build_verified_takeout_export(
    input_csv: Path,
    output_csv: Path,
    unmatched_csv: Path,
    summary_path: Path,
    cache_path: Path | None = None,
    *,
    log_path: Path = DEFAULT_LOG,
    workers: int = 6,
) -> dict[str, str]:
    rows = read_rows(input_csv)
    titled_rows = [row for row in rows if clean(row.get("title")) and clean(row.get("artist"))]

    cache: dict[str, dict[str, str]] = {}
    if cache_path:
        cache = load_cache(cache_path)

    pending = [row for row in titled_rows if clean(row.get("videoID")) not in cache]
    unmatched_rows: list[dict[str, str]] = []
    verified_rows_by_video_id: dict[str, dict[str, str]] = {}

    token = spotify_token(_worker_session(), log_path)

    def run(row: dict[str, str]) -> tuple[str, dict[str, str], dict[str, str] | None]:
        video_id = clean(row.get("videoID"))
        verified, unmatched = verify_row(row, token)
        return video_id, verified, unmatched

    if pending:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(run, row): clean(row.get("videoID")) for row in pending}
            for future in as_completed(futures):
                video_id, verified, unmatched = future.result()
                if verified.get("match_status") == "matched":
                    verified_rows_by_video_id[video_id] = verified
                if unmatched:
                    unmatched_rows.append(unmatched)
        if cache_path:
            cache.update(verified_rows_by_video_id)
            save_cache(cache_path, cache)

    for row in titled_rows:
        video_id = clean(row.get("videoID"))
        if video_id in verified_rows_by_video_id:
            continue
        if video_id in cache:
            cached_row = cache[video_id]
            if cached_row.get("match_status") == "matched":
                verified_rows_by_video_id[video_id] = cached_row
            continue

    verified_rows = [verified_rows_by_video_id[clean(row.get("videoID"))] for row in titled_rows if clean(row.get("videoID")) in verified_rows_by_video_id]

    fieldnames = [
        "videoID",
        "title",
        "artist",
        "year",
        "album",
        "genre",
        "metadata_source",
        "match_score",
        "match_status",
        "spotify_track_id",
        "spotify_url",
        "itunes_track_id",
        "itunes_url",
        "source_title",
        "source_artist",
        "source_year",
        "source_album",
        "source_genre",
        "source_release_date",
        "source_upload_date",
        "duration_seconds",
        "channel",
        "uploader",
        "categories",
        "tags",
        "description",
        "webpage_url",
        "metadata_lookup_url",
        "metadata_lookup_status",
        "source_playlist_count",
        "source_playlists",
        "source_files",
        "first_seen_playlist_video_creation_timestamp",
        "last_seen_playlist_video_creation_timestamp",
        "occurrence_count",
        "verified_candidate_note",
    ]
    write_csv(output_csv, fieldnames, verified_rows)
    write_csv(
        unmatched_csv,
        ["videoID", "title", "artist", "year", "album", "genre", "source_playlists", "metadata_lookup_status", "match_status"],
        unmatched_rows,
    )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_csv": str(input_csv),
        "output_csv": str(output_csv),
        "unmatched_csv": str(unmatched_csv),
        "cache_path": str(cache_path) if cache_path else "",
        "rows_seen": len(rows),
        "rows_with_title_artist": len(titled_rows),
        "rows_verified": len(verified_rows),
        "rows_unmatched": len(unmatched_rows),
        "spotify_enabled": False,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify YouTube Music Takeout metadata against Spotify and iTunes.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--unmatched", type=Path, default=DEFAULT_UNMATCHED)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--write", action="store_true", help="Write the verified metadata export.")
    args = parser.parse_args()

    if not args.write:
        print("verify-youtube-music-takeout: dry-run=True")
        print(f"Input: {args.input}")
        print(f"Output: {args.output}")
        print(f"Unmatched: {args.unmatched}")
        print("DRY RUN: Would verify title/artist rows against Spotify and iTunes and write a canonical metadata CSV.")
        return 0

    summary = build_verified_takeout_export(
        args.input,
        args.output,
        args.unmatched,
        args.summary,
        args.cache,
        log_path=DEFAULT_LOG,
        workers=args.workers,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Clean and verify questionable SongDB rows.

This script reads the raw rows from basket/questionable.csv, attempts conservative
title/artist cleanup, verifies matches against Spotify and iTunes, and writes a
reviewable candidate plus skip report. Use --write only after reviewing the
generated actions and backup path.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MAIN = PROJECT_DIR / "data" / "processed" / "Main_Song_Database.csv"
DEFAULT_QUESTIONABLE = PROJECT_DIR / "basket" / "questionable.csv"
DEFAULT_EXPORT_DIR = PROJECT_DIR / "data" / "exports" / "codex" / "questionable_cleanup"
DEFAULT_BACKUP_DIR = PROJECT_DIR / "data" / "backups" / "questionable_cleanup"

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
    value = value.replace("’", "'")
    value = re.sub(r"\b(feat|featuring|ft)\.?\b.*$", "", value)
    value = re.sub(r"\[[^\]]*\]", " ", value)
    value = re.sub(r"\(([^)]*)\)", strip_noise_parenthetical, value)
    value = re.sub(r"\b(the|a|an)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_title_for_match(value: object) -> str:
    value = clean(value).lower()
    value = re.sub(r"\s*[-–—]\s*(?:radio edit|edit|live|remaster(?:ed)?|remix|acoustic|instrumental|mono|stereo)\b.*$", "", value)
    value = re.sub(r"\s*\(([^)]*(?:radio edit|edit|live|remaster(?:ed)?|remix|acoustic|instrumental|mono|stereo)[^)]*)\)", " ", value)
    value = re.sub(r"\s*\[[^\]]*(?:radio edit|edit|live|remaster(?:ed)?|remix|acoustic|instrumental|mono|stereo)[^\]]*\]", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value.replace("&", " and ").replace("’", "'"))
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


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [dict(row) for row in reader]
        return list(reader.fieldnames or []), rows


def read_raw_rows(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [row for row in csv.reader(f)]


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def session() -> requests.Session:
    s = requests.Session()
    retry = Retry(connect=3, read=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


def spotify_token(s: requests.Session) -> str | None:
    client_id = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None
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
    if response.status_code != 200:
        return None
    return response.json().get("access_token")


def query_spotify(s: requests.Session, token: str, title: str, artist: str) -> list[dict[str, str]]:
    q = f"track:{title}"
    if artist:
        q = f"{q} artist:{artist}"
    response = s.get(
        "https://api.spotify.com/v1/search",
        params={"q": q, "type": "track", "limit": 5},
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if response.status_code != 200:
        return []
    items = response.json().get("tracks", {}).get("items", [])
    results: list[dict[str, str]] = []
    for item in items:
        artist_names = ", ".join(a.get("name", "") for a in item.get("artists", []))
        album = item.get("album", {})
        release_date = album.get("release_date", "")
        year = ""
        if re.match(r"^\d{4}", release_date or ""):
            year = release_date[:4]
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
        year = ""
        if re.match(r"^\d{4}", release_date or ""):
            year = release_date[:4]
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
    text = re.sub(r"\s*[-–—]\s*(?:official|video|lyric|audio)\b.*$", "", text, flags=re.I)
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


def is_suspicious_row(row: dict[str, str]) -> bool:
    title = clean(row.get("Title"))
    artist = clean(row.get("Artist"))
    return (
        clean_title(title) != title
        or clean_artist(artist) != artist
        or " - " in title
        or " | " in title
        or bool(re.search(r"\b(feat\.?|featuring|ft\.?)\b", title, flags=re.I))
        or any(tok in title.lower() for tok in NOISE_TITLE_TOKENS)
        or any(
            tok in artist.lower()
            for tok in [
                "actual life",
                "junos 365 sessions",
                "disney channel animation",
                "volume ",
                "official",
                "topic",
            ]
        )
    )


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


def source_verification(row: dict[str, str]) -> str:
    source = clean(row.get("Source Files"))
    if "YouTube and YouTube Music" in source or "YTMusic" in source:
        return "YouTube Music source file"
    if "YouTube" in source:
        return "YouTube source file"
    return ""


def song_key(title: object, artist: object) -> tuple[str, str]:
    return normalize_for_match(title), normalize_for_match(artist)


def choose_hit(
    q_row: dict[str, str],
    matches: list[int],
    main_rows: list[dict[str, str]],
) -> int:
    if len(matches) == 1:
        return matches[0]

    q_album = normalize_for_match(q_row.get("Album"))
    q_duration = normalize_for_match(q_row.get("Duration"))
    q_source = normalize_for_match(q_row.get("Source Files"))

    best_index = matches[0]
    best_score = -1
    for index in matches:
        row = main_rows[index]
        score = 0
        if q_album and normalize_for_match(row.get("Album")) == q_album:
            score += 2
        if q_duration and normalize_for_match(row.get("Duration")) == q_duration:
            score += 1
        if q_source and normalize_for_match(row.get("Source Files")) == q_source:
            score += 1
        if score > best_score:
            best_index = index
            best_score = score
    return best_index


def write_backup(main_csv: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = DEFAULT_BACKUP_DIR / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / main_csv.name
    shutil.copy2(main_csv, backup_path)
    return backup_path


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Clean and verify questionable SongDB rows.")
    parser.add_argument("--main", type=Path, default=DEFAULT_MAIN)
    parser.add_argument("--questionable", type=Path, default=DEFAULT_QUESTIONABLE)
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    parser.add_argument("--write", action="store_true", help="Write the cleaned rows back to the main database.")
    parser.add_argument("--limit", type=int, default=0, help="Process at most this many questionable rows.")
    parser.add_argument("--all", action="store_true", help="Process all rows instead of only obviously mangled ones.")
    args = parser.parse_args()

    main_headers, main_rows = read_csv(args.main)
    question_rows = read_raw_rows(args.questionable)
    if not question_rows:
        print(json.dumps({"error": "no_questionable_rows"}, indent=2))
        return 1

    main_index: dict[tuple[str, str], list[int]] = {}
    for index, row in enumerate(main_rows):
        key = song_key(row.get("Title"), row.get("Artist"))
        main_index.setdefault(key, []).append(index)

    s = session()
    token = spotify_token(s)

    candidate_rows = [dict(row) for row in main_rows]
    actions: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    stats = {
        "rows_seen": 0,
        "rows_matched": 0,
        "rows_updated": 0,
        "spotify_matches": 0,
        "itunes_matches": 0,
        "ytmusic_verified": 0,
    }

    for q_index, q_values in enumerate(question_rows, start=1):
        if args.limit and stats["rows_seen"] >= args.limit:
            break
        stats["rows_seen"] += 1
        raw_values = list(q_values)
        q_row = {header: (raw_values[i] if i < len(raw_values) else "") for i, header in enumerate(main_headers)}
        matches = main_index.get(song_key(q_row.get("Title"), q_row.get("Artist")), [])
        if not matches:
            skipped.append(
                {
                    "Questionable Row": str(q_index),
                    "Title": clean(raw_values[0] if len(raw_values) > 0 else ""),
                    "Artist": clean(raw_values[2] if len(raw_values) > 2 else ""),
                    "Source Files": clean(raw_values[11] if len(raw_values) > 11 else ""),
                    "Reason": "row_not_found_in_main_db",
                }
            )
            continue

        stats["rows_matched"] += 1
        if not args.all and not is_suspicious_row(q_row):
            skipped.append(
                {
                    "Questionable Row": str(q_index),
                    "Title": clean(q_row.get("Title")),
                    "Artist": clean(q_row.get("Artist")),
                    "Source Files": clean(q_row.get("Source Files")),
                    "Reason": "not_obviously_mangled",
                }
            )
            continue

        best_candidate: Candidate | None = None
        best_score = 0.0
        best_service = ""
        best_url = ""

        chosen_index = choose_hit(q_row, matches, main_rows)
        matches = [chosen_index]

        for proposal in title_candidates(q_row):
            search_results: list[dict[str, str]] = []
            if token:
                search_results.extend(query_spotify(s, token, proposal.title, proposal.artist))
            search_results.extend(query_itunes(s, proposal.title, proposal.artist))
            match, score = best_match(proposal, search_results)
            if match and score > best_score:
                best_candidate = Candidate(
                    title=match.get("title", ""),
                    artist=match.get("artist", ""),
                    note=proposal.note,
                )
                best_score = score
                best_service = match.get("service", "")
                best_url = match.get("url", "")

        source_ver = source_verification(q_row)
        if source_ver and not best_candidate:
            stats["ytmusic_verified"] += 1

        if not best_candidate or best_score < 0.88:
            skipped.append(
                {
                    "Questionable Row": str(q_index),
                    "Title": clean(q_row.get("Title")),
                    "Artist": clean(q_row.get("Artist")),
                    "Source Files": clean(q_row.get("Source Files")),
                    "Reason": f"no_high_confidence_match(score={best_score:.3f})",
                }
            )
            continue

        for match_index in matches:
            row = candidate_rows[match_index]
            before_title = clean(row.get("Title"))
            before_artist = clean(row.get("Artist"))
            before_album = clean(row.get("Album"))
            after_title = clean(best_candidate.title)
            after_artist = clean(best_candidate.artist)
            if before_title == after_title and before_artist == after_artist:
                continue
            row["Title"] = after_title
            row["Base Title"] = after_title
            if after_artist:
                row["Artist"] = after_artist
            if best_service == "Spotify":
                row["Spotify Verified"] = "Yes"
                stats["spotify_matches"] += 1
            elif best_service == "iTunes":
                row["iTunes Verified"] = "Yes"
                stats["itunes_matches"] += 1
            note = f"verified via {best_service or 'source cleanup'}"
            if source_ver:
                note = f"{source_ver}; {note}"
            if clean(row.get("Original Data")):
                if note not in row.get("Original Data", ""):
                    row["Original Data"] = f"{clean(row.get('Original Data'))} | {note}"
            else:
                row["Original Data"] = note
            actions.append(
                {
                    "Questionable Row": str(q_index),
                    "Main DB Row": str(match_index + 2),
                    "Before Title": before_title,
                    "Before Artist": before_artist,
                    "After Title": after_title,
                    "After Artist": after_artist,
                    "Before Album": before_album,
                    "After Album": clean(row.get("Album")),
                    "Service": best_service,
                    "Confidence": f"{best_score:.3f}",
                    "Source URL": best_url,
                    "Source Files": clean(q_row.get("Source Files")),
                    "Candidate Note": best_candidate.note,
                }
            )
            stats["rows_updated"] += 1

    args.export_dir.mkdir(parents=True, exist_ok=True)
    actions_csv = args.export_dir / "questionable_cleanup_actions.csv"
    skipped_csv = args.export_dir / "questionable_cleanup_skipped.csv"
    candidate_csv = args.export_dir / "questionable_cleanup_candidate.csv"
    summary_json = args.export_dir / "questionable_cleanup_summary.json"

    action_headers = [
        "Questionable Row",
        "Main DB Row",
        "Before Title",
        "Before Artist",
        "After Title",
        "After Artist",
        "Before Album",
        "After Album",
        "Service",
        "Confidence",
        "Source URL",
        "Source Files",
        "Candidate Note",
    ]
    skip_headers = ["Questionable Row", "Title", "Artist", "Source Files", "Reason"]
    write_csv(actions_csv, action_headers, actions)
    write_csv(skipped_csv, skip_headers, skipped)
    write_csv(candidate_csv, main_headers, candidate_rows)

    backup_path = ""
    if args.write:
        backup_path = str(write_backup(args.main))
        write_csv(args.main, main_headers, candidate_rows)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "main_csv": str(args.main),
        "questionable_csv": str(args.questionable),
        "candidate_csv": str(candidate_csv),
        "actions_csv": str(actions_csv),
        "skipped_csv": str(skipped_csv),
        "backup_csv": backup_path,
        "rows_seen": stats["rows_seen"],
        "rows_matched": stats["rows_matched"],
        "rows_updated": stats["rows_updated"],
        "spotify_matches": stats["spotify_matches"],
        "itunes_matches": stats["itunes_matches"],
        "ytmusic_verified": stats["ytmusic_verified"],
        "write_enabled": args.write,
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

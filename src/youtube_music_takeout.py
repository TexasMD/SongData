from __future__ import annotations

import csv
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from src.normalization import normalize_display_text


VIDEO_ID_COLUMNS = ("Video ID", "videoID", "video ID")
TIMESTAMP_COLUMNS = (
    "Playlist Video Creation Timestamp",
    "playlist video creation timestamp",
    "Timestamp",
    "timestamp",
)


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def normalize_key(value: object) -> str:
    value = clean(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[’‘`']", "", value)
    value = re.sub(r"\b(feat|featuring|ft)\.?\b.*$", "", value)
    value = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def split_playlists(value: object) -> list[str]:
    parts = re.split(r"\s*\|\s*|\s*;\s*", clean(value))
    return [part for part in (clean(part) for part in parts) if part]


def semicolon_join(values: list[str]) -> str:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        value = clean(value)
        if not value:
            continue
        key = value.lower()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return "; ".join(result)


def pick_first(mapping: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = clean(mapping.get(key))
        if value:
            return value
    return ""


def parse_year(info: dict[str, Any]) -> str:
    release_year = info.get("release_year")
    if release_year:
        return str(release_year)
    release_date = clean(info.get("release_date"))
    if len(release_date) >= 4 and release_date[:4].isdigit():
        return release_date[:4]
    upload_date = clean(info.get("upload_date"))
    if len(upload_date) >= 4 and upload_date[:4].isdigit():
        return upload_date[:4]
    return ""


@dataclass
class TakeoutEntry:
    video_id: str
    source_playlists: set[str] = field(default_factory=set)
    source_files: set[str] = field(default_factory=set)
    first_seen_timestamp: str = ""
    last_seen_timestamp: str = ""
    occurrence_count: int = 0


@dataclass
class TakeoutExportResult:
    output_csv: Path
    cache_path: Path | None
    summary: dict[str, Any]
    rows: list[dict[str, str]]


@dataclass
class RecordingMatchResult:
    membership_rows: list[dict[str, str]]
    unmatched_rows: list[dict[str, str]]


def collect_takeout_entries(input_dir: Path) -> list[TakeoutEntry]:
    entries: list[TakeoutEntry] = []
    index_by_id: dict[str, TakeoutEntry] = {}

    for csv_path in sorted(input_dir.glob("*-videos.csv")):
        playlist_name = csv_path.stem[:-7] if csv_path.stem.endswith("-videos") else csv_path.stem
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                video_id = pick_first(row, VIDEO_ID_COLUMNS)
                if not video_id:
                    continue
                timestamp = pick_first(row, TIMESTAMP_COLUMNS)

                entry = index_by_id.get(video_id)
                if entry is None:
                    entry = TakeoutEntry(
                        video_id=video_id,
                        first_seen_timestamp=timestamp,
                        last_seen_timestamp=timestamp,
                    )
                    index_by_id[video_id] = entry
                    entries.append(entry)
                entry.occurrence_count += 1
                entry.source_playlists.add(playlist_name)
                entry.source_files.add(csv_path.name)
                if timestamp and (not entry.first_seen_timestamp or timestamp < entry.first_seen_timestamp):
                    entry.first_seen_timestamp = timestamp
                if timestamp and (not entry.last_seen_timestamp or timestamp > entry.last_seen_timestamp):
                    entry.last_seen_timestamp = timestamp

    return entries


_thread_local = threading.local()


class SilentLogger:
    def debug(self, msg: str) -> None:  # noqa: D401
        pass

    def warning(self, msg: str) -> None:  # noqa: D401
        pass

    def error(self, msg: str) -> None:  # noqa: D401
        pass


def _get_ydl() -> YoutubeDL:
    ydl = getattr(_thread_local, "ydl", None)
    if ydl is None:
        ydl = YoutubeDL(
            {
                "quiet": True,
                "no_warnings": True,
                "logger": SilentLogger(),
                "skip_download": True,
                "extract_flat": False,
                "noplaylist": True,
                "socket_timeout": 20,
                "retries": 1,
            }
        )
        _thread_local.ydl = ydl
    return ydl


def fetch_video_metadata(video_id: str) -> dict[str, Any]:
    urls = [
        f"https://music.youtube.com/watch?v={video_id}",
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    last_error = ""

    for url in urls:
        try:
            info = _get_ydl().extract_info(url, download=False)
            if info:
                return normalize_metadata(video_id, info, url, "ok")
        except DownloadError as exc:
            last_error = clean(str(exc))
        except Exception as exc:  # noqa: BLE001
            last_error = clean(str(exc))

    return normalize_metadata(video_id, {}, "", f"unavailable: {last_error}" if last_error else "unavailable")


def normalize_metadata(video_id: str, info: dict[str, Any], lookup_url: str, status: str) -> dict[str, str]:
    artists_value = info.get("artists")
    artists = clean(info.get("artist")) or clean(info.get("creator")) or clean(info.get("channel"))
    if not artists and isinstance(artists_value, list):
        artists = " | ".join(clean(item) for item in artists_value if clean(item))
    elif not artists:
        artists = clean(artists_value)

    tags_value = info.get("tags")
    if isinstance(tags_value, list):
        tags = " | ".join(clean(item) for item in tags_value if clean(item))
    else:
        tags = clean(tags_value)

    categories_value = info.get("categories")
    if isinstance(categories_value, list):
        categories = " | ".join(clean(item) for item in categories_value if clean(item))
    else:
        categories = clean(categories_value)

    title = clean(info.get("track")) or clean(info.get("title"))
    album = clean(info.get("album"))
    genre = clean(info.get("genre")) or clean(info.get("genres"))
    release_date = clean(info.get("release_date"))
    upload_date = clean(info.get("upload_date"))
    duration = info.get("duration")
    description = clean(info.get("description"))
    channel = clean(info.get("channel")) or clean(info.get("uploader"))
    uploader = clean(info.get("uploader"))
    webpage_url = clean(info.get("webpage_url"))

    return {
        "videoID": normalize_display_text(video_id),
        "title": normalize_display_text(title),
        "artist": normalize_display_text(artists),
        "year": normalize_display_text(parse_year(info)),
        "album": normalize_display_text(album),
        "genre": normalize_display_text(genre),
        "release_date": normalize_display_text(release_date),
        "upload_date": normalize_display_text(upload_date),
        "duration_seconds": normalize_display_text(str(duration) if duration is not None else ""),
        "channel": normalize_display_text(channel),
        "uploader": normalize_display_text(uploader),
        "categories": normalize_display_text(categories),
        "tags": normalize_display_text(tags),
        "description": normalize_display_text(description),
        "webpage_url": normalize_display_text(webpage_url),
        "metadata_lookup_url": normalize_display_text(lookup_url),
        "metadata_lookup_status": normalize_display_text(status),
    }


def load_cache(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_cache(path: Path, cache: dict[str, dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        json.dump(cache, handle, ensure_ascii=False, indent=2, sort_keys=True)


def build_takeout_export(
    input_dir: Path,
    output_csv: Path,
    cache_path: Path | None = None,
    *,
    workers: int = 8,
    metadata_fetcher: Callable[[str], dict[str, str]] = fetch_video_metadata,
) -> TakeoutExportResult:
    entries = collect_takeout_entries(input_dir)
    cache: dict[str, dict[str, str]] = {}
    if cache_path:
        cache = load_cache(cache_path)

    pending = [entry.video_id for entry in entries if entry.video_id not in cache]
    looked_up: dict[str, dict[str, str]] = {}

    if pending:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(metadata_fetcher, video_id): video_id for video_id in pending}
            for future in as_completed(futures):
                video_id = futures[future]
                looked_up[video_id] = future.result()
        cache.update(looked_up)
        if cache_path:
            save_cache(cache_path, cache)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "videoID",
        "title",
        "artist",
        "year",
        "album",
        "genre",
        "release_date",
        "upload_date",
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
    ]

    rows: list[dict[str, str]] = []
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for entry in entries:
            metadata = cache.get(entry.video_id) or metadata_fetcher(entry.video_id)
            row = {key: "" for key in fieldnames}
            row.update(metadata)
            row.update(
                {
                    "videoID": normalize_display_text(entry.video_id),
                    "source_playlist_count": normalize_display_text(str(len(entry.source_playlists))),
                    "source_playlists": normalize_display_text(" | ".join(sorted(entry.source_playlists))),
                    "source_files": normalize_display_text(" | ".join(sorted(entry.source_files))),
                    "first_seen_playlist_video_creation_timestamp": normalize_display_text(entry.first_seen_timestamp),
                    "last_seen_playlist_video_creation_timestamp": normalize_display_text(entry.last_seen_timestamp),
                    "occurrence_count": normalize_display_text(str(entry.occurrence_count)),
                }
            )
            writer.writerow(row)
            rows.append(row)

    summary = {
        "input_dir": str(input_dir),
        "output_csv": str(output_csv),
        "cache_path": str(cache_path) if cache_path else "",
        "playlist_files": len(list(input_dir.glob("*-videos.csv"))),
        "unique_video_ids": len(entries),
        "cached_metadata_hits": len(entries) - len(pending),
        "metadata_lookups": len(pending),
        "metadata_unavailable": sum(1 for row in rows if str(row.get("metadata_lookup_status", "")).startswith("unavailable")),
    }
    return TakeoutExportResult(output_csv=output_csv, cache_path=cache_path, summary=summary, rows=rows)


def load_takeout_export(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def build_takeout_song_export(
    takeout_rows: list[dict[str, str]],
    output_csv: Path,
) -> list[dict[str, str]]:
    fieldnames = [
        "youtube music song ID",
        "title",
        "artist",
        "album",
        "year",
        "genre",
    ]

    rows: list[dict[str, str]] = []
    seen_song_ids: set[str] = set()

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for takeout_row in takeout_rows:
            song_id = clean(takeout_row.get("videoID"))
            if not song_id or song_id in seen_song_ids:
                continue
            seen_song_ids.add(song_id)

            row = {
                "youtube music song ID": normalize_display_text(song_id),
                "title": normalize_display_text(takeout_row.get("title")),
                "artist": normalize_display_text(takeout_row.get("artist")),
                "album": normalize_display_text(takeout_row.get("album")),
                "year": normalize_display_text(takeout_row.get("year")),
                "genre": normalize_display_text(takeout_row.get("genre")),
            }
            writer.writerow(row)
            rows.append(row)

    return rows


def build_recording_index(recordings: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, dict[str, str]]]:
    index: dict[tuple[str, str], dict[str, dict[str, str]]] = {}
    for row in recordings:
        recording_id = clean(row.get("Recording ID")) or clean(row.get("recording_id"))
        artist_candidates = [
            row.get("Artist", ""),
            row.get("Canonical Artist", ""),
            row.get("Original Artist", ""),
            row.get("Covering Artist", ""),
        ]
        title_candidates = [
            row.get("Title", ""),
            row.get("Canonical Title", ""),
        ]
        for title in title_candidates:
            for artist in artist_candidates:
                key = (normalize_key(title), normalize_key(artist))
                if key[0] and key[1]:
                    index.setdefault(key, {})[recording_id or f"row-{id(row)}"] = row
    return index


def match_takeout_export_to_recordings(
    takeout_rows: list[dict[str, str]],
    recordings: list[dict[str, str]],
) -> RecordingMatchResult:
    index = build_recording_index(recordings)
    membership_rows: list[dict[str, str]] = []
    unmatched_rows: list[dict[str, str]] = []

    for takeout_row in takeout_rows:
        title = clean(takeout_row.get("title"))
        artist = clean(takeout_row.get("artist"))
        key = (normalize_key(title), normalize_key(artist))
        matches = list(index.get(key, {}).values())

        if len(matches) != 1:
            unmatched_rows.append(
                {
                    "videoID": clean(takeout_row.get("videoID")),
                    "title": title,
                    "artist": artist,
                    "year": clean(takeout_row.get("year")),
                    "album": clean(takeout_row.get("album")),
                    "source_playlists": clean(takeout_row.get("source_playlists")),
                    "metadata_lookup_status": clean(takeout_row.get("metadata_lookup_status")),
                    "match_status": "ambiguous" if matches else "unmatched",
                }
            )
            continue

        recording = matches[0]
        for playlist in split_playlists(takeout_row.get("source_playlists")):
            membership_rows.append(
                {
                    "Recording ID": clean(recording.get("Recording ID")),
                    "Song ID": clean(recording.get("Song ID")),
                    "Playlist": playlist,
                    "Source": "YouTube Music Takeout",
                    "Notes": (
                        f"videoID={clean(takeout_row.get('videoID'))}; "
                        f"title={title}; artist={artist}; "
                        f"album={clean(takeout_row.get('album'))}; year={clean(takeout_row.get('year'))}"
                    ).strip(),
                }
            )

    return RecordingMatchResult(membership_rows=membership_rows, unmatched_rows=unmatched_rows)

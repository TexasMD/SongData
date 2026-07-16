from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cover_info_client import scrape_cover_info


OUTPUT_PATH = ROOT / "basket" / "coverdata_shs_ci.csv"
LOG_PATH = ROOT / "basket" / "coverdata_shs_ci.log"
HEARTBEAT_PATH = ROOT / "basket" / "coverdata_shs_ci.status.json"
USER_AGENT = "MusicDB-CoverScraper/1.0 ( Windows )"
CSV_FIELDNAMES = [
    "performing_artist",
    "title",
    "year",
    "album",
    "genre",
    "original_artist",
    "original_song_title",
    "original_album",
    "original_year",
    "secondhandsongs_artist_id",
    "secondhandsongs_title_id",
    "secondhandsongs_performance_id",
    "secondhandsongs_album_id",
    "source",
    "queried_at_utc",
    "source_url",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_line(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line, flush=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def write_heartbeat(path: Path, **payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at_utc"] = utc_now_iso()
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def clean(text: str | None) -> str:
    return " ".join((text or "").split()).strip()


def normalize(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def uri_id(value: Any) -> str:
    return str(value or "").rsplit("/", 1)[-1] if value else ""


def load_existing_keys(path: Path) -> set[tuple[str, str, str, str]]:
    keys: set[tuple[str, str, str, str]] = set()
    if not path.exists():
        return keys

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            keys.add(
                (
                    normalize(row.get("performing_artist")),
                    normalize(row.get("title")),
                    normalize(row.get("original_artist")),
                    normalize(row.get("original_song_title")),
                )
            )
    return keys


def ensure_output_header(path: Path) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=CSV_FIELDNAMES,
        )
        writer.writeheader()


def append_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    ensure_output_header(path)
    with path.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=CSV_FIELDNAMES,
        )
        writer.writerows(rows)


def merge_source_fields(row: dict[str, Any], source: str, queried_at_utc: str, source_url: str) -> dict[str, Any]:
    merged = dict(row)
    sources = [part for part in str(merged.get("source", "")).split(";") if part]
    if source not in sources:
        sources.append(source)
    times = [part for part in str(merged.get("queried_at_utc", "")).split(";") if part]
    if queried_at_utc not in times:
        times.append(queried_at_utc)
    urls = [part for part in str(merged.get("source_url", "")).split(";") if part]
    if source_url and source_url not in urls:
        urls.append(source_url)

    merged["source"] = ";".join(sources)
    merged["queried_at_utc"] = ";".join(times)
    merged["source_url"] = ";".join(urls)
    return merged


def shs_get(session: requests.Session, url: str, *, params: dict[str, Any] | None = None) -> dict[str, Any] | list[dict[str, Any]] | None:
    resp = session.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        return None
    try:
        return resp.json()
    except ValueError:
        return None


def shs_search_artist(session: requests.Session, artist: str) -> dict[str, Any] | None:
    data = shs_get(
        session,
        "https://api.secondhandsongs.com/search/artist",
        params={"commonName": artist, "pageSize": 100, "page": 1},
    )
    if not isinstance(data, dict):
        return None
    for item in data.get("resultPage") or []:
        if clean(item.get("commonName")).lower() == clean(artist).lower():
            return item
    return None


def shs_get_artist_performances(session: requests.Session, artist_id: str) -> list[dict[str, Any]]:
    data = shs_get(session, f"https://api.secondhandsongs.com/artist/{artist_id}/performances")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        result_page = data.get("resultPage")
        if isinstance(result_page, list):
            return [item for item in result_page if isinstance(item, dict)]
    return []


def shs_get_performance(session: requests.Session, performance_id: str) -> dict[str, Any] | None:
    data = shs_get(session, f"https://api.secondhandsongs.com/performance/{performance_id}")
    return data if isinstance(data, dict) else None


def shs_search_object(session: requests.Session, caption: str, *, page_size: int = 50) -> list[dict[str, Any]]:
    data = shs_get(
        session,
        "https://api.secondhandsongs.com/search/object",
        params={"caption": caption, "pageSize": page_size, "page": 1},
    )
    if not isinstance(data, dict):
        return []
    return [item for item in data.get("resultPage") or [] if isinstance(item, dict)]


def shs_search_performances(
    session: requests.Session,
    title: str,
    artist: str,
    *,
    page_size: int = 50,
) -> list[dict[str, Any]]:
    queries = [
        {"title": title, "pageSize": page_size, "page": 1},
        {"title": title, "performer": artist, "pageSize": page_size, "page": 1},
    ]
    artist_variants = []
    stripped_artist = clean(artist)
    if stripped_artist.lower().startswith("the "):
        artist_variants.append(stripped_artist[4:])
    if stripped_artist:
        artist_variants.append(stripped_artist)

    seen_uris: set[str] = set()
    results: list[dict[str, Any]] = []
    for params in queries:
        data = shs_get(session, "https://api.secondhandsongs.com/search/performance", params=params)
        if not isinstance(data, dict):
            continue
        for item in data.get("resultPage") or []:
            if not isinstance(item, dict):
                continue
            uri = str(item.get("uri") or "")
            if uri and uri in seen_uris:
                continue
            if uri:
                seen_uris.add(uri)
            results.append(item)

    for item in shs_search_object(session, title, page_size=page_size):
        if item.get("entityType") != "performance":
            continue
        uri = str(item.get("uri") or "")
        if uri and uri in seen_uris:
            continue
        if uri:
            seen_uris.add(uri)
        results.append(item)

    for variant in artist_variants:
        if variant.lower() == stripped_artist.lower():
            continue
        data = shs_get(
            session,
            "https://api.secondhandsongs.com/search/performance",
            params={"title": title, "performer": variant, "pageSize": page_size, "page": 1},
        )
        if not isinstance(data, dict):
            continue
        for item in data.get("resultPage") or []:
            if not isinstance(item, dict):
                continue
            uri = str(item.get("uri") or "")
            if uri and uri in seen_uris:
                continue
            if uri:
                seen_uris.add(uri)
            results.append(item)

    return results


def shs_pick_original_performance(
    performances: list[dict[str, Any]],
    title: str,
    artist: str,
) -> dict[str, Any] | None:
    title_norm = clean(title).lower()
    exact_matches = [
        perf
        for perf in performances
        if clean(perf.get("title")).lower() == title_norm
    ]

    for perf in exact_matches:
        if perf.get("isOriginal"):
            return perf
    if exact_matches:
        return exact_matches[0]

    return None


def shs_resolve_original_performance(
    session: requests.Session,
    performance: dict[str, Any],
) -> dict[str, Any] | None:
    if performance.get("isOriginal"):
        return performance

    performance_id = str(performance.get("uri") or "").rsplit("/", 1)[-1]
    detail = shs_get_performance(session, performance_id) if performance_id else None
    if not detail:
        return None

    originals = detail.get("originals") or []
    for original in originals:
        original_perf = original.get("original") if isinstance(original, dict) else None
        if isinstance(original_perf, dict):
            return shs_get_performance(
                session,
                str(original_perf.get("uri") or "").rsplit("/", 1)[-1],
            ) or original_perf

    return None


def shs_extract_rows(title: str, artist: str) -> list[dict[str, Any]]:
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"Accept": "application/json", "User-Agent": USER_AGENT})

    performances = shs_search_performances(session, title, artist, page_size=50)
    original_perf = shs_pick_original_performance(performances, title, artist)
    if original_perf is not None and not original_perf.get("isOriginal"):
        original_perf = shs_resolve_original_performance(session, original_perf)

    if original_perf is None:
        return []

    original_id = str(original_perf.get("uri") or "").rsplit("/", 1)[-1]
    original_detail = shs_get_performance(session, original_id) if original_id else original_perf
    if not original_detail:
        return []

    original_title = clean(original_detail.get("title")) or clean(title)
    original_artist = clean((original_detail.get("performer") or {}).get("name")) or clean(artist)
    original_year = clean(str(original_detail.get("date") or original_detail.get("firstReleaseDate") or ""))[:4]
    title_id = ""
    works = original_detail.get("works") or []
    for work in works:
        if isinstance(work, dict) and work.get("uri"):
            title_id = uri_id(work.get("uri"))
            break
    if not title_id:
        title_id = uri_id(original_detail.get("uri"))

    original_album = ""
    album_id = ""
    releases = original_detail.get("releases") or []
    for release in releases:
        if isinstance(release, dict) and release.get("entitySubType") == "album":
            original_album = clean(release.get("title"))
            album_id = uri_id(release.get("uri"))
            break
    if not original_album and releases:
        original_album = clean(releases[0].get("title"))
        album_id = uri_id(releases[0].get("uri"))

    rows: list[dict[str, Any]] = []
    for cover in original_detail.get("covers") or []:
        cover_title = clean(cover.get("title"))
        cover_artist = clean((cover.get("performer") or {}).get("name"))
        if not cover_title or not cover_artist:
            continue
        rows.append(
            {
                "performing_artist": cover_artist,
                "title": cover_title,
                "year": "",
                "album": "",
                "genre": "",
                "original_artist": original_artist,
                "original_song_title": original_title,
                "original_album": original_album,
                "original_year": original_year,
                "secondhandsongs_artist_id": uri_id((cover.get("performer") or {}).get("uri")),
                "secondhandsongs_title_id": title_id,
                "secondhandsongs_performance_id": uri_id(cover.get("uri")),
                "secondhandsongs_album_id": album_id,
                "source": "SecondHandSongs",
                "queried_at_utc": utc_now_iso(),
                "source_url": str(cover.get("uri") or ""),
            }
        )

    return rows


def cover_info_rows(title: str, artist: str) -> list[dict[str, Any]]:
    rows = []
    queried_at = utc_now_iso()
    for item in scrape_cover_info(title, artist):
        rows.append(
            {
                "performing_artist": clean(item.get("artist")),
                "title": clean(item.get("title")),
                "year": clean(str(item.get("year") or "")),
                "album": clean(str(item.get("album") or "")),
                "genre": clean(str(item.get("genre") or "")),
                "original_artist": clean(item.get("original_artist")),
                "original_song_title": clean(item.get("original_title")),
                "original_album": clean(str(item.get("original_album") or "")),
                "original_year": clean(str(item.get("original_year") or "")),
                "secondhandsongs_artist_id": "",
                "secondhandsongs_title_id": "",
                "secondhandsongs_performance_id": "",
                "secondhandsongs_album_id": "",
                "source": "cover.info",
                "queried_at_utc": queried_at,
                "source_url": "https://cover.info/api/song/get-detailed",
            }
        )
    return rows


def dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: "OrderedDict[tuple[str, str, str, str], dict[str, Any]]" = OrderedDict()
    for row in rows:
        key = (
            normalize(row.get("performing_artist")),
            normalize(row.get("title")),
            normalize(row.get("original_artist")),
            normalize(row.get("original_song_title")),
        )
        if key not in deduped:
            deduped[key] = row
            continue

        current = deduped[key]
        for field in ["year", "album", "genre", "original_album", "original_year"]:
            if not current.get(field) and row.get(field):
                current[field] = row[field]
        current = merge_source_fields(current, row.get("source", ""), row.get("queried_at_utc", ""), row.get("source_url", ""))
        deduped[key] = current
    return list(deduped.values())


def write_in_batches(
    rows: list[dict[str, Any]],
    output_path: Path,
    *,
    batch_size: int = 30,
    log_path: Path | None = None,
    heartbeat_path: Path | None = None,
    source_count: int = 0,
) -> None:
    existing_keys = load_existing_keys(output_path)
    buffer: list[dict[str, Any]] = []
    seen_keys = set(existing_keys)
    appended = 0
    total = len(rows)

    for row in rows:
        key = (
            normalize(row.get("performing_artist")),
            normalize(row.get("title")),
            normalize(row.get("original_artist")),
            normalize(row.get("original_song_title")),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        buffer.append(row)
        if len(buffer) >= batch_size:
            append_rows(output_path, buffer)
            appended += len(buffer)
            if log_path:
                log_line(log_path, f"Progress appended={appended}; total_candidates={total}; unique_seen={len(seen_keys)}")
            if heartbeat_path:
                write_heartbeat(
                    heartbeat_path,
                    state="running",
                    appended=appended,
                    total_candidates=total,
                    unique_seen=len(seen_keys),
                    output=str(output_path),
                    source_count=source_count,
                )
            buffer.clear()

    if buffer:
        append_rows(output_path, buffer)
        appended += len(buffer)
        if log_path:
            log_line(log_path, f"Progress appended={appended}; total_candidates={total}; unique_seen={len(seen_keys)}")
        if heartbeat_path:
            write_heartbeat(
                heartbeat_path,
                state="running",
                appended=appended,
                total_candidates=total,
                unique_seen=len(seen_keys),
                output=str(output_path),
                source_count=source_count,
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape cover metadata from cover.info and SecondHandSongs.")
    parser.add_argument("--input", type=Path, help="CSV file of songs to process in batch mode.")
    parser.add_argument("--title", help="Song title to search for.")
    parser.add_argument("--artist", help="Original artist to search for.")
    parser.add_argument("--title-column", default="Base Title", help="Title column name when using --input.")
    parser.add_argument("--artist-column", default="Artist", help="Artist column name when using --input.")
    parser.add_argument(
        "--output",
        default=str(OUTPUT_PATH),
        help="Output CSV path. Defaults to D:\\Music\\MusicDB\\basket\\coverdata_shs_ci.csv",
    )
    parser.add_argument(
        "--log",
        default=str(LOG_PATH),
        help="Status log path. Defaults to D:\\Music\\MusicDB\\basket\\coverdata_shs_ci.log",
    )
    parser.add_argument(
        "--heartbeat",
        default=str(HEARTBEAT_PATH),
        help="Heartbeat JSON path. Defaults to D:\\Music\\MusicDB\\basket\\coverdata_shs_ci.status.json",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    log_path = Path(args.log)
    heartbeat_path = Path(args.heartbeat)
    songs: list[tuple[str, str]] = []
    if args.input:
        seen: set[tuple[str, str]] = set()
        if log_path:
            log_line(log_path, f"Start input={args.input} output={output_path}")
        with args.input.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                title = clean(row.get(args.title_column))
                artist = clean(row.get(args.artist_column))
                if not title or not artist:
                    continue
                key = (normalize(title), normalize(artist))
                if key in seen:
                    continue
                seen.add(key)
                songs.append((title, artist))
    else:
        if not args.title or not args.artist:
            parser.error("either --input or both --title and --artist are required")
        songs.append((args.title, args.artist))

    rows: list[dict[str, Any]] = []
    for title, artist in songs:
        if log_path:
            log_line(log_path, f"Query title={title!r} artist={artist!r}")
        rows.extend(cover_info_rows(title, artist) + shs_extract_rows(title, artist))
    rows = dedupe_rows(rows)
    write_in_batches(rows, output_path, batch_size=30, log_path=log_path, heartbeat_path=heartbeat_path, source_count=len(songs))
    if log_path:
        log_line(log_path, f"Done rows={len(rows)} output={output_path}")
    if heartbeat_path:
        write_heartbeat(
            heartbeat_path,
            state="done",
            appended=len(rows),
            total_candidates=len(rows),
            unique_seen=len(rows),
            output=str(output_path),
            source_count=len(songs),
        )

    print(f"ROWS\t{len(rows)}")
    print(f"OUTPUT\t{output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

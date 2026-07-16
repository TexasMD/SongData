"""verify-nyov-batch command implementation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.commands.nyov_report import build_report
from src.config import MusicDBPaths
from src.normalization import normalize_search_text


VERIFIER_VERSION = "nyov-provider-verifier-v1"
DEFAULT_PROVIDERS = ("itunes", "musicbrainz", "spotify")
DEFAULT_TIE_BREAKER_PROVIDERS = ("spotify",)


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    entity_type: str
    entity_id: str
    url: str
    title: str
    artist: str
    album: str
    duration_ms: str
    isrc: str
    raw: dict[str, object]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session() -> requests.Session:
    current = requests.Session()
    retry = Retry(connect=3, read=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    current.mount("http://", adapter)
    current.mount("https://", adapter)
    return current


def _spotify_token(session: requests.Session) -> str:
    client_id = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return ""
    response = session.post(
        "https://accounts.spotify.com/api/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=10,
    )
    if response.status_code != 200:
        return ""
    return str(response.json().get("access_token") or "")


def _status(left: str, right: str) -> str:
    left_norm = normalize_search_text(left)
    right_norm = normalize_search_text(right)
    if not left_norm and not right_norm:
        return "missing"
    if left_norm == right_norm:
        return "exact"
    if left_norm and right_norm and (left_norm in right_norm or right_norm in left_norm):
        return "partial"
    return "different"


def _score(seed: dict[str, str], result: ProviderResult) -> float:
    title = _status(seed.get("seed_title", ""), result.title)
    artist = _status(seed.get("seed_artist", ""), result.artist)
    album = _status(seed.get("seed_album", ""), result.album)
    score = 0.0
    score += {"exact": 0.55, "partial": 0.45}.get(title, 0.0)
    score += {"exact": 0.35, "partial": 0.25}.get(artist, 0.0)
    score += {"exact": 0.10, "partial": 0.05, "missing": 0.03}.get(album, 0.0)
    return min(score, 1.0)


def _match_status(seed: dict[str, str], result: ProviderResult) -> str:
    score = _score(seed, result)
    if score >= 0.9:
        return "matched"
    if score >= 0.72:
        return "needs_review"
    return "rejected"


def _attempt_id(nyov_id: str, provider: str, entity_id: str, queried_at: str) -> str:
    payload = f"{nyov_id}|{provider}|{entity_id}|{queried_at}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _to_attempt_row(seed: dict[str, str], result: ProviderResult, queried_at: str) -> tuple[str, ...]:
    match_status = _match_status(seed, result)
    return (
        _attempt_id(seed["nyov_id"], result.provider, result.entity_id or result.url, queried_at),
        seed["nyov_id"],
        result.provider,
        result.entity_type,
        result.entity_id,
        result.url,
        seed.get("seed_title", ""),
        seed.get("seed_artist", ""),
        seed.get("seed_album", ""),
        queried_at,
        json.dumps(result.raw, ensure_ascii=False, sort_keys=True),
        match_status,
        f"{_score(seed, result):.3f}",
        _status(seed.get("seed_title", ""), result.title),
        _status(seed.get("seed_artist", ""), result.artist),
        _status(seed.get("seed_album", ""), result.album),
        "not_checked",
        "not_checked" if not result.isrc else "present",
        "automation",
        VERIFIER_VERSION,
        "",
    )


def query_itunes(session: requests.Session, title: str, artist: str) -> list[ProviderResult]:
    term = f"{artist} {title}".strip()
    response = session.get(
        "https://itunes.apple.com/search",
        params={"term": term, "media": "music", "limit": 5},
        timeout=15,
    )
    if response.status_code != 200:
        return []
    results: list[ProviderResult] = []
    for item in response.json().get("results", []):
        if item.get("wrapperType") != "track":
            continue
        results.append(
            ProviderResult(
                provider="iTunes",
                entity_type="track",
                entity_id=str(item.get("trackId") or ""),
                url=str(item.get("trackViewUrl") or ""),
                title=str(item.get("trackName") or ""),
                artist=str(item.get("artistName") or ""),
                album=str(item.get("collectionName") or ""),
                duration_ms=str(item.get("trackTimeMillis") or ""),
                isrc="",
                raw=dict(item),
            )
        )
    return results


def query_musicbrainz(session: requests.Session, title: str, artist: str) -> list[ProviderResult]:
    user_agent = os.getenv("MUSICBRAINZ_USER_AGENT", "MusicDBVerifier/1.0").strip()
    query = f'recording:"{title}" AND artist:"{artist}"'
    response = session.get(
        f"https://musicbrainz.org/ws/2/recording/?query={quote(query)}&fmt=json",
        headers={"User-Agent": user_agent},
        timeout=15,
    )
    if response.status_code != 200:
        return []
    results: list[ProviderResult] = []
    for item in response.json().get("recordings", [])[:5]:
        artist_credit = item.get("artist-credit") or []
        artist_names = []
        for credit in artist_credit:
            if isinstance(credit, dict):
                artist_names.append(str((credit.get("artist") or {}).get("name") or credit.get("name") or ""))
        releases = item.get("releases") or []
        isrcs = item.get("isrcs") or []
        results.append(
            ProviderResult(
                provider="MusicBrainz",
                entity_type="recording",
                entity_id=str(item.get("id") or ""),
                url=f"https://musicbrainz.org/recording/{item.get('id')}" if item.get("id") else "",
                title=str(item.get("title") or ""),
                artist=", ".join(name for name in artist_names if name),
                album=str((releases[0] if releases else {}).get("title") or ""),
                duration_ms=str(item.get("length") or ""),
                isrc=str(isrcs[0] if isrcs else ""),
                raw=dict(item),
            )
        )
    return results


def query_spotify(session: requests.Session, token: str, title: str, artist: str) -> list[ProviderResult]:
    if not token:
        return []
    query = f"track:{title}"
    if artist:
        query = f"{query} artist:{artist}"
    response = session.get(
        "https://api.spotify.com/v1/search",
        params={"q": query, "type": "track", "limit": 5},
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if response.status_code != 200:
        return []
    results: list[ProviderResult] = []
    for item in response.json().get("tracks", {}).get("items", []):
        album = item.get("album") or {}
        external_ids = item.get("external_ids") or {}
        results.append(
            ProviderResult(
                provider="Spotify",
                entity_type="track",
                entity_id=str(item.get("id") or ""),
                url=str((item.get("external_urls") or {}).get("spotify") or ""),
                title=str(item.get("name") or ""),
                artist=", ".join(str(artist.get("name") or "") for artist in item.get("artists", [])),
                album=str(album.get("name") or ""),
                duration_ms=str(item.get("duration_ms") or ""),
                isrc=str(external_ids.get("isrc") or ""),
                raw=dict(item),
            )
        )
    return results


def _provider_functions(
    session: requests.Session,
    providers: Iterable[str],
    spotify_token: str,
) -> list[tuple[str, Callable[[str, str], list[ProviderResult]]]]:
    functions: list[tuple[str, Callable[[str, str], list[ProviderResult]]]] = []
    provider_set = {provider.lower().strip() for provider in providers if provider.strip()}
    if "itunes" in provider_set:
        functions.append(("iTunes", lambda title, artist: query_itunes(session, title, artist)))
    if "musicbrainz" in provider_set:
        functions.append(("MusicBrainz", lambda title, artist: query_musicbrainz(session, title, artist)))
    if "spotify" in provider_set and spotify_token:
        functions.append(("Spotify", lambda title, artist: query_spotify(session, spotify_token, title, artist)))
    return functions


def _insert_attempts(conn: sqlite3.Connection, rows: list[tuple[str, ...]]) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO nyov_verification_attempts
        (attempt_id, nyov_id, provider, provider_entity_type, provider_entity_id, provider_url,
         query_title, query_artist, query_album, queried_at, result_json, match_status,
         match_score, title_match_status, artist_match_status, album_match_status,
         duration_match_status, isrc_match_status, verifier, verifier_version, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _empty_provider_stat() -> dict[str, object]:
    return {
        "calls": 0,
        "elapsed_seconds": 0.0,
        "results": 0,
        "matched": 0,
        "needs_review": 0,
        "rejected": 0,
    }


def _record_provider_stat(
    stats: dict[str, dict[str, object]],
    provider: str,
    *,
    elapsed_seconds: float,
    rows: list[tuple[str, ...]],
) -> None:
    stat = stats.setdefault(provider, _empty_provider_stat())
    stat["calls"] = int(stat["calls"]) + 1
    stat["elapsed_seconds"] = round(float(stat["elapsed_seconds"]) + elapsed_seconds, 3)
    stat["results"] = int(stat["results"]) + len(rows)
    for row in rows:
        status = row[11]
        if status in {"matched", "needs_review", "rejected"}:
            stat[status] = int(stat[status]) + 1


def _is_ambiguous(rows: list[tuple[str, ...]]) -> bool:
    reviewable = [row for row in rows if row[11] in {"matched", "needs_review"}]
    matched_providers = {row[2] for row in rows if row[11] == "matched"}
    if len(matched_providers) < 2:
        return True
    return any(row[14] == "different" or row[15] == "different" or row[16] == "different" for row in reviewable)


def _run_provider_for_seed(
    seed: dict[str, str],
    provider_name: str,
    provider_fn: Callable[[str, str], list[ProviderResult]],
    queried_at: str,
    stats: dict[str, dict[str, object]],
) -> list[tuple[str, ...]]:
    title = str(seed.get("seed_title") or "")
    artist = str(seed.get("seed_artist") or "")
    started_at = time.perf_counter()
    results = provider_fn(title, artist)
    rows = [_to_attempt_row(seed, result, queried_at) for result in results]
    _record_provider_stat(stats, provider_name, elapsed_seconds=time.perf_counter() - started_at, rows=rows)
    return rows


def verify_batch(
    db_path: Path,
    *,
    batch_step: str = "candidate_dual_source_match",
    batch_limit: int = 10,
    providers: Iterable[str] = DEFAULT_PROVIDERS,
    strategy: str = "all",
    tie_breaker_providers: Iterable[str] = DEFAULT_TIE_BREAKER_PROVIDERS,
    write: bool = False,
) -> dict[str, object]:
    report = build_report(db_path, queue_limit=batch_limit, batch_step=batch_step, batch_limit=batch_limit)
    batch = report["verification_batch"]
    if not write:
        return {
            "db_path": str(db_path),
            "dry_run": True,
            "batch_step": batch_step,
            "batch_limit": batch_limit,
            "providers": list(providers),
            "strategy": strategy,
            "tie_breaker_providers": list(tie_breaker_providers),
            "candidate_rows": len(batch),
            "attempts_written": 0,
        }

    session = _session()
    token = _spotify_token(session)
    provider_functions = _provider_functions(session, providers, token)
    tie_breaker_functions = _provider_functions(session, tie_breaker_providers, token)
    queried_at = _utc_now()
    attempt_rows: list[tuple[str, ...]] = []
    provider_errors: list[dict[str, str]] = []
    provider_stats: dict[str, dict[str, object]] = {}
    tie_breaker_rows = 0

    for seed in batch:
        seed_rows: list[tuple[str, ...]] = []
        for provider_name, provider_fn in provider_functions:
            try:
                rows = _run_provider_for_seed(seed, provider_name, provider_fn, queried_at, provider_stats)
                seed_rows.extend(rows)
                attempt_rows.extend(rows)
            except requests.RequestException as exc:
                provider_errors.append({"nyov_id": seed["nyov_id"], "provider": provider_name, "error": str(exc)})
        if strategy == "tie-breaker" and _is_ambiguous(seed_rows):
            already_checked = {row[2] for row in seed_rows}
            for provider_name, provider_fn in tie_breaker_functions:
                if provider_name in already_checked:
                    continue
                try:
                    rows = _run_provider_for_seed(seed, provider_name, provider_fn, queried_at, provider_stats)
                    tie_breaker_rows += len(rows)
                    attempt_rows.extend(rows)
                except requests.RequestException as exc:
                    provider_errors.append({"nyov_id": seed["nyov_id"], "provider": provider_name, "error": str(exc)})

    with sqlite3.connect(db_path) as conn:
        _insert_attempts(conn, attempt_rows)
        attempts_total = conn.execute("SELECT COUNT(*) FROM nyov_verification_attempts").fetchone()[0]

    return {
        "db_path": str(db_path),
        "dry_run": False,
        "batch_step": batch_step,
        "batch_limit": batch_limit,
        "providers": [name for name, _ in provider_functions],
        "strategy": strategy,
        "tie_breaker_providers": [name for name, _ in tie_breaker_functions],
        "candidate_rows": len(batch),
        "attempts_written": len(attempt_rows),
        "tie_breaker_attempts_written": tie_breaker_rows,
        "attempts_total": attempts_total,
        "provider_stats": provider_stats,
        "provider_errors": provider_errors,
    }


def run(
    *,
    write: bool,
    paths: MusicDBPaths,
    db_path: Path | None = None,
    batch_step: str = "candidate_dual_source_match",
    batch_limit: int = 10,
    providers: str = ",".join(DEFAULT_PROVIDERS),
    strategy: str = "all",
    tie_breaker_providers: str = ",".join(DEFAULT_TIE_BREAKER_PROVIDERS),
) -> int:
    db_path = (db_path or paths.nyov_db_path).resolve()
    provider_list = [provider.strip() for provider in providers.split(",") if provider.strip()]
    tie_breaker_provider_list = [provider.strip() for provider in tie_breaker_providers.split(",") if provider.strip()]
    summary = verify_batch(
        db_path,
        batch_step=batch_step,
        batch_limit=batch_limit,
        providers=provider_list,
        strategy=strategy,
        tie_breaker_providers=tie_breaker_provider_list,
        write=write,
    )
    print("verify-nyov-batch: dry-run=" + str(not write))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0

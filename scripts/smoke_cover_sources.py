"""Smoke-test live cover metadata sources.

This script is intentionally observational: it queries the configured cover
sources and reports counts, callback checks, sample rows, and errors without
writing to MusicDB data files.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.cover_info_client import scrape_cover_info
from src.secondhandsongs_client import scrape_secondhandsongs
from src.whosampled_client import scrape_whosampled


SourceFn = Callable[[str, str, str, Callable[..., None]], list[dict[str, Any]]]
CROSS_SOURCE_EMPTY_RETRY_THRESHOLD = 10


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cover_info(title: str, artist: str, year: str, callback: Callable[..., None]) -> list[dict[str, Any]]:
    return scrape_cover_info(title, artist, year, callback=callback)


def _secondhandsongs(title: str, artist: str, year: str, callback: Callable[..., None]) -> list[dict[str, Any]]:
    return scrape_secondhandsongs(title, artist, year, callback=callback)


def _whosampled(title: str, artist: str, year: str, callback: Callable[..., None]) -> list[dict[str, Any]]:
    return scrape_whosampled(title, artist, callback=callback)


SOURCES: dict[str, SourceFn] = {
    "cover.info": _cover_info,
    "SecondHandSongs": _secondhandsongs,
    "WhoSampled": _whosampled,
}


def run_smoke(title: str, artist: str, year: str, sources: list[str]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def callback(source: str, query_kind: str, query_url: str, result_count: int | None, checked_at: str) -> None:
        checks.append(
            {
                "source": source,
                "query_kind": query_kind,
                "query_url": query_url,
                "result_count": result_count,
                "checked_at": checked_at,
            }
        )

    source_results: dict[str, Any] = {}
    for source in sources:
        source_results[source] = _run_source(source, title, artist, year, callback, checks)

    best_row_count = max(
        (int(result.get("row_count") or 0) for result in source_results.values() if result.get("status") == "ok"),
        default=0,
    )
    if best_row_count >= CROSS_SOURCE_EMPTY_RETRY_THRESHOLD:
        for source in sources:
            result = source_results[source]
            if result.get("status") != "ok" or int(result.get("row_count") or 0) != 0:
                continue
            retry_result = _run_source(source, title, artist, year, callback, checks)
            retry_result["initial_row_count"] = 0
            retry_result["retry_attempts"] = 1
            retry_result["retry_reason"] = (
                f"cross_source_empty: another source returned at least "
                f"{CROSS_SOURCE_EMPTY_RETRY_THRESHOLD} rows"
            )
            if int(retry_result.get("row_count") or 0) == 0:
                retry_result["warning"] = "suspicious_empty_after_retry"
            source_results[source] = retry_result

    return {
        "title": title,
        "artist": artist,
        "year": year,
        "sources": source_results,
        "source_checks": checks,
    }


def _run_source(
    source: str,
    title: str,
    artist: str,
    year: str,
    callback: Callable[..., None],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    started_at = _utc_now_iso()
    source_check_start = len(checks)
    try:
        rows = SOURCES[source](title, artist, year, callback)
        source_checks = checks[source_check_start:]
        result: dict[str, Any] = {
            "status": "ok",
            "started_at": started_at,
            "finished_at": _utc_now_iso(),
            "row_count": len(rows),
            "sample_rows": rows[:5],
        }
        if source == "SecondHandSongs":
            result["diagnostics"] = secondhandsongs_diagnostics(rows, source_checks)
        return result
    except Exception as exc:  # noqa: BLE001 - smoke test must preserve source-specific failures.
        return {
            "status": "error",
            "started_at": started_at,
            "finished_at": _utc_now_iso(),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def secondhandsongs_diagnostics(
    rows: list[dict[str, Any]],
    source_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    exact_counts = [
        check.get("result_count")
        for check in source_checks
        if check.get("query_kind") == "search_performance" and "performer=" in str(check.get("query_url") or "")
    ]
    broad_counts = [
        check.get("result_count")
        for check in source_checks
        if check.get("query_kind") == "search_performance" and "performer=" not in str(check.get("query_url") or "")
    ]
    detail_checks = [check for check in source_checks if check.get("query_kind") == "performance_detail"]
    detail_check = detail_checks[-1] if detail_checks else {}
    artists = {str(row.get("artist") or "").casefold() for row in rows}
    return {
        "returned_row_count": len(rows),
        "exact_performance_count": exact_counts[0] if exact_counts else 0,
        "broad_performance_count": sum(count for count in broad_counts if isinstance(count, int)),
        "detail_result_count": detail_check.get("result_count", 0),
        "detail_url": detail_check.get("query_url", ""),
        "known_covers_present": {
            "Jeff Buckley": "jeff buckley" in artists,
            "John Cale": "john cale" in artists,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test live cover metadata sources.")
    parser.add_argument("--title", default="Hallelujah")
    parser.add_argument("--artist", default="Leonard Cohen")
    parser.add_argument("--year", default="1984")
    parser.add_argument(
        "--source",
        action="append",
        choices=sorted(SOURCES),
        help="Source to check. Repeat to check multiple sources. Defaults to all.",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    selected_sources = args.source or list(SOURCES)
    result = run_smoke(args.title, args.artist, args.year, selected_sources)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

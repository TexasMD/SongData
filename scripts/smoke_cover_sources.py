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
        started_at = _utc_now_iso()
        try:
            rows = SOURCES[source](title, artist, year, callback)
            source_results[source] = {
                "status": "ok",
                "started_at": started_at,
                "finished_at": _utc_now_iso(),
                "row_count": len(rows),
                "sample_rows": rows[:5],
            }
        except Exception as exc:  # noqa: BLE001 - smoke test must preserve source-specific failures.
            source_results[source] = {
                "status": "error",
                "started_at": started_at,
                "finished_at": _utc_now_iso(),
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

    return {
        "title": title,
        "artist": artist,
        "year": year,
        "sources": source_results,
        "source_checks": checks,
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

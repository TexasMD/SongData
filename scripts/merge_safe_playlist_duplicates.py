#!/usr/bin/env python3
"""Merge high-confidence duplicate SongDB rows for a playlist.

This only merges exact normalized title+artist duplicates with compatible
durations and no explicit version/remix/live distinction.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MAIN = PROJECT_DIR / "data" / "processed" / "Main_Song_Database.csv"
DEFAULT_EXPORTS = PROJECT_DIR / "data" / "exports"
COMPILATION_RE = re.compile(
    r"\b(greatest|best of|very best|essential|collection|anthology|singles|"
    r"hits|gold|definitive|ultimate|chronicles|retrospective|time capsule|absolute)\b",
    re.I,
)
VERSION_RE = re.compile(
    r"\b(live|mix|remix|remaster|version|edit|extended|dub|instrumental|"
    r"acoustic|alternate|night version|club|single version|album version)\b",
    re.I,
)
MULTI_FIELDS = {
    "Source Files", "Playlists", "Original Data", "Spotify LastFM Tags",
    "Spotify Genre Detail", "Duplicate Merge Notes", "Alternate Albums",
}


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def norm(value: str) -> str:
    value = clean(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[’‘`']", "", value)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"\bthe\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def key(row: dict[str, str]) -> tuple[str, str]:
    return norm(row.get("Title") or row.get("Base Title")), norm(row.get("Artist"))


def playlist_values(value: str) -> set[str]:
    return {p.strip() for p in re.split(r"\s*;\s*|\s*,\s*", clean(value)) if p.strip()}


def add_multi(existing: str, addition: str) -> str:
    items = []
    for value in [existing, addition]:
        for piece in re.split(r"\s*;\s*|\s*,\s*", clean(value)):
            if piece and piece not in items:
                items.append(piece)
    return "; ".join(items)


def duration_seconds(value: str) -> int | None:
    parts = clean(value).split(":")
    if not parts or not all(p.isdigit() for p in parts):
        return None
    nums = list(map(int, parts))
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    return None


def year_value(row: dict[str, str]) -> int | None:
    for field in ["Year", "Spotify Release Date"]:
        match = re.search(r"\b(19\d{2}|20\d{2})\b", clean(row.get(field)))
        if match:
            return int(match.group(1))
    return None


def useful_score(row: dict[str, str]) -> int:
    fields = [
        "Title", "Base Title", "Artist", "Album", "Duration", "Genre", "Year",
        "Original Artist", "Energy", "BPM", "Vibe", "Spotify Track ID",
        "Spotify Popularity", "Spotify MusicBrainz ID", "Spotify LastFM Tags",
    ]
    return sum(1 for f in fields if clean(row.get(f)))


def safe_group(rows: list[dict[str, str]]) -> bool:
    if len(rows) < 2:
        return False
    if any(VERSION_RE.search(clean(r.get("Title"))) for r in rows):
        return False
    durations = [duration_seconds(r.get("Duration", "")) for r in rows]
    durations = [d for d in durations if d is not None]
    if len(durations) >= 2 and max(durations) - min(durations) > 3:
        return False
    return True


def choose_keeper(rows: list[dict[str, str]]) -> dict[str, str]:
    def sort_key(row: dict[str, str]):
        album = clean(row.get("Album"))
        return (
            bool(COMPILATION_RE.search(album)),
            year_value(row) if year_value(row) is not None else 9999,
            not bool(album),
            -useful_score(row),
            clean(row.get("Title")),
        )

    return sorted(rows, key=sort_key)[0]


def merge_into(keeper: dict[str, str], duplicate: dict[str, str], duplicate_line: int) -> None:
    for field, value in duplicate.items():
        value = clean(value)
        if not value:
            continue
        if field in MULTI_FIELDS:
            keeper[field] = add_multi(keeper.get(field, ""), value)
        elif not clean(keeper.get(field)):
            keeper[field] = value

    album = clean(duplicate.get("Album"))
    if album and album != clean(keeper.get("Album")):
        keeper["Alternate Albums"] = add_multi(keeper.get("Alternate Albums", ""), album)
    note = "merged duplicate csv line {}: {} / {} / {}".format(
        duplicate_line,
        clean(duplicate.get("Title")),
        clean(duplicate.get("Artist")),
        album,
    )
    keeper["Duplicate Merge Notes"] = add_multi(keeper.get("Duplicate Merge Notes", ""), note)


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge high-confidence playlist duplicate rows.")
    parser.add_argument("--main", type=Path, default=DEFAULT_MAIN)
    parser.add_argument("--playlist", default="NRG")
    parser.add_argument("--summary", type=Path, default=None)
    args = parser.parse_args()

    with args.main.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]

    for col in ["Alternate Albums", "Duplicate Merge Notes"]:
        if col not in headers:
            headers.append(col)
        for row in rows:
            row.setdefault(col, "")

    indexed = defaultdict(list)
    for idx, row in enumerate(rows):
        if args.playlist in playlist_values(row.get("Playlists", "")):
            indexed[key(row)].append((idx, row))

    removed = set()
    merge_log = []
    review_groups = []
    for group_key, vals in indexed.items():
        group_rows = [row for _, row in vals]
        if len(group_rows) < 2:
            continue
        if not safe_group(group_rows):
            review_groups.append({
                "key": group_key,
                "rows": [{"csv_line": idx + 2, "title": r.get("Title", ""), "artist": r.get("Artist", ""), "album": r.get("Album", ""), "duration": r.get("Duration", "")} for idx, r in vals],
            })
            continue
        keeper = choose_keeper(group_rows)
        keeper_idx = next(idx for idx, row in vals if row is keeper)
        for idx, row in vals:
            if row is keeper:
                continue
            merge_into(keeper, row, idx + 2)
            removed.add(idx)
            merge_log.append({
                "group_key": "|".join(group_key),
                "keeper_original_csv_line": keeper_idx + 2,
                "removed_original_csv_line": idx + 2,
                "removed_title": row.get("Title", ""),
                "removed_artist": row.get("Artist", ""),
                "removed_album": row.get("Album", ""),
                "keeper_title": keeper.get("Title", ""),
                "keeper_artist": keeper.get("Artist", ""),
                "keeper_album": keeper.get("Album", ""),
            })

    new_rows = [row for idx, row in enumerate(rows) if idx not in removed]
    with args.main.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(new_rows)

    summary = {
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "playlist": args.playlist,
        "input_rows": len(rows),
        "removed_duplicate_rows": len(removed),
        "output_rows": len(new_rows),
        "merged_groups": len({item["group_key"] for item in merge_log}),
        "review_groups_not_merged": len(review_groups),
        "merge_log": merge_log,
        "review_groups": review_groups,
    }
    summary_path = args.summary or DEFAULT_EXPORTS / f"playlist_{args.playlist}_safe_duplicate_merge_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

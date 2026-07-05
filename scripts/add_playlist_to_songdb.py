#!/usr/bin/env python3
"""Mark songs in Main_Song_Database.csv as belonging to a named playlist."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MAIN = PROJECT_DIR / "data" / "processed" / "Main_Song_Database.csv"
DEFAULT_EXPORTS = PROJECT_DIR / "data" / "exports"


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def norm(value: str) -> str:
    value = clean(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[’‘`']", "", value)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"\b(feat|featuring|ft)\.?\b.*$", "", value)
    value = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", value)
    value = re.sub(r"\bthe\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def key_variants(title: str, artist: str) -> List[Tuple[str, str]]:
    title_key = norm(title)
    artist_key = norm(artist)
    if not title_key or not artist_key:
        return []
    variants = [
        (title_key, artist_key),
        (title_key.replace(" ", ""), artist_key),
        (title_key, artist_key.replace(" ", "")),
        (title_key.replace(" ", ""), artist_key.replace(" ", "")),
    ]
    out = []
    for item in variants:
        if item not in out:
            out.append(item)
    return out


def parse_playlist_name(path: Path) -> str:
    stem = path.stem
    match = re.match(r"PLAYLIST\s*-\s*(.+)$", stem, flags=re.I)
    return clean(match.group(1) if match else stem)


def parse_playlist(path: Path) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = clean(raw_line).strip("*")
        if not line or line.startswith("#"):
            continue
        if "—" in line:
            artist, title = [clean(x) for x in line.split("—", 1)]
        elif " - " in line:
            artist, title = [clean(x) for x in line.split(" - ", 1)]
        else:
            continue
        if artist and title:
            entries.append({"line": str(line_no), "artist": artist, "title": title})
    return entries


def read_csv(path: Path) -> tuple[List[str], List[Dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write_csv(path: Path, headers: List[str], rows: List[Dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def add_list_value(existing: str, value: str) -> str:
    seen = []
    for item in re.split(r"\s*;\s*|\s*,\s*", clean(existing)):
        if item and item not in seen:
            seen.append(item)
    if value not in seen:
        seen.append(value)
    return "; ".join(seen)


def build_index(rows: List[Dict[str, str]]) -> Dict[Tuple[str, str], List[int]]:
    index: Dict[Tuple[str, str], List[int]] = {}
    for idx, row in enumerate(rows):
        titles = [
            row.get("Title", ""),
            row.get("Base Title", ""),
            row.get("Spotify Input Title", ""),
            row.get("Spotify Matched Title", ""),
        ]
        artists = [
            row.get("Artist", ""),
            row.get("Spotify Input Artist", ""),
            row.get("Spotify Matched Artist", ""),
        ]
        for title in titles:
            for artist in artists:
                for key in key_variants(title, artist):
                    index.setdefault(key, []).append(idx)
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description="Add playlist membership to SongDB.")
    parser.add_argument("playlist_file", type=Path)
    parser.add_argument("--main", type=Path, default=DEFAULT_MAIN)
    parser.add_argument("--playlist-name", default="")
    parser.add_argument("--summary", type=Path, default=None)
    args = parser.parse_args()

    playlist_name = clean(args.playlist_name) or parse_playlist_name(args.playlist_file)
    headers, rows = read_csv(args.main)
    if "Playlists" not in headers:
        insert_after = headers.index("Source Files") + 1 if "Source Files" in headers else len(headers)
        headers.insert(insert_after, "Playlists")
    for row in rows:
        row.setdefault("Playlists", "")

    entries = parse_playlist(args.playlist_file)
    index = build_index(rows)
    unmatched = []
    matched_entries = 0
    touched_rows = set()
    for entry in entries:
        row_ids = []
        seen = set()
        for key in key_variants(entry["title"], entry["artist"]):
            for idx in index.get(key, []):
                if idx not in seen:
                    row_ids.append(idx)
                    seen.add(idx)
        if not row_ids:
            unmatched.append(entry)
            continue
        matched_entries += 1
        for idx in row_ids:
            rows[idx]["Playlists"] = add_list_value(rows[idx].get("Playlists", ""), playlist_name)
            touched_rows.add(idx)

    write_csv(args.main, headers, rows)
    summary = {
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "main_database": str(args.main),
        "playlist_file": str(args.playlist_file),
        "playlist_name": playlist_name,
        "playlist_entries": len(entries),
        "matched_playlist_entries": matched_entries,
        "unmatched_playlist_entries": len(unmatched),
        "database_rows_marked": len(touched_rows),
        "unmatched": unmatched,
    }
    summary_path = args.summary or DEFAULT_EXPORTS / f"playlist_import_{playlist_name}_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

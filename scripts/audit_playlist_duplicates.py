#!/usr/bin/env python3
"""Audit duplicate/alternate SongDB entries for a playlist."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MAIN = PROJECT_DIR / "data" / "processed" / "Main_Song_Database.csv"
DEFAULT_EXPORTS = PROJECT_DIR / "data" / "exports"
GREATEST_HITS_RE = re.compile(
    r"\b(greatest|best of|very best|essential|collection|anthology|"
    r"singles|hits|gold|definitive|ultimate|chronicles|retrospective)\b",
    re.I,
)


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


def compact_norm(value: str) -> str:
    return norm(value).replace(" ", "")


def group_key(row: dict[str, str]) -> str:
    title = row.get("Base Title") or row.get("Title") or row.get("Spotify Input Title")
    artist = row.get("Artist") or row.get("Spotify Input Artist")
    return f"{compact_norm(title)}|||{compact_norm(artist)}"


def playlist_values(value: str) -> set[str]:
    return {p.strip() for p in re.split(r"\s*;\s*|\s*,\s*", clean(value)) if p.strip()}


def parse_year(row: dict[str, str]) -> int | None:
    candidates = [row.get("Year", ""), row.get("Spotify Release Date", "")]
    for value in candidates:
        match = re.search(r"\b(19\d{2}|20\d{2})\b", clean(value))
        if match:
            return int(match.group(1))
    return None


def usefulness_score(row: dict[str, str]) -> int:
    preferred_fields = [
        "Title", "Base Title", "Artist", "Album", "Duration", "Genre", "Year",
        "Original Artist", "Energy", "BPM", "Vibe", "Spotify Track ID",
        "Spotify Popularity", "Spotify MusicBrainz ID", "Spotify LastFM Tags",
    ]
    score = sum(1 for field in preferred_fields if clean(row.get(field)))
    if clean(row.get("Spotify Verified")) == "Yes":
        score += 3
    if clean(row.get("MusicBrainz Verified")) == "Yes":
        score += 3
    if clean(row.get("Album")) and not GREATEST_HITS_RE.search(clean(row.get("Album"))):
        score += 2
    if parse_year(row):
        score += 1
    return score


def choose_keeper(rows: list[dict[str, str]]) -> dict[str, str]:
    def sort_key(row: dict[str, str]):
        year = parse_year(row)
        is_hits = bool(GREATEST_HITS_RE.search(clean(row.get("Album"))))
        return (
            is_hits,
            year if year is not None else 9999,
            -usefulness_score(row),
            clean(row.get("Title")),
        )

    return sorted(rows, key=sort_key)[0]


def classify_group(rows: list[dict[str, str]]) -> str:
    albums = {compact_norm(r.get("Album", "")) for r in rows if clean(r.get("Album"))}
    durations = {compact_norm(r.get("Duration", "")) for r in rows if clean(r.get("Duration"))}
    spotify_ids = {clean(r.get("Spotify Track ID")) for r in rows if clean(r.get("Spotify Track ID"))}
    years = {parse_year(r) for r in rows if parse_year(r) is not None}
    has_hits = any(GREATEST_HITS_RE.search(clean(r.get("Album"))) for r in rows)
    if len(spotify_ids) == 1 and len(spotify_ids) > 0:
        return "true_duplicate_same_spotify_track"
    if len(albums) <= 1 and len(durations) <= 1:
        return "probable_true_duplicate"
    if has_hits:
        return "album_alternate_greatest_hits_present"
    if len(years) > 1 or len(albums) > 1:
        return "album_or_release_alternate"
    return "needs_review"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit duplicate rows for a SongDB playlist.")
    parser.add_argument("--main", type=Path, default=DEFAULT_MAIN)
    parser.add_argument("--playlist", default="NRG")
    parser.add_argument("--out-csv", type=Path, default=None)
    parser.add_argument("--summary", type=Path, default=None)
    args = parser.parse_args()

    with args.main.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        headers = list(rows[0].keys()) if rows else []

    playlist_rows = [
        (idx + 2, row)
        for idx, row in enumerate(rows)
        if args.playlist in playlist_values(row.get("Playlists", ""))
    ]
    groups: dict[str, list[tuple[int, dict[str, str]]]] = defaultdict(list)
    for line_no, row in playlist_rows:
        groups[group_key(row)].append((line_no, row))

    duplicate_groups = {key: vals for key, vals in groups.items() if len(vals) > 1}
    out_rows = []
    class_counts: dict[str, int] = defaultdict(int)
    for group_id, (key, vals) in enumerate(sorted(duplicate_groups.items()), 1):
        group_rows = [row for _, row in vals]
        classification = classify_group(group_rows)
        class_counts[classification] += 1
        keeper = choose_keeper(group_rows)
        keeper_line = next(line for line, row in vals if row is keeper)
        for line_no, row in vals:
            out_rows.append({
                "duplicate_group": f"{args.playlist}_{group_id:04d}",
                "classification": classification,
                "recommended_action": "keep_merge_into_this_row" if row is keeper else "merge_into_recommended_keeper",
                "recommended_keeper_line": keeper_line,
                "csv_line": line_no,
                "Title": row.get("Title", ""),
                "Base Title": row.get("Base Title", ""),
                "Artist": row.get("Artist", ""),
                "Album": row.get("Album", ""),
                "Duration": row.get("Duration", ""),
                "Year": row.get("Year", ""),
                "Genre": row.get("Genre", ""),
                "Source Files": row.get("Source Files", ""),
                "Spotify Track ID": row.get("Spotify Track ID", ""),
                "Spotify Popularity": row.get("Spotify Popularity", ""),
                "Spotify Album": row.get("Spotify Album", ""),
                "Spotify Release Date": row.get("Spotify Release Date", ""),
                "Spotify Match Method": row.get("Spotify Match Method", ""),
                "MusicBrainz Verified": row.get("MusicBrainz Verified", ""),
                "Playlists": row.get("Playlists", ""),
                "usefulness_score": usefulness_score(row),
            })

    out_csv = args.out_csv or DEFAULT_EXPORTS / f"playlist_{args.playlist}_duplicate_alternate_audit.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_fields = [
        "duplicate_group", "classification", "recommended_action",
        "recommended_keeper_line", "csv_line", "Title", "Base Title", "Artist",
        "Album", "Duration", "Year", "Genre", "Source Files", "Spotify Track ID",
        "Spotify Popularity", "Spotify Album", "Spotify Release Date",
        "Spotify Match Method", "MusicBrainz Verified", "Playlists", "usefulness_score",
    ]
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(out_rows)

    summary = {
        "playlist": args.playlist,
        "playlist_rows": len(playlist_rows),
        "unique_playlist_song_groups": len(groups),
        "duplicate_or_alternate_groups": len(duplicate_groups),
        "duplicate_or_alternate_rows": sum(len(v) for v in duplicate_groups.values()),
        "classification_counts": dict(sorted(class_counts.items())),
        "audit_csv": str(out_csv),
    }
    summary_path = args.summary or DEFAULT_EXPORTS / f"playlist_{args.playlist}_duplicate_alternate_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

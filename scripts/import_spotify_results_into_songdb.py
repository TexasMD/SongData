#!/usr/bin/env python3
"""Merge Spotify popularity results into the main SongDB CSV.

The importer preserves existing SongDB columns, adds Spotify-specific columns,
updates matching title+artist rows, and appends Spotify rows that are not
already present in the database.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MAIN = PROJECT_DIR / "data" / "processed" / "Main_Song_Database.csv"
DEFAULT_EXPORTS = PROJECT_DIR / "data" / "exports"
DEFAULT_SPOTIFY = Path(r"C:\codex_work\projects\spotify_popularity_ranker\data\songpopularity_results.csv")
SPOTIFY_SOURCE = "spotify_popularity_results.csv"

SPOTIFY_COLUMNS = [
    "Spotify Input Title",
    "Spotify Input Artist",
    "Spotify Matched Title",
    "Spotify Matched Artist",
    "Spotify Artist Changed",
    "Spotify Artist Similarity",
    "Spotify Popularity",
    "Spotify Track ID",
    "Spotify Match Method",
    "Spotify Match Score",
    "Spotify Search Strategy",
    "Spotify ISRC",
    "Spotify Album",
    "Spotify Release Date",
    "Spotify Duration (ms)",
    "Spotify MusicBrainz ID",
    "Spotify MBID Method",
    "Spotify BPM",
    "Spotify Key",
    "Spotify Scale",
    "Spotify Key Full",
    "Spotify Energy Level",
    "Spotify Danceability",
    "Spotify Vocal Type",
    "Spotify Mood Happy",
    "Spotify Mood Sad",
    "Spotify Mood Aggressive",
    "Spotify Mood Relaxed",
    "Spotify Mood Party",
    "Spotify Genre",
    "Spotify Genre Detail",
    "Spotify LastFM Tags",
    "Spotify Vibe",
    "Spotify AB Source",
]

SPOTIFY_MAP = {
    "Input Title": "Spotify Input Title",
    "Input Artist": "Spotify Input Artist",
    "Matched Title": "Spotify Matched Title",
    "Matched Artist": "Spotify Matched Artist",
    "Artist Changed": "Spotify Artist Changed",
    "Artist Similarity": "Spotify Artist Similarity",
    "Popularity": "Spotify Popularity",
    "Spotify Track ID": "Spotify Track ID",
    "Match Method": "Spotify Match Method",
    "Match Score": "Spotify Match Score",
    "Search Strategy": "Spotify Search Strategy",
    "ISRC": "Spotify ISRC",
    "Album": "Spotify Album",
    "Release Date": "Spotify Release Date",
    "Duration (ms)": "Spotify Duration (ms)",
    "MusicBrainz ID": "Spotify MusicBrainz ID",
    "MBID Method": "Spotify MBID Method",
    "BPM": "Spotify BPM",
    "Key": "Spotify Key",
    "Scale": "Spotify Scale",
    "Key Full": "Spotify Key Full",
    "Energy Level": "Spotify Energy Level",
    "Danceability": "Spotify Danceability",
    "Vocal Type": "Spotify Vocal Type",
    "Mood Happy": "Spotify Mood Happy",
    "Mood Sad": "Spotify Mood Sad",
    "Mood Aggressive": "Spotify Mood Aggressive",
    "Mood Relaxed": "Spotify Mood Relaxed",
    "Mood Party": "Spotify Mood Party",
    "Genre": "Spotify Genre",
    "Genre Detail": "Spotify Genre Detail",
    "LastFM Tags": "Spotify LastFM Tags",
    "Vibe": "Spotify Vibe",
    "AB Source": "Spotify AB Source",
}


def read_csv(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write_csv(path: Path, headers: List[str], rows: List[Dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def norm(value: str) -> str:
    value = clean(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"\b(feat|featuring|ft)\.?\b.*$", "", value)
    value = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", value)
    value = re.sub(r"\bthe\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def keys_for_song(title: str, base_title: str, artist: str) -> List[Tuple[str, str]]:
    artist_key = norm(artist)
    keys = []
    for t in [title, base_title]:
        title_key = norm(t)
        if title_key and artist_key:
            key = (title_key, artist_key)
            if key not in keys:
                keys.append(key)
    return keys


def combine_list(existing: str, addition: str) -> str:
    seen = []
    for piece in re.split(r"\s*,\s*|\s*;\s*", clean(existing)):
        if piece and piece not in seen:
            seen.append(piece)
    if addition and addition not in seen:
        seen.append(addition)
    return ", ".join(seen)


def duration_from_ms(value: str) -> str:
    value = clean(value)
    if not value:
        return ""
    try:
        seconds = round(float(value) / 1000)
    except ValueError:
        return ""
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{sec:02d}"
    return f"{minutes}:{sec:02d}"


def year_from_release_date(value: str) -> str:
    match = re.match(r"^(\d{4})", clean(value))
    return match.group(1) if match else ""


def spotify_values(row: Dict[str, str]) -> Dict[str, str]:
    return {target: clean(row.get(source)) for source, target in SPOTIFY_MAP.items()}


def apply_spotify(row: Dict[str, str], sp: Dict[str, str]) -> None:
    values = spotify_values(sp)
    for col, value in values.items():
        if value:
            row[col] = value

    matched = clean(sp.get("Match Method")) != "not_found" and bool(clean(sp.get("Spotify Track ID")))
    if matched:
        row["Spotify Verified"] = "Yes"
    elif not row.get("Spotify Verified"):
        row["Spotify Verified"] = "No"

    if clean(sp.get("MusicBrainz ID")):
        row["MusicBrainz Verified"] = "Yes"

    fill_if_blank = {
        "Album": clean(sp.get("Album")),
        "Duration": duration_from_ms(sp.get("Duration (ms)", "")),
        "Genre": clean(sp.get("Genre")),
        "Year": year_from_release_date(sp.get("Release Date", "")),
        "Energy": clean(sp.get("Energy Level")),
        "BPM": clean(sp.get("BPM")),
        "Vibe": clean(sp.get("Vibe")),
    }
    for col, value in fill_if_blank.items():
        if value and not clean(row.get(col)):
            row[col] = value

    row["Source Files"] = combine_list(row.get("Source Files", ""), SPOTIFY_SOURCE)


def make_new_songdb_row(headers: List[str], sp: Dict[str, str]) -> Dict[str, str]:
    row = {h: "" for h in headers}
    title = clean(sp.get("Input Title")) or clean(sp.get("Matched Title"))
    artist = clean(sp.get("Input Artist")) or clean(sp.get("Matched Artist"))
    row.update({
        "Title": title,
        "Base Title": title,
        "Artist": artist,
        "Album": clean(sp.get("Album")),
        "Duration": duration_from_ms(sp.get("Duration (ms)", "")),
        "Genre": clean(sp.get("Genre")),
        "Year": year_from_release_date(sp.get("Release Date", "")),
        "Cover Song": "No",
        "Source Files": SPOTIFY_SOURCE,
        "Original Data": "Spotify Track ID: {} | Popularity: {} | Match Method: {} | LastFM Tags: {}".format(
            clean(sp.get("Spotify Track ID")),
            clean(sp.get("Popularity")),
            clean(sp.get("Match Method")),
            clean(sp.get("LastFM Tags")),
        ),
        "Energy": clean(sp.get("Energy Level")),
        "BPM": clean(sp.get("BPM")),
        "Vibe": clean(sp.get("Vibe")),
        "Spotify Verified": "Yes" if clean(sp.get("Match Method")) != "not_found" and clean(sp.get("Spotify Track ID")) else "No",
        "MusicBrainz Verified": "Yes" if clean(sp.get("MusicBrainz ID")) else "",
    })
    apply_spotify(row, sp)
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge Spotify ranker output into SongDB.")
    parser.add_argument("--main", type=Path, default=DEFAULT_MAIN)
    parser.add_argument("--spotify-csv", type=Path, default=DEFAULT_SPOTIFY)
    parser.add_argument("--summary", type=Path, default=DEFAULT_EXPORTS / "spotify_import_summary.json")
    args = parser.parse_args()

    headers, main_rows = read_csv(args.main)
    _, spotify_rows = read_csv(args.spotify_csv)
    for col in SPOTIFY_COLUMNS:
        if col not in headers:
            headers.append(col)
    for row in main_rows:
        for col in headers:
            row.setdefault(col, "")

    index: Dict[Tuple[str, str], List[Dict[str, str]]] = {}
    for row in main_rows:
        for key in keys_for_song(row.get("Title", ""), row.get("Base Title", ""), row.get("Artist", "")):
            index.setdefault(key, []).append(row)

    matched_spotify_rows = 0
    updated_database_rows = 0
    appended_rows = 0
    unmatched_spotify_rows = []
    seen_updated_row_ids = set()

    for sp in spotify_rows:
        sp_keys = keys_for_song(sp.get("Input Title", ""), sp.get("Matched Title", ""), sp.get("Input Artist", ""))
        targets = []
        seen_target_ids = set()
        for key in sp_keys:
            for row in index.get(key, []):
                ident = id(row)
                if ident not in seen_target_ids:
                    targets.append(row)
                    seen_target_ids.add(ident)
        if targets:
            matched_spotify_rows += 1
            for row in targets:
                apply_spotify(row, sp)
                row_id = id(row)
                if row_id not in seen_updated_row_ids:
                    updated_database_rows += 1
                    seen_updated_row_ids.add(row_id)
        else:
            new_row = make_new_songdb_row(headers, sp)
            main_rows.append(new_row)
            appended_rows += 1
            unmatched_spotify_rows.append({
                "Input Title": clean(sp.get("Input Title")),
                "Input Artist": clean(sp.get("Input Artist")),
                "Spotify Track ID": clean(sp.get("Spotify Track ID")),
                "Popularity": clean(sp.get("Popularity")),
                "Match Method": clean(sp.get("Match Method")),
            })
            for key in keys_for_song(new_row.get("Title", ""), new_row.get("Base Title", ""), new_row.get("Artist", "")):
                index.setdefault(key, []).append(new_row)

    write_csv(args.main, headers, main_rows)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    unmatched_path = args.summary.with_name("spotify_import_appended_rows.csv")
    write_csv(unmatched_path, ["Input Title", "Input Artist", "Spotify Track ID", "Popularity", "Match Method"], unmatched_spotify_rows)
    summary = {
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "main_database": str(args.main),
        "spotify_csv": str(args.spotify_csv),
        "input_database_rows": len(main_rows) - appended_rows,
        "spotify_rows": len(spotify_rows),
        "matched_spotify_rows": matched_spotify_rows,
        "updated_database_rows": updated_database_rows,
        "appended_rows": appended_rows,
        "output_database_rows": len(main_rows),
        "spotify_verified_rows": sum(1 for r in main_rows if clean(r.get("Spotify Verified")) == "Yes"),
        "musicbrainz_verified_rows": sum(1 for r in main_rows if clean(r.get("MusicBrainz Verified")) == "Yes"),
        "added_spotify_columns": SPOTIFY_COLUMNS,
        "appended_rows_csv": str(unmatched_path),
    }
    args.summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

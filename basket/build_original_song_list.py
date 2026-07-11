from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SONG_DATA = ROOT / "basket" / "Song_Data.csv"
DEFAULT_COVER_LIST = ROOT / "basket" / "listcoversongs.csv"
DEFAULT_OUTPUT = ROOT / "basket" / "original_songs.csv"


def normalize(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def load_cover_pairs(path: Path) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            title = normalize(row.get("title"))
            artist = normalize(row.get("artist"))
            if title and artist:
                pairs.add((title, artist))
    return pairs


def should_remove(row: dict[str, str], cover_pairs: set[tuple[str, str]]) -> bool:
    candidates = [
        (row.get("Title"), row.get("Artist")),
        (row.get("Base Title"), row.get("Artist")),
        (row.get("Title"), row.get("Covering Artist")),
        (row.get("Base Title"), row.get("Covering Artist")),
    ]
    for title, artist in candidates:
        key = (normalize(title), normalize(artist))
        if key in cover_pairs:
            return True
    return False


def build_original_song_list(song_data_path: Path, cover_list_path: Path, output_path: Path) -> tuple[int, int]:
    cover_pairs = load_cover_pairs(cover_list_path)

    with song_data_path.open("r", newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames or []
        kept_rows: list[dict[str, str]] = []
        kept = removed = 0
        for row in reader:
            if should_remove(row, cover_pairs):
                removed += 1
                continue
            kept_rows.append(row)
            kept += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept_rows)

    return kept, removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an originals-only Song_Data CSV by removing cover rows.")
    parser.add_argument("--song-data", default=str(DEFAULT_SONG_DATA), help="Input Song_Data.csv path.")
    parser.add_argument("--covers", default=str(DEFAULT_COVER_LIST), help="Input listcoversongs.csv path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output CSV path.")
    args = parser.parse_args()

    kept, removed = build_original_song_list(Path(args.song_data), Path(args.covers), Path(args.output))
    print(f"KEPT\t{kept}")
    print(f"REMOVED\t{removed}")
    print(f"OUTPUT\t{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

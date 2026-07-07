#!/usr/bin/env python3
"""Add Spotify title/artist/album context to skipped review conflicts."""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW_CSV = PROJECT_DIR / "data" / "exports" / "codex" / "active_main_patch_skipped_review.csv"
DEFAULT_SUMMARY_JSON = PROJECT_DIR / "data" / "exports" / "codex" / "spotify_conflict_review_enrichment_summary.json"
DEFAULT_CACHE_CSV = PROJECT_DIR / "data" / "exports" / "codex" / "spotify_conflict_track_metadata_cache.csv"
BACKUP_DIR = PROJECT_DIR / "data" / "backups" / "codex_review_enrichment"

CONFLICT_REASON = "active Spotify ID differs from active Spotify Track ID; manual review required"
TRACK_ID_FIELDS = {
    "Active": "Active Value",
    "Candidate": "Candidate Value",
    "Staged": "Staged Value",
}
METADATA_COLUMNS = [
    "Active Spotify Title",
    "Active Spotify Artist",
    "Active Spotify Album",
    "Candidate Spotify Title",
    "Candidate Spotify Artist",
    "Candidate Spotify Album",
    "Staged Spotify Title",
    "Staged Spotify Artist",
    "Staged Spotify Album",
]


def clean(value: object) -> str:
    return str(value or "").strip()


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def request_json(url: str, *, headers: dict[str, str] | None = None, data: bytes | None = None) -> dict:
    request = urllib.request.Request(url, headers=headers or {}, data=data)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def spotify_token() -> str:
    client_id = clean(os.getenv("SPOTIFY_CLIENT_ID"))
    client_secret = clean(os.getenv("SPOTIFY_CLIENT_SECRET"))
    if not client_id or not client_secret:
        raise RuntimeError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set.")

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    payload = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode("ascii")
    response = request_json(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=payload,
    )
    return clean(response.get("access_token"))


def chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def fetch_tracks(track_ids: list[str], token: str) -> dict[str, dict[str, str]]:
    metadata: dict[str, dict[str, str]] = {}
    headers = {"Authorization": f"Bearer {token}"}
    for group in chunks(track_ids, 50):
        query = urllib.parse.urlencode({"ids": ",".join(group)})
        url = f"https://api.spotify.com/v1/tracks?{query}"
        while True:
            try:
                response = request_json(url, headers=headers)
                break
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    retry_after = int(exc.headers.get("Retry-After", "1"))
                    time.sleep(retry_after)
                    continue
                raise
        for track in response.get("tracks", []):
            if not track:
                continue
            track_id = clean(track.get("id"))
            artists = "; ".join(clean(artist.get("name")) for artist in track.get("artists", []) if clean(artist.get("name")))
            album = track.get("album") or {}
            metadata[track_id] = {
                "Spotify Track ID": track_id,
                "Spotify Title": clean(track.get("name")),
                "Spotify Artist": artists,
                "Spotify Album": clean(album.get("name")),
            }
    return metadata


def add_metadata(rows: list[dict[str, str]], metadata: dict[str, dict[str, str]]) -> int:
    updated_rows = 0
    for row in rows:
        if clean(row.get("Reason")) != CONFLICT_REASON:
            for column in METADATA_COLUMNS:
                row.setdefault(column, "")
            continue
        updated_rows += 1
        for label, id_field in TRACK_ID_FIELDS.items():
            info = metadata.get(clean(row.get(id_field)), {})
            row[f"{label} Spotify Title"] = clean(info.get("Spotify Title"))
            row[f"{label} Spotify Artist"] = clean(info.get("Spotify Artist"))
            row[f"{label} Spotify Album"] = clean(info.get("Spotify Album"))
    return updated_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich Spotify conflict review rows with track metadata.")
    parser.add_argument("--review-csv", type=Path, default=DEFAULT_REVIEW_CSV)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--cache-csv", type=Path, default=DEFAULT_CACHE_CSV)
    args = parser.parse_args()

    fieldnames, rows = read_rows(args.review_csv)
    conflict_rows = [row for row in rows if clean(row.get("Reason")) == CONFLICT_REASON]
    track_ids = sorted(
        {
            clean(row.get(field))
            for row in conflict_rows
            for field in TRACK_ID_FIELDS.values()
            if clean(row.get(field))
        }
    )

    token = spotify_token()
    metadata = fetch_tracks(track_ids, token)
    missing_ids = sorted(set(track_ids) - set(metadata))

    backup_path = BACKUP_DIR / datetime.now().strftime("%Y%m%d_%H%M%S") / args.review_csv.name
    backup_path.parent.mkdir(parents=True, exist_ok=False)
    shutil.copy2(args.review_csv, backup_path)

    output_fields = list(fieldnames)
    for column in METADATA_COLUMNS:
        if column not in output_fields:
            output_fields.append(column)

    enriched_conflict_rows = add_metadata(rows, metadata)
    write_rows(args.review_csv, output_fields, rows)

    cache_fields = ["Spotify Track ID", "Spotify Title", "Spotify Artist", "Spotify Album"]
    write_rows(args.cache_csv, cache_fields, [metadata[track_id] for track_id in sorted(metadata)])

    summary = {
        "generated_at": datetime.now().isoformat(),
        "review_csv": str(args.review_csv),
        "backup_path": str(backup_path),
        "cache_csv": str(args.cache_csv),
        "conflict_rows": len(conflict_rows),
        "enriched_conflict_rows": enriched_conflict_rows,
        "unique_track_ids": len(track_ids),
        "metadata_rows": len(metadata),
        "missing_track_ids": missing_ids,
        "added_columns": METADATA_COLUMNS,
    }
    args.summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import argparse
import csv
import json
import os
import urllib.parse
from typing import Any
from pathlib import Path

import requests
import yt_dlp

from src.config import paths


def get_spotify_token(session: requests.Session) -> str | None:
    client_id = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None
    try:
        response = session.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except requests.RequestException:
        pass
    return None


def fetch_spotify(title: str, artist: str) -> dict[str, Any] | None:
    session = requests.Session()
    token = get_spotify_token(session)
    if not token:
        return {"error": "No Spotify credentials"}

    q = f"track:{title} artist:{artist}"
    try:
        response = session.get(
            f"https://api.spotify.com/v1/search?q={urllib.parse.quote(q)}&type=track&limit=5",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}
    return None


def fetch_itunes(title: str, artist: str) -> dict[str, Any] | None:
    try:
        response = requests.get(
            f"https://itunes.apple.com/search?term={urllib.parse.quote(f'{artist} {title}')}&media=music&limit=5",
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}
    return None


def fetch_musicbrainz(title: str, artist: str) -> dict[str, Any] | None:
    user_agent = os.getenv("MUSICBRAINZ_USER_AGENT", "MusicDBVerifier/1.0").strip()
    query = f'recording:"{title}" AND artist:"{artist}"'
    try:
        response = requests.get(
            f"https://musicbrainz.org/ws/2/recording/?query={urllib.parse.quote(query)}&fmt=json",
            headers={"User-Agent": user_agent},
            timeout=15,
        )
        if response.status_code == 200:
            return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}
    return None


def fetch_discogs(title: str, artist: str) -> dict[str, Any] | None:
    token = os.getenv("DISCOGS_TOKEN", "").strip()
    if not token:
        return {"error": "No Discogs credentials"}
    try:
        response = requests.get(
            "https://api.discogs.com/database/search"
            f"?track={urllib.parse.quote(title)}&artist={urllib.parse.quote(artist)}&token={urllib.parse.quote(token)}",
            headers={"User-Agent": "MusicDBVerifier/1.0"},
            timeout=15,
        )
        if response.status_code == 200:
            return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}
    return None


def fetch_youtube(title: str, artist: str) -> dict[str, Any] | None:
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'extract_flat': True,
        'quiet': True,
    }
    query = f"ytsearch5:{artist} {title}"
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                # Sanitize the output to avoid huge dumps
                entries = []
                for entry in info['entries']:
                    entries.append({
                        'id': entry.get('id'),
                        'title': entry.get('title'),
                        'uploader': entry.get('uploader'),
                        'duration': entry.get('duration'),
                        'view_count': entry.get('view_count'),
                        'url': entry.get('url'),
                    })
                return {"entries": entries}
    except Exception as e:
        return {"error": str(e)}
    return None


def write_csv(data: dict | None, filename: Path):
    if not data or "error" in data:
        print(f"Skipping {filename.name} due to error or missing data: {data}")
        return

    filename.parent.mkdir(parents=True, exist_ok=True)

    # Very basic flattening for the CSVs
    rows = []

    if "tracks" in data and "items" in data["tracks"]: # Spotify
        for item in data["tracks"]["items"]:
            rows.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "artist": item["artists"][0]["name"] if item.get("artists") else "",
                "album": item["album"]["name"] if item.get("album") else "",
                "raw_json": json.dumps(item)
            })
    elif "results" in data: # iTunes, Discogs
        for item in data["results"]:
            rows.append({
                "id": item.get("trackId") or item.get("id"),
                "name": item.get("trackName") or item.get("title"),
                "artist": item.get("artistName") or "",
                "raw_json": json.dumps(item)
            })
    elif "recordings" in data: # MusicBrainz
        for item in data["recordings"]:
            rows.append({
                "id": item.get("id"),
                "name": item.get("title"),
                "artist": item["artist-credit"][0]["name"] if item.get("artist-credit") else "",
                "raw_json": json.dumps(item)
            })
    elif "entries" in data: # YouTube
        for item in data["entries"]:
            rows.append({
                "id": item.get("id"),
                "name": item.get("title"),
                "artist": item.get("uploader"),
                "raw_json": json.dumps(item)
            })

    if not rows:
        print(f"No parseable items found to write for {filename.name}")
        return

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Fetch metadata for a song from various services.")
    parser.add_argument("--title", required=True, help="Song title")
    parser.add_argument("--artist", required=True, help="Song artist")
    args = parser.parse_args()

    project_paths = paths()

    safe_title = "".join(c for c in args.title if c.isalnum() or c in " _-")
    safe_artist = "".join(c for c in args.artist if c.isalnum() or c in " _-")
    base_name = f"{safe_artist}_{safe_title}.csv".replace(" ", "_")

    mb_data = fetch_musicbrainz(args.title, args.artist)
    write_csv(mb_data, project_paths.basket_dir / "musicbrainz" / base_name)

    yt_data = fetch_youtube(args.title, args.artist)
    write_csv(yt_data, project_paths.basket_dir / "youtube_music" / base_name)

    sp_data = fetch_spotify(args.title, args.artist)
    write_csv(sp_data, project_paths.basket_dir / "spotify" / base_name)

    dc_data = fetch_discogs(args.title, args.artist)
    write_csv(dc_data, project_paths.basket_dir / "discogs" / base_name)

    it_data = fetch_itunes(args.title, args.artist)
    write_csv(it_data, project_paths.basket_dir / "itunes" / base_name)


if __name__ == "__main__":
    main()

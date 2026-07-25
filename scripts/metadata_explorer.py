import argparse
import json
import os
import re
import urllib.parse
from typing import Any

import requests
import cloudscraper
import yt_dlp
from bs4 import BeautifulSoup


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


def fetch_amazon_music(title: str, artist: str) -> dict[str, Any] | None:
    scraper = cloudscraper.create_scraper()
    query = urllib.parse.quote_plus(f"{artist} {title} music")
    url = f"https://www.amazon.com/s?k={query}&i=digital-music"

    try:
        response = scraper.get(url, timeout=15)
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}"}

        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        for item in soup.select('div[data-component-type="s-search-result"]'):
            title_el = item.select_one('h2 a span')
            author_el = item.select_one('.a-row.a-size-base.a-color-secondary .a-size-base')
            if title_el:
                results.append({
                    "title": title_el.text.strip(),
                    "artist": author_el.text.strip() if author_el else "Unknown"
                })
                if len(results) >= 5:
                    break
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Fetch metadata for a song from various services.")
    parser.add_argument("--title", required=True, help="Song title")
    parser.add_argument("--artist", required=True, help="Song artist")
    args = parser.parse_args()

    results = {
        "query": {
            "title": args.title,
            "artist": args.artist,
        },
        "sources": {}
    }

    results["sources"]["spotify"] = fetch_spotify(args.title, args.artist)
    results["sources"]["itunes"] = fetch_itunes(args.title, args.artist)
    results["sources"]["musicbrainz"] = fetch_musicbrainz(args.title, args.artist)
    results["sources"]["discogs"] = fetch_discogs(args.title, args.artist)
    results["sources"]["youtube"] = fetch_youtube(args.title, args.artist)
    results["sources"]["amazon"] = fetch_amazon_music(args.title, args.artist)

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()

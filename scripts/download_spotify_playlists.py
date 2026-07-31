#!/usr/bin/env python3
"""Script to download Spotify playlists as CSV files."""

import argparse
import csv
import logging
import os
import re
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def clean_filename(name: str) -> str:
    """Clean playlist name to be a valid filename."""
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name.strip()


def download_playlists(output_dir: Path) -> None:
    """Download the user's Spotify playlists and save them as CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Requires SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, and SPOTIPY_REDIRECT_URI
    # to be set in the environment or passed directly.
    # It might use the existing SPOTIFY_CLIENT_ID variables if present.
    client_id = os.environ.get("SPOTIFY_CLIENT_ID") or os.environ.get(
        "SPOTIPY_CLIENT_ID"
    )
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET") or os.environ.get(
        "SPOTIPY_CLIENT_SECRET"
    )
    redirect_uri = os.environ.get("SPOTIPY_REDIRECT_URI", "http://localhost:8080")

    if not client_id or not client_secret:
        logging.error("Spotify client credentials not found in environment.")
        return

    os.environ["SPOTIPY_CLIENT_ID"] = client_id
    os.environ["SPOTIPY_CLIENT_SECRET"] = client_secret
    os.environ["SPOTIPY_REDIRECT_URI"] = redirect_uri

    scope = "playlist-read-private playlist-read-collaborative"
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

    logging.info("Fetching playlists...")
    playlists = sp.current_user_playlists()

    if not playlists or "items" not in playlists:
        logging.info("No playlists found.")
        return

    while playlists:
        for i, playlist in enumerate(playlists["items"]):
            name = playlist["name"]
            playlist_id = playlist["id"]
            owner = playlist["owner"]["display_name"]

            logging.info(f"Downloading playlist: {name} by {owner}")

            filename = clean_filename(name) + ".csv"
            filepath = output_dir / filename

            with filepath.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Track Name",
                        "Artist",
                        "Album",
                        "Added At",
                        "Added By",
                        "Duration (ms)",
                        "Spotify URI",
                        "ISRC",
                    ]
                )

                tracks = sp.playlist_items(playlist_id, additional_types=("track",))
                while tracks:
                    for item in tracks["items"]:
                        track = item.get("track")
                        if not track or track.get("is_local"):
                            # Skip local tracks for now or add them with missing info
                            continue

                        track_name = track.get("name", "")
                        artists = ", ".join(
                            artist["name"] for artist in track.get("artists", [])
                        )
                        album = track.get("album", {}).get("name", "")
                        added_at = item.get("added_at", "")
                        added_by = item.get("added_by", {}).get("id", "")
                        duration = track.get("duration_ms", "")
                        uri = track.get("uri", "")
                        isrc = track.get("external_ids", {}).get("isrc", "")

                        writer.writerow(
                            [
                                track_name,
                                artists,
                                album,
                                added_at,
                                added_by,
                                duration,
                                uri,
                                isrc,
                            ]
                        )

                    if tracks["next"]:
                        tracks = sp.next(tracks)
                    else:
                        tracks = None

        if playlists["next"]:
            playlists = sp.next(playlists)
        else:
            playlists = None

    logging.info("Finished downloading playlists.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Spotify playlists to CSV.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/exports"),
        help="Directory to save the CSV files.",
    )
    args = parser.parse_args()

    try:
        download_playlists(args.output_dir)
    except Exception as e:
        logging.error(f"Failed to download playlists: {e}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

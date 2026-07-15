from __future__ import annotations

import csv
from pathlib import Path

import scripts.verify_youtube_music_takeout as verify_takeout


def write_takeout_export(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "videoID",
        "title",
        "artist",
        "year",
        "album",
        "genre",
        "release_date",
        "upload_date",
        "duration_seconds",
        "channel",
        "uploader",
        "categories",
        "tags",
        "description",
        "webpage_url",
        "metadata_lookup_url",
        "metadata_lookup_status",
        "source_playlist_count",
        "source_playlists",
        "source_files",
        "first_seen_playlist_video_creation_timestamp",
        "last_seen_playlist_video_creation_timestamp",
        "occurrence_count",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_build_verified_takeout_export_prefers_matched_metadata(tmp_path, monkeypatch):
    input_csv = tmp_path / "takeout.csv"
    output_csv = tmp_path / "verified.csv"
    unmatched_csv = tmp_path / "unmatched.csv"
    summary_json = tmp_path / "summary.json"
    cache_path = tmp_path / "cache.json"

    write_takeout_export(
        input_csv,
        [
            {
                "videoID": "vid-1",
                "title": "Song A",
                "artist": "Artist X",
                "year": "",
                "album": "",
                "genre": "",
                "release_date": "",
                "upload_date": "",
                "duration_seconds": "",
                "channel": "",
                "uploader": "",
                "categories": "",
                "tags": "",
                "description": "",
                "webpage_url": "",
                "metadata_lookup_url": "",
                "metadata_lookup_status": "ok",
                "source_playlist_count": "1",
                "source_playlists": "Playlist One",
                "source_files": "Playlist One-videos.csv",
                "first_seen_playlist_video_creation_timestamp": "",
                "last_seen_playlist_video_creation_timestamp": "",
                "occurrence_count": "1",
            },
            {
                "videoID": "vid-2",
                "title": "Unmatched Song",
                "artist": "Unknown Artist",
                "year": "",
                "album": "",
                "genre": "",
                "release_date": "",
                "upload_date": "",
                "duration_seconds": "",
                "channel": "",
                "uploader": "",
                "categories": "",
                "tags": "",
                "description": "",
                "webpage_url": "",
                "metadata_lookup_url": "",
                "metadata_lookup_status": "ok",
                "source_playlist_count": "1",
                "source_playlists": "Playlist Two",
                "source_files": "Playlist Two-videos.csv",
                "first_seen_playlist_video_creation_timestamp": "",
                "last_seen_playlist_video_creation_timestamp": "",
                "occurrence_count": "1",
            },
        ],
    )

    def fake_spotify(session, token, title, artist):
        if title == "Song A" and artist == "Artist X":
            return [
                {
                    "service": "Spotify",
                    "title": "Song A",
                    "artist": "Artist X",
                    "album": "Spotify Album",
                    "release_date": "2020-01-01",
                    "year": "2020",
                    "track_id": "sp-1",
                    "url": "https://open.spotify.com/track/sp-1",
                }
            ]
        return []

    def fake_itunes(session, title, artist):
        if title == "Song A" and artist == "Artist X":
            return [
                {
                    "service": "iTunes",
                    "title": "Song A",
                    "artist": "Artist X",
                    "album": "iTunes Album",
                    "genre": "Pop",
                    "release_date": "2020-01-02",
                    "year": "2020",
                    "track_id": "it-1",
                    "url": "https://music.apple.com/track/it-1",
                }
            ]
        return []

    monkeypatch.setattr(verify_takeout, "query_spotify", fake_spotify)
    monkeypatch.setattr(verify_takeout, "query_itunes", fake_itunes)
    monkeypatch.setattr(verify_takeout, "spotify_token", lambda session, log_path: "token")

    summary = verify_takeout.build_verified_takeout_export(
        input_csv,
        output_csv,
        unmatched_csv,
        summary_json,
        cache_path,
        workers=1,
    )

    assert summary["rows_with_title_artist"] == 2
    assert summary["rows_verified"] == 1
    assert summary["rows_unmatched"] == 1

    with output_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        verified_rows = list(csv.DictReader(handle))
    assert verified_rows[0]["title"] == "Song A"
    assert verified_rows[0]["genre"] == "Pop"
    assert verified_rows[0]["metadata_source"] == "iTunes"

    with unmatched_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        unmatched_rows = list(csv.DictReader(handle))
    assert unmatched_rows[0]["videoID"] == "vid-2"

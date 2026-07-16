from __future__ import annotations

import csv
from pathlib import Path

from src.youtube_music_takeout import build_takeout_export, build_takeout_song_export, match_takeout_export_to_recordings


def write_takeout_csv(path: Path, rows: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Video ID", "Playlist Video Creation Timestamp"])
        writer.writerows(rows)


def test_build_takeout_export_dedupes_and_tracks_playlists(tmp_path):
    takeout_dir = tmp_path / "takeout"
    write_takeout_csv(
        takeout_dir / "Playlist One-videos.csv",
        [
            ("vid-1", "2026-07-01T10:00:00+00:00"),
            ("vid-2", "2026-07-01T11:00:00+00:00"),
        ],
    )
    write_takeout_csv(
        takeout_dir / "Playlist Two-videos.csv",
        [
            ("vid-1", "2026-07-02T10:00:00+00:00"),
        ],
    )

    def fake_fetch(video_id: str) -> dict[str, str]:
        if video_id == "vid-1":
            return {
                "videoID": video_id,
                "title": "Song A",
                "artist": "Artist X",
                "year": "2020",
                "album": "Album A",
                "genre": "",
                "release_date": "20200101",
                "upload_date": "20200101",
                "duration_seconds": "123",
                "channel": "Artist X",
                "uploader": "Artist X",
                "categories": "Music",
                "tags": "",
                "description": "",
                "webpage_url": f"https://www.youtube.com/watch?v={video_id}",
                "metadata_lookup_url": f"https://music.youtube.com/watch?v={video_id}",
                "metadata_lookup_status": "ok",
            }
        return {
            "videoID": video_id,
            "title": "Song B",
            "artist": "Artist Y",
            "year": "2021",
            "album": "Album B",
            "genre": "",
            "release_date": "20210101",
            "upload_date": "20210101",
            "duration_seconds": "234",
            "channel": "Artist Y",
            "uploader": "Artist Y",
            "categories": "Music",
            "tags": "",
            "description": "",
            "webpage_url": f"https://www.youtube.com/watch?v={video_id}",
            "metadata_lookup_url": f"https://music.youtube.com/watch?v={video_id}",
            "metadata_lookup_status": "ok",
        }

    output_csv = tmp_path / "export.csv"
    cache_path = tmp_path / "cache.json"
    result = build_takeout_export(
        takeout_dir,
        output_csv,
        cache_path,
        workers=2,
        metadata_fetcher=fake_fetch,
    )

    assert result.summary["unique_video_ids"] == 2
    assert result.summary["metadata_lookups"] == 2
    rows_by_id = {row["videoID"]: row for row in result.rows}
    assert rows_by_id["vid-1"]["source_playlist_count"] == "2"
    assert "Playlist One" in rows_by_id["vid-1"]["source_playlists"]
    assert "Playlist Two" in rows_by_id["vid-1"]["source_playlists"]

    recordings = [
        {
            "Recording ID": "rec-1",
            "Song ID": "song-1",
            "Title": "Song A",
            "Canonical Title": "Song A",
            "Artist": "Artist X",
            "Canonical Artist": "Artist X",
        }
    ]
    match_result = match_takeout_export_to_recordings(result.rows, recordings)

    assert len(match_result.membership_rows) == 2
    assert len(match_result.unmatched_rows) == 1
    assert match_result.membership_rows[0]["Source"] == "YouTube Music Takeout"
    assert "videoID=vid-1" in match_result.membership_rows[0]["Notes"]


def test_build_takeout_song_export_projects_unique_song_rows(tmp_path):
    output_csv = tmp_path / "songs.csv"
    rows = [
        {
            "videoID": "vid-1",
            "title": "Song A",
            "artist": "Artist X",
            "album": "Album A",
            "year": "2020",
            "genre": "Pop",
        },
        {
            "videoID": "vid-1",
            "title": "Song A",
            "artist": "Artist X",
            "album": "Album A",
            "year": "2020",
            "genre": "Pop",
        },
    ]

    song_rows = build_takeout_song_export(rows, output_csv)

    assert len(song_rows) == 1
    assert song_rows[0]["youtube music song ID"] == "vid-1"
    assert song_rows[0]["title"] == "Song A"
    assert song_rows[0]["artist"] == "Artist X"
    assert song_rows[0]["album"] == "Album A"
    assert song_rows[0]["year"] == "2020"
    assert song_rows[0]["genre"] == "Pop"

    with output_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        exported = list(csv.DictReader(handle))
    assert exported == song_rows

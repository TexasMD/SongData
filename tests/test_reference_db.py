import csv
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from api.main import app
from src.config import paths
from src.reference_db import build_reference_db


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def make_temp_root() -> Path:
    root = Path.cwd() / "tmp" / f"test_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=False)
    return root


def write_antigravity_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE antigravity_cover_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_recording_id TEXT,
                title TEXT,
                artist TEXT,
                year TEXT,
                genre TEXT,
                album TEXT,
                tags TEXT,
                original_year TEXT,
                original_genre TEXT,
                original_album TEXT,
                mbid TEXT,
                source TEXT
            );
            CREATE TABLE antigravity_external_link_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id TEXT,
                site TEXT,
                verified_url TEXT,
                search_url TEXT,
                match_type TEXT,
                confidence TEXT,
                notes TEXT
            );
            CREATE TABLE antigravity_mood_event_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id TEXT,
                suggested_mood_tags TEXT,
                suggested_event_tags TEXT,
                suggested_situation_tags TEXT,
                source_url TEXT,
                confidence TEXT,
                notes TEXT
            );
            CREATE TABLE antigravity_performance_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id TEXT,
                bpm TEXT,
                song_key TEXT,
                tuning TEXT,
                capo TEXT,
                guitar_difficulty TEXT,
                bass_difficulty TEXT,
                drum_difficulty TEXT,
                vocal_range TEXT,
                instrumentation TEXT,
                arrangement_notes TEXT,
                source_url TEXT,
                confidence TEXT,
                notes TEXT
            );
            """
        )
        conn.executemany(
            "INSERT INTO antigravity_cover_candidates (original_recording_id, title, artist, year, genre, album, tags, original_year, original_genre, original_album, mbid, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [("R1", "Bye Bye Bye", "Further Seems Forever", "2001", "Rock / Pop", "", "", "", "", "", "", "WhoSampled")],
        )
        conn.executemany(
            "INSERT INTO antigravity_external_link_suggestions (recording_id, site, verified_url, search_url, match_type, confidence, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [("R1", "SecondHandSongs", "", "https://secondhandsongs.example", "Search Query", "Low", "note")],
        )
        conn.executemany(
            "INSERT INTO antigravity_mood_event_suggestions (recording_id, suggested_mood_tags, suggested_event_tags, suggested_situation_tags, source_url, confidence, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [("R1", "aggressive", "workout", "road_trip", "https://musicbrainz.example", "High", "note")],
        )
        conn.executemany(
            "INSERT INTO antigravity_performance_suggestions (recording_id, bpm, song_key, tuning, capo, guitar_difficulty, bass_difficulty, drum_difficulty, vocal_range, instrumentation, arrangement_notes, source_url, confidence, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [("R1", "120", "Am", "Standard", "0", "2", "2", "2", "C3-E4", "Guitar, Bass", "Note", "https://spotify.example", "High", "note")],
        )


class TestReferenceDb(unittest.TestCase):
    def test_build_reference_db_indexes_sources_and_identifiers(self):
        root = make_temp_root()
        configured = paths(root)

        write_csv(
            configured.data_dir / "source_registry.csv",
            [
                "Source",
                "Kind",
                "Credential Required",
                "Credential Environment Variables",
                "Used By",
                "Status",
                "Notes",
            ],
            [
                [
                    "Spotify Web API",
                    "metadata/verification",
                    "Yes",
                    "SPOTIFY_CLIENT_ID; SPOTIFY_CLIENT_SECRET",
                    "tests",
                    "env_required",
                    "Credentialed source.",
                ]
            ],
        )
        write_csv(
            configured.data_dir / "source_metadata_matrix.csv",
            [
                "Source",
                "Primary Metadata",
                "Identifier Fields",
                "Best Match Keys",
                "Default Confidence",
                "Notes",
            ],
            [
                [
                    "Spotify Web API",
                    "track title artist album release date popularity artwork duration explicitness and ISRC",
                    "Spotify Track ID Spotify Album ID Spotify Artist ID",
                    "Exact Spotify track ID or exact title artist album plus ISRC",
                    "High",
                    "Credentialed source; prefer exact IDs when available.",
                ]
            ],
        )
        write_csv(
            configured.songs_csv,
            [
                "Song ID",
                "Canonical Title",
                "Canonical Artist",
                "MusicBrainz Work ID",
                "Primary Recording ID",
                "Preferred Primary Release",
                "First Published Year",
                "Notes",
            ],
            [["S1", "Song", "Artist", "W1", "R1", "Album", "1999", "song note"]],
        )
        write_csv(
            configured.recordings_csv,
            [
                "Recording ID",
                "Song ID",
                "Title",
                "Artist",
                "Album",
                "Release Year",
                "Spotify Track ID",
                "Legacy Spotify ID",
                "Spotify ISRC",
                "MusicBrainz Recording ID",
                "Spotify Verified",
                "MusicBrainz Verified",
                "Notes",
            ],
            [[
                "R1",
                "S1",
                "Song",
                "Artist",
                "Album",
                "1999",
                "spotify-track-1",
                "legacy-spotify-1",
                "ISRC123",
                "mbid-1",
                "Yes",
                "Yes",
                "rec note",
            ]],
        )
        write_csv(
            configured.external_links_csv,
            [
                "Recording ID",
                "Song ID",
                "Site",
                "Search URL",
                "Verified URL",
                "Link Type",
                "Link Status",
                "Preferred Match Rule",
                "Last Checked",
                "Notes",
            ],
            [[
                "R1",
                "S1",
                "SecondHandSongs",
                "https://example.com/search",
                "https://example.com/verified",
                "covers/originals/search",
                "verified_exact",
                "exact title/artist",
                "2026-07-13T00:00:00Z",
                "link note",
            ]],
        )
        write_csv(
            configured.exports_dir / "codex" / "youtube_music_takeout_verified.csv",
            [
                "videoID",
                "title",
                "artist",
                "year",
                "album",
                "genre",
                "metadata_source",
                "match_score",
                "match_status",
                "spotify_track_id",
                "spotify_url",
                "itunes_track_id",
                "itunes_url",
                "source_title",
                "source_artist",
                "source_year",
                "source_album",
                "source_genre",
                "source_release_date",
                "source_upload_date",
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
                "verified_candidate_note",
            ],
            [[
                "yt-1",
                "Song Title",
                "Artist",
                "1999",
                "Album",
                "Rock",
                "iTunes",
                "1.0",
                "matched",
                "sp-1",
                "https://spotify.example",
                "it-1",
                "https://itunes.example",
                "Source Title",
                "Source Artist",
                "1999",
                "Source Album",
                "Genre",
                "19990101",
                "19990102",
                "180",
                "Channel",
                "Uploader",
                "Music",
                "tag1 | tag2",
                "Description",
                "https://youtube.example",
                "https://music.youtube.example",
                "ok",
                "1",
                "Playlist 1",
                "source.csv",
                "2024-01-01T00:00:00Z",
                "2024-01-01T00:00:00Z",
                "1",
                "verified note",
            ]],
        )
        write_csv(
            configured.exports_dir / "codex" / "youtube_music_takeout_unmatched.csv",
            ["videoID", "title", "artist", "year", "album", "genre", "source_playlists", "metadata_lookup_status", "match_status"],
            [["yt-2", "Unmatched Song", "Artist", "2000", "Album", "Pop", "Playlist 2", "ok", "unmatched"]],
        )
        write_csv(
            configured.staging_dir / "jules" / "antigravity_cover_candidates.csv",
            ["id", "original_recording_id", "title", "artist", "year", "genre", "album", "tags", "original_year", "original_genre", "original_album", "mbid", "source"],
            [["1", "R1", "Bye Bye Bye", "Further Seems Forever", "2001", "Rock / Pop", "", "", "", "", "", "", "WhoSampled"]],
        )
        write_antigravity_db(configured.staging_dir / "jules" / "music_antigravity_review.sqlite")
        write_csv(
            configured.active_main_csv,
            [
                "Title",
                "Base Title",
                "Artist",
                "Album",
                "Duration",
                "Genre",
                "Year",
                "Original Artist",
                "Cover Song",
                "Orig Artist",
                "Covering Artist",
                "Source Files",
                "Original Data",
                "Energy",
                "BPM",
                "Vibe",
                "Discogs Verified",
                "Spotify Verified",
                "MusicBrainz Verified",
                "iTunes Verified",
                "Spotify ID",
                "Playlists",
                "Spotify Track ID",
                "Spotify MusicBrainz ID",
            ],
            [[
                "Song Title",
                "Song Title",
                "Artist",
                "Album",
                "3:00",
                "Genre",
                "1999",
                "",
                "No",
                "",
                "",
                "source.csv",
                "Song Title | Artist",
                "High",
                "120",
                "Vibe",
                "Yes",
                "Yes",
                "Yes",
                "No",
                "spotify-legacy",
                "Playlist 1",
                "spotify-track-1",
                "mbid-1",
            ]],
        )

        summary = build_reference_db(configured)

        self.assertEqual(summary["source_registry_rows"], 1)
        self.assertEqual(summary["source_metadata_matrix_rows"], 1)
        self.assertGreaterEqual(summary["reference_entities_rows"], 5)
        self.assertGreaterEqual(summary["reference_identifiers_rows"], 8)
        self.assertGreaterEqual(summary["source_observation_rows"], 20)
        self.assertTrue(configured.reference_db_path.exists())

        with sqlite3.connect(configured.reference_db_path) as conn:
            source_count = conn.execute("SELECT COUNT(*) FROM source_registry").fetchone()[0]
            identifier_count = conn.execute("SELECT COUNT(*) FROM reference_identifiers WHERE source = 'Spotify'").fetchone()[0]
            url_count = conn.execute("SELECT COUNT(*) FROM reference_identifiers WHERE value_kind = 'url'").fetchone()[0]
            whosampled_identifier_count = conn.execute("SELECT COUNT(*) FROM reference_identifiers WHERE source = 'WhoSampled'").fetchone()[0]
            secondhandsongs_identifier_count = conn.execute("SELECT COUNT(*) FROM reference_identifiers WHERE source = 'SecondHandSongs'").fetchone()[0]
            antigravity_identifier_count = conn.execute("SELECT COUNT(*) FROM reference_identifiers WHERE source = 'Antigravity'").fetchone()[0]
            title_count = conn.execute("SELECT COUNT(*) FROM reference_entities WHERE entity_kind = 'title'").fetchone()[0]
            artist_count = conn.execute("SELECT COUNT(*) FROM reference_entities WHERE entity_kind = 'artist'").fetchone()[0]
            album_count = conn.execute("SELECT COUNT(*) FROM reference_entities WHERE entity_kind = 'album'").fetchone()[0]
            observation_count = conn.execute("SELECT COUNT(*) FROM source_observations").fetchone()[0]

        self.assertEqual(source_count, 1)
        self.assertEqual(identifier_count, 2)
        self.assertEqual(url_count, 5)
        self.assertEqual(whosampled_identifier_count, 1)
        self.assertEqual(secondhandsongs_identifier_count, 3)
        self.assertEqual(antigravity_identifier_count, 2)
        self.assertEqual(title_count, 1)
        self.assertEqual(artist_count, 1)
        self.assertEqual(album_count, 1)
        self.assertGreaterEqual(observation_count, 40)

    def test_reference_api_exposes_source_rows(self):
        root = make_temp_root()
        configured = paths(root)

        write_csv(
            configured.data_dir / "source_registry.csv",
            [
                "Source",
                "Kind",
                "Credential Required",
                "Credential Environment Variables",
                "Used By",
                "Status",
                "Notes",
            ],
            [["MusicBrainz API", "metadata/verification", "No", "MUSICBRAINZ_USER_AGENT", "tests", "user_agent_required", "Public lookup source."]],
        )
        write_csv(
            configured.data_dir / "source_metadata_matrix.csv",
            [
                "Source",
                "Primary Metadata",
                "Identifier Fields",
                "Best Match Keys",
                "Default Confidence",
                "Notes",
            ],
            [["MusicBrainz API", "recording release artist work relationships and ISRC", "Recording ID Release ID Work ID", "Exact MBID or ISRC", "High", "Open canonical backbone."]],
        )
        write_csv(
            configured.songs_csv,
            ["Song ID", "Canonical Title", "Canonical Artist", "Notes"],
            [["S1", "Song", "Artist", ""]],
        )
        write_csv(
            configured.recordings_csv,
            ["Recording ID", "Song ID", "Title", "Artist", "Album", "Release Year", "MusicBrainz Recording ID", "MusicBrainz Verified", "Notes"],
            [["R1", "S1", "Song", "Artist", "Album", "1999", "mbid-1", "Yes", ""]],
        )
        write_csv(
            configured.external_links_csv,
            ["Recording ID", "Song ID", "Site", "Search URL", "Verified URL", "Link Type", "Link Status", "Preferred Match Rule", "Last Checked", "Notes"],
            [["R1", "S1", "MusicBrainz", "https://example.com/search", "", "recording", "verified_exact", "exact", "", ""]],
        )
        write_csv(
            configured.active_main_csv,
            [
                "Title",
                "Base Title",
                "Artist",
                "Album",
                "Duration",
                "Genre",
                "Year",
                "Original Artist",
                "Cover Song",
                "Orig Artist",
                "Covering Artist",
                "Source Files",
                "Original Data",
                "Energy",
                "BPM",
                "Vibe",
                "Discogs Verified",
                "Spotify Verified",
                "MusicBrainz Verified",
                "iTunes Verified",
                "Spotify ID",
                "Playlists",
                "Spotify Track ID",
                "Spotify MusicBrainz ID",
            ],
            [[
                "Song Title",
                "Song Title",
                "Artist",
                "Album",
                "3:00",
                "Genre",
                "1999",
                "",
                "No",
                "",
                "",
                "source.csv",
                "Song Title | Artist",
                "High",
                "120",
                "Vibe",
                "Yes",
                "Yes",
                "Yes",
                "No",
                "spotify-legacy",
                "Playlist 1",
                "spotify-track-1",
                "mbid-1",
            ]],
        )
        write_antigravity_db(configured.staging_dir / "jules" / "music_antigravity_review.sqlite")

        build_reference_db(configured)

        with patch("api.main.DEFAULT_REFERENCE_DB_PATH", configured.reference_db_path):
            client = TestClient(app)
            response = client.get("/api/reference/sources")
            obs_response = client.get("/api/reference/source-observations")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["source"], "MusicBrainz API")
        self.assertEqual(obs_response.status_code, 200)
        results = obs_response.json()["results"]
        self.assertTrue(any(row["source_name"] == "MusicDB" for row in results))
        self.assertTrue(any(row["source_name"] == "WhoSampled" for row in results))
        self.assertTrue(any(row["source_name"] == "SecondHandSongs" for row in results))


if __name__ == "__main__":
    unittest.main()

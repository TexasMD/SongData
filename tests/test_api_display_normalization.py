from __future__ import annotations

import pandas as pd
from fastapi.testclient import TestClient

import api.main as api_main


def test_api_recordings_normalizes_display_text(monkeypatch):
    monkeypatch.setattr(
        api_main,
        "execute_query",
        lambda query, params=None, db_path=None: pd.DataFrame(
            [
                {
                    "recording_id": "rec-1",
                    "title": "R%C3%9CF%C3%9CS DU SOL",
                    "artist": "Billy Idol - \xa0Rebel Yell",
                    "album": "La Femme D´Argent",
                    "version": "",
                    "release_year": 2018,
                    "duration": "2:14",
                    "genre": "",
                    "genre_detail": "",
                    "bpm": "",
                    "key": "",
                    "mood_tags": "",
                    "event_tags": "",
                    "situation_tags": "",
                    "playlists": "",
                    "crowd_energy": "",
                    "spotify_track_id": "",
                    "musicbrainz_recording_id": "",
                }
            ]
        ),
    )

    client = TestClient(api_main.app)
    response = client.get("/api/recordings")

    assert response.status_code == 200
    row = response.json()["results"][0]
    assert row["title"] == "RÜFÜS DU SOL"
    assert row["artist"] == "Billy Idol - Rebel Yell"
    assert row["album"] == "La Femme D'Argent"

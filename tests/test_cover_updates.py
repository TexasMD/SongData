from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

import api.main as api_main
from src.cover_update_service import CoverUpdateResult, run_cover_update


def test_run_cover_update_writes_stage_files_and_timestamps(tmp_path, monkeypatch):
    monkeypatch.setattr("src.cover_update_service.CODEx_STAGE_ROOT", tmp_path)
    monkeypatch.setattr(
        "src.cover_update_service.execute_query",
        lambda query, params=None, db_path=None: pd.DataFrame(
            [
                {
                    "recording_id": "rec-1",
                    "title": "Blackbird",
                    "artist": "The Beatles",
                    "release_year": 1968,
                }
            ]
        ),
    )

    def fake_scrape_covers(title, artist, original_year, on_source_checked=None):
        if on_source_checked:
            on_source_checked("MusicBrainz", "recording_search", "mb://recording", 2, "2026-07-10T00:00:00Z")
            on_source_checked("cover.info", "song_find", "ci://find", 1, "2026-07-10T00:00:01Z")
            on_source_checked("SecondHandSongs", "search_performance", "shs://search", 3, "2026-07-10T00:00:02Z")
            on_source_checked("WhoSampled", "track_search", "ws://search", 4, "2026-07-10T00:00:03Z")
        return [
            {
                "title": "Blackbird (Cover)",
                "artist": "Cover Artist",
                "original_title": title,
                "original_artist": artist,
                "original_year": original_year,
                "musicbrainz_recording_id": None,
                "source": "cover.info, SecondHandSongs",
                "cover_song": "Yes",
                "cover_genre": "Folk",
            }
        ]

    monkeypatch.setattr("src.cover_update_service.scrape_covers", fake_scrape_covers)

    result = run_cover_update(["rec-1"])
    assert result.run_dir.exists()
    assert len(result.covers) == 1
    assert len(result.source_query_checks) == 4

    csv_path = result.run_dir / "cover_relationship_candidates.csv"
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    assert list(df.columns) == [
        "original_recording_id",
        "title",
        "artist",
        "original_title",
        "original_artist",
        "original_year",
        "musicbrainz_recording_id",
        "source",
        "musicbrainz_last_checked_at",
        "coverinfo_last_checked_at",
        "secondhandsongs_last_checked_at",
        "whosampled_last_checked_at",
    ]
    row = df.iloc[0].to_dict()
    assert row["original_recording_id"] == "rec-1"
    assert row["coverinfo_last_checked_at"] == "2026-07-10T00:00:01Z"
    assert row["secondhandsongs_last_checked_at"] == "2026-07-10T00:00:02Z"
    assert row["whosampled_last_checked_at"] == "2026-07-10T00:00:03Z"


def test_cover_updates_endpoint_returns_stage_metadata(monkeypatch, tmp_path):
    fake = CoverUpdateResult(
        run_id="20260710T000000Z",
        run_dir=Path(tmp_path / "run"),
        recordings=[{"recording_id": "rec-1"}],
        covers=[{"title": "Blackbird (Cover)", "artist": "Cover Artist"}],
        source_query_checks=[{"recording_id": "rec-1", "source": "cover.info"}],
    )
    fake.run_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(api_main, "run_cover_update", lambda recording_ids: fake)

    client = TestClient(api_main.app)
    response = client.post("/api/cover_updates", json={"recording_ids": ["rec-1"]})
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "20260710T000000Z"
    assert body["stage_dir"].endswith("run")
    assert body["covers"][0]["title"] == "Blackbird (Cover)"

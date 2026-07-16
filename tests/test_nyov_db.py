import csv
import sqlite3
import zipfile
from pathlib import Path

from src.config import paths
from src.nyov_db import build_nyov_db
from src.commands.nyov_report import build_report
from src.commands import verify_nyov_batch
from src.commands.verify_nyov_batch import ProviderResult
from src.commands.nyov_verification_summary import build_summary


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def test_build_nyov_db_imports_seed_and_basket_evidence(tmp_path):
    basket = tmp_path / "basket"
    seed = basket / "MyMusicBasefiltered_fixed.csv"
    write_csv(
        seed,
        ["Title", "Artist", "Album"],
        [
            ["Electric Avenue", "Eddy Grant", "Killer On The Rampage"],
            ["Billie Jean", "Susan Wong", "511"],
        ],
    )
    write_csv(
        basket / "spotify.csv",
        ["Title", "Artist", "Album", "Spotify Track ID", "MusicBrainz ID"],
        [["Electric Avenue", "Eddy Grant", "Killer On The Rampage", "sp-1", "none"]],
    )
    (basket / "playlist.txt").write_text("Susan Wong - Billie Jean\n", encoding="utf-8")
    with zipfile.ZipFile(basket / "takeout.zip", "w") as archive:
        archive.writestr("Takeout/YouTube and YouTube Music/playlists/test-videos.csv", "Video ID,Title,Artist\nyt-1,Electric Avenue,Eddy Grant\n")

    configured = paths(tmp_path)
    summary = build_nyov_db(configured, seed_csv=seed, basket_dir=basket, output_db=tmp_path / "nyov.sqlite")

    assert summary["seed_entities"] == 2
    assert summary["source_observations"] >= 5
    assert summary["matched_observations"] >= 3
    assert summary["identifiers"] >= 2

    with sqlite3.connect(tmp_path / "nyov.sqlite") as conn:
        entities = conn.execute("SELECT seed_title, seed_artist FROM nyov_entities ORDER BY seed_title").fetchall()
        assert entities == [("Billie Jean", "Susan Wong"), ("Electric Avenue", "Eddy Grant")]
        identifiers = conn.execute("SELECT source_name, identifier_value FROM nyov_identifiers ORDER BY source_name").fetchall()
        assert ("Spotify", "sp-1") in identifiers
        assert ("YouTube Music", "yt-1") in identifiers
        assert ("MusicBrainz", "none") not in identifiers


def test_nyov_report_classifies_verification_candidates(tmp_path):
    basket = tmp_path / "basket"
    seed = basket / "MyMusicBasefiltered_fixed.csv"
    write_csv(
        seed,
        ["Title", "Artist", "Album"],
        [
            ["Electric Avenue", "Eddy Grant", "Killer On The Rampage"],
            ["Billie Jean", "Susan Wong", "511"],
        ],
    )
    write_csv(
        basket / "spotify.csv",
        ["Title", "Artist", "Album", "Spotify Track ID"],
        [["Electric Avenue", "Eddy Grant", "Killer On The Rampage", "sp-1"]],
    )
    write_csv(
        basket / "youtube.csv",
        ["Title", "Artist", "Album", "Video ID"],
        [["Electric Avenue", "Eddy Grant", "Killer On The Rampage", "yt-1"]],
    )

    configured = paths(tmp_path)
    db_path = tmp_path / "nyov.sqlite"
    build_nyov_db(configured, seed_csv=seed, basket_dir=basket, output_db=db_path)

    report = build_report(db_path, queue_limit=10)

    assert report["counts"]["nyov_entities"] == 2
    buckets = {row["next_step"]: row["entity_count"] for row in report["next_step_counts"]}
    assert buckets["candidate_dual_source_match"] == 1
    assert buckets["seed_only"] == 1
    assert report["verification_queue"][0]["seed_title"] == "Electric Avenue"
    assert report["verification_queue"][0]["next_step"] == "candidate_dual_source_match"
    assert len(report["verification_batch"]) == 1
    assert report["verification_batch"][0]["seed_title"] == "Electric Avenue"
    assert any(
        row["identifier_source"] == "Spotify" and row["identifier_value"] == "sp-1"
        for row in report["verification_batch_evidence"]
    )
    assert any(
        row["identifier_source"] == "YouTube Music" and row["identifier_value"] == "yt-1"
        for row in report["verification_batch_evidence"]
    )


def test_nyov_schema_has_field_level_verification_columns(tmp_path):
    basket = tmp_path / "basket"
    seed = basket / "MyMusicBasefiltered_fixed.csv"
    write_csv(seed, ["Title", "Artist", "Album"], [["Electric Avenue", "Eddy Grant", "Killer On The Rampage"]])

    configured = paths(tmp_path)
    db_path = tmp_path / "nyov.sqlite"
    build_nyov_db(configured, seed_csv=seed, basket_dir=basket, output_db=db_path)

    with sqlite3.connect(db_path) as conn:
        attempt_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(nyov_verification_attempts)").fetchall()
        }
        promotion_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(nyov_promotions)").fetchall()
        }

    assert {"provider_entity_type", "provider_entity_id", "title_match_status", "verifier_version"} <= attempt_columns
    assert {"target_field", "promoted_value", "verification_level", "evidence_json"} <= promotion_columns


def test_verify_nyov_batch_dry_run_does_not_insert_attempts(tmp_path):
    basket = tmp_path / "basket"
    seed = basket / "MyMusicBasefiltered_fixed.csv"
    write_csv(seed, ["Title", "Artist", "Album"], [["Electric Avenue", "Eddy Grant", "Killer On The Rampage"]])
    write_csv(
        basket / "spotify.csv",
        ["Title", "Artist", "Album", "Spotify Track ID"],
        [["Electric Avenue", "Eddy Grant", "Killer On The Rampage", "sp-1"]],
    )
    write_csv(
        basket / "youtube.csv",
        ["Title", "Artist", "Album", "Video ID"],
        [["Electric Avenue", "Eddy Grant", "Killer On The Rampage", "yt-1"]],
    )

    db_path = tmp_path / "nyov.sqlite"
    build_nyov_db(paths(tmp_path), seed_csv=seed, basket_dir=basket, output_db=db_path)

    summary = verify_nyov_batch.verify_batch(db_path, batch_limit=1, providers=["itunes"], write=False)

    assert summary["dry_run"] is True
    assert summary["candidate_rows"] == 1
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM nyov_verification_attempts").fetchone()[0] == 0


def test_verify_nyov_batch_inserts_provider_attempts(tmp_path, monkeypatch):
    basket = tmp_path / "basket"
    seed = basket / "MyMusicBasefiltered_fixed.csv"
    write_csv(seed, ["Title", "Artist", "Album"], [["Electric Avenue", "Eddy Grant", "Killer On The Rampage"]])
    write_csv(
        basket / "spotify.csv",
        ["Title", "Artist", "Album", "Spotify Track ID"],
        [["Electric Avenue", "Eddy Grant", "Killer On The Rampage", "sp-1"]],
    )
    write_csv(
        basket / "youtube.csv",
        ["Title", "Artist", "Album", "Video ID"],
        [["Electric Avenue", "Eddy Grant", "Killer On The Rampage", "yt-1"]],
    )

    db_path = tmp_path / "nyov.sqlite"
    build_nyov_db(paths(tmp_path), seed_csv=seed, basket_dir=basket, output_db=db_path)

    monkeypatch.setattr(verify_nyov_batch, "_session", lambda: object())
    monkeypatch.setattr(verify_nyov_batch, "_spotify_token", lambda session: "")
    monkeypatch.setattr(
        verify_nyov_batch,
        "query_itunes",
        lambda session, title, artist: [
            ProviderResult(
                provider="iTunes",
                entity_type="track",
                entity_id="it-1",
                url="https://itunes.example/it-1",
                title="Electric Avenue",
                artist="Eddy Grant",
                album="Killer On The Rampage",
                duration_ms="200000",
                isrc="",
                raw={"trackId": "it-1"},
            )
        ],
    )

    summary = verify_nyov_batch.verify_batch(db_path, batch_limit=1, providers=["itunes"], write=True)

    assert summary["dry_run"] is False
    assert summary["attempts_written"] == 1
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT provider, provider_entity_id, match_status, title_match_status FROM nyov_verification_attempts"
        ).fetchone()
    assert row == ("iTunes", "it-1", "matched", "exact")


def test_nyov_verification_summary_buckets_attempts(tmp_path):
    basket = tmp_path / "basket"
    seed = basket / "MyMusicBasefiltered_fixed.csv"
    write_csv(
        seed,
        ["Title", "Artist", "Album"],
        [
            ["Electric Avenue", "Eddy Grant", "Killer On The Rampage"],
            ["Song B", "Artist B", "Album B"],
            ["Song C", "Artist C", "Album C"],
            ["Song D", "Artist D", "Album D"],
        ],
    )
    db_path = tmp_path / "nyov.sqlite"
    build_nyov_db(paths(tmp_path), seed_csv=seed, basket_dir=basket, output_db=db_path)

    with sqlite3.connect(db_path) as conn:
        ids = {
            row[1]: row[0]
            for row in conn.execute("SELECT nyov_id, seed_title FROM nyov_entities").fetchall()
        }
        rows = [
            (
                "a1",
                ids["Electric Avenue"],
                "iTunes",
                "track",
                "it-1",
                "https://itunes.example/it-1",
                "Electric Avenue",
                "Eddy Grant",
                "Killer On The Rampage",
                "2026-07-16T00:00:00Z",
                "{}",
                "matched",
                1.0,
                "exact",
                "exact",
                "exact",
                "not_checked",
                "not_checked",
                "test",
                "test",
                "",
            ),
            (
                "a2",
                ids["Electric Avenue"],
                "MusicBrainz",
                "recording",
                "mb-1",
                "https://musicbrainz.example/mb-1",
                "Electric Avenue",
                "Eddy Grant",
                "Killer On The Rampage",
                "2026-07-16T00:00:00Z",
                "{}",
                "matched",
                0.95,
                "exact",
                "exact",
                "exact",
                "not_checked",
                "not_checked",
                "test",
                "test",
                "",
            ),
            (
                "b1",
                ids["Song B"],
                "iTunes",
                "track",
                "it-b",
                "https://itunes.example/it-b",
                "Song B",
                "Artist B",
                "Different Album",
                "2026-07-16T00:00:00Z",
                "{}",
                "matched",
                0.9,
                "exact",
                "exact",
                "different",
                "not_checked",
                "not_checked",
                "test",
                "test",
                "",
            ),
            (
                "c1",
                ids["Song C"],
                "iTunes",
                "track",
                "it-c",
                "https://itunes.example/it-c",
                "Different Song",
                "Artist C",
                "Album C",
                "2026-07-16T00:00:00Z",
                "{}",
                "rejected",
                0.4,
                "different",
                "exact",
                "exact",
                "not_checked",
                "not_checked",
                "test",
                "test",
                "",
            ),
            (
                "d1",
                ids["Song D"],
                "iTunes",
                "track",
                "it-d",
                "https://itunes.example/it-d",
                "Different Song",
                "Artist D",
                "Album D",
                "2026-07-16T00:00:00Z",
                "{}",
                "needs_review",
                0.75,
                "different",
                "exact",
                "exact",
                "not_checked",
                "not_checked",
                "test",
                "test",
                "",
            ),
        ]
        conn.executemany(
            """
            INSERT INTO nyov_verification_attempts
            (attempt_id, nyov_id, provider, provider_entity_type, provider_entity_id, provider_url,
             query_title, query_artist, query_album, queried_at, result_json, match_status,
             match_score, title_match_status, artist_match_status, album_match_status,
             duration_match_status, isrc_match_status, verifier, verifier_version, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    summary = build_summary(db_path)

    buckets = {row["review_bucket"]: row["entity_count"] for row in summary["review_bucket_counts"]}
    assert buckets["review_candidate_strong_identity"] == 1
    assert buckets["conflict_album_only"] == 1
    assert buckets["conflict_identity"] == 1
    assert buckets["insufficient_match"] == 1

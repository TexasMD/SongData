import csv
import sqlite3
import zipfile
from pathlib import Path

from src.config import paths
from src.nyov_db import build_nyov_db
from src.commands.nyov_report import build_report


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
        ["Title", "Artist", "Album", "Spotify Track ID"],
        [["Electric Avenue", "Eddy Grant", "Killer On The Rampage", "sp-1"]],
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

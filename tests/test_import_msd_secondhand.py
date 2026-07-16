from __future__ import annotations

import sqlite3
from pathlib import Path

from src.commands.import_msd_secondhand import build_import
from src.commands.import_msd_secondhand import parse_msd_secondhand_file


def test_parse_msd_secondhand_file_reads_cliques(tmp_path: Path):
    source = tmp_path / "shs_dataset_train.txt"
    source.write_text(
        "\n".join(
            [
                "# comment",
                "%72636,4253, My Sweet Lord",
                "TRPYNNL12903CAF506<SEP>ARXJJSN1187B98CB37<SEP>46770",
                "TRFYRVZ128F92EF998<SEP>ARNUFGE1187B9B7881<SEP>72636",
                "%-42, Missing Work",
                "TRMISS01234567890<SEP>ARMISS01234567890<SEP>-1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows = parse_msd_secondhand_file(source)

    assert len(rows) == 3
    assert rows[0].dataset_split == "train"
    assert rows[0].clique_id == "train_00001"
    assert rows[0].clique_title == "My Sweet Lord"
    assert rows[0].work_ids == ("72636", "4253")
    assert rows[0].msd_track_id == "TRPYNNL12903CAF506"
    assert rows[0].shs_performance_id == "46770"
    assert rows[2].work_ids == ("-42",)


def test_build_import_writes_csv_and_sqlite_outputs(tmp_path: Path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    (input_dir / "shs_dataset_train.txt").write_text(
        "\n".join(
            [
                "# train",
                "%1, Test Clique",
                "TRA<SEP>ARA<SEP>101",
                "TRB<SEP>ARB<SEP>102",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (input_dir / "shs_dataset_test.txt").write_text(
        "\n".join(
            [
                "# test",
                "%2, Other Clique",
                "TRC<SEP>ARC<SEP>201",
                "TRD<SEP>ARD<SEP>-1",
                "TRE<SEP>ARE<SEP>203",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = build_import(input_dir, output_dir)

    assert summary["clique_count"] == 2
    assert summary["performance_count"] == 5
    assert summary["connection_count"] == 4
    assert summary["known_shs_performance_count"] == 4
    assert summary["negative_or_missing_shs_performance_count"] == 1
    sqlite_path = output_dir / "msd_secondhand.sqlite"
    assert sqlite_path.exists()
    assert (output_dir / "msd_shs_cliques.csv").exists()
    assert (output_dir / "msd_shs_performances.csv").exists()
    assert (output_dir / "msd_shs_connections.csv").exists()
    assert (output_dir / "summary.json").exists()

    with sqlite3.connect(sqlite_path) as conn:
        clique_count = conn.execute("SELECT COUNT(*) FROM msd_shs_cliques").fetchone()[0]
        performance_count = conn.execute("SELECT COUNT(*) FROM msd_shs_performances").fetchone()[0]
        connection_count = conn.execute("SELECT COUNT(*) FROM msd_shs_connections").fetchone()[0]
        missing_perf_url = conn.execute(
            "SELECT shs_performance_url FROM msd_shs_performances WHERE msd_track_id = 'TRD'"
        ).fetchone()[0]

    assert clique_count == 2
    assert performance_count == 5
    assert connection_count == 4
    assert missing_perf_url == ""


def test_build_import_enriches_metadata_and_musicdb_matches(tmp_path: Path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    (input_dir / "shs_dataset_train.txt").write_text(
        "\n".join(
            [
                "# train",
                "%1, Shared Song",
                "TRA<SEP>ARA<SEP>101",
                "TRB<SEP>ARB<SEP>102",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (input_dir / "shs_dataset_test.txt").write_text("# test\n", encoding="utf-8")

    metadata_db = tmp_path / "track_metadata.db"
    with sqlite3.connect(metadata_db) as conn:
        conn.execute(
            """
            CREATE TABLE songs (
                track_id text PRIMARY KEY,
                title text,
                song_id text,
                release text,
                artist_id text,
                artist_mbid text,
                artist_name text,
                duration real,
                artist_familiarity real,
                artist_hotttnesss real,
                year int,
                track_7digitalid int,
                shs_perf int,
                shs_work int
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO songs
            (track_id, title, song_id, release, artist_id, artist_mbid, artist_name, duration, artist_familiarity, artist_hotttnesss, year, track_7digitalid, shs_perf, shs_work)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("TRA", "Shared Song", "SOA", "Release A", "ARA", "mba", "Artist A", 200.0, 0, 0, 1970, 1, 101, 1),
                ("TRB", "Shared Song", "SOB", "Release B", "ARB", "mbb", "Artist B", 201.0, 0, 0, 1971, 2, 102, 1),
            ],
        )

    recordings_csv = tmp_path / "recordings.csv"
    recordings_csv.write_text(
        "\n".join(
            [
                "Recording ID,Song ID,Title,Canonical Title,Artist",
                "R1,S1,Shared Song,Shared Song,Artist A",
                "R2,S2,Shared Song,Shared Song,Artist B",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = build_import(input_dir, output_dir, metadata_db, recordings_csv)

    assert summary["metadata_enriched_count"] == 2
    assert summary["musicdb_match_count"] == 2
    assert summary["musicdb_connection_count"] == 1
    with sqlite3.connect(output_dir / "msd_secondhand.sqlite") as conn:
        match_count = conn.execute("SELECT COUNT(*) FROM msd_shs_musicdb_matches").fetchone()[0]
        connection = conn.execute(
            "SELECT left_recording_id, right_recording_id FROM msd_shs_musicdb_connections"
        ).fetchone()

    assert match_count == 2
    assert connection == ("R1", "R2")

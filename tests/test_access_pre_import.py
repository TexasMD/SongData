import pytest
from pathlib import Path
import csv
from scripts.access_pre_import import (
    clean_value,
    build_dependency_graph,
    topological_sort,
    detect_orphans,
    infer_schema,
)


def test_clean_value():
    # Nulls
    assert clean_value("some_field", "None") == ""
    assert clean_value("some_field", "N/A") == ""
    assert clean_value("some_field", "--") == ""

    # Numerics
    assert clean_value("id", "123") == "123"
    assert clean_value("artist_id", "A-123") == "-123"
    assert clean_value("play_count", "1,234.56") == "1234.56"
    assert clean_value("index", "-10") == "-10"

    # Years
    assert clean_value("release_year", "October 1999") == "1999"
    assert clean_value("year", "2024 (Remaster)") == "2024"

    # Text
    assert clean_value("title", "Hello\r\nWorld") == "Hello World"
    assert clean_value("title", 'He said "Hello"') == 'He said ""Hello""'


def test_topological_sort():
    # Graph where parent -> children
    # artists has no dependencies (root)
    # albums depends on artists
    # songs depends on albums and artists
    # tags depends on songs
    schemas = [
        {"table": "tags", "fk_candidates": ["song_id"]},
        {"table": "songs", "fk_candidates": ["album_id", "artist_id"]},
        {"table": "albums", "fk_candidates": ["artist_id"]},
        {"table": "artists", "fk_candidates": []},
    ]

    graph = build_dependency_graph(schemas)
    assert "artists" in graph

    order = topological_sort(graph)

    # order should be artists, albums, songs, tags
    assert order.index("artists") < order.index("albums")
    assert order.index("artists") < order.index("songs")
    assert order.index("albums") < order.index("songs")
    assert order.index("songs") < order.index("tags")


def test_detect_orphans_memory_safe(tmp_path):
    # Setup test CSVs
    artists_path = tmp_path / "artists_clean.csv"
    with artists_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["artist_pk", "name"])
        writer.writeheader()
        writer.writerow({"artist_pk": "1", "name": "Artist 1"})
        writer.writerow({"artist_pk": "2", "name": "Artist 2"})

    songs_path = tmp_path / "songs_clean.csv"
    with songs_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["song_id", "artist_id", "title"])
        writer.writeheader()
        writer.writerow(
            {"song_id": "100", "artist_id": "1", "title": "Song 1"}
        )  # valid
        writer.writerow(
            {"song_id": "101", "artist_id": "3", "title": "Song 2"}
        )  # orphan

    clean_paths = [artists_path, songs_path]

    schemas = [
        {"table": "artists", "pk_candidates": ["artist_pk"], "fk_candidates": []},
        {
            "table": "songs",
            "pk_candidates": ["song_id"],
            "fk_candidates": ["artist_id"],
        },
    ]

    orphans = detect_orphans(clean_paths, schemas)

    assert len(orphans) == 1
    assert orphans[0]["table"] == "songs"
    assert orphans[0]["fk_field"] == "artist_id"
    assert orphans[0]["fk_value"] == "3"

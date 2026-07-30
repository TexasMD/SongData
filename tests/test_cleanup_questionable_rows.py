import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def load_module():
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "cleanup_questionable_rows.py"
    )
    spec = spec_from_file_location("cleanup_questionable_rows", script_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_title_candidates_strip_common_video_noise():
    module = load_module()
    candidates = module.title_candidates(
        {"Title": "Artist X - Song A (Official Video)", "Artist": "Artist X Topic"}
    )

    candidate_pairs = {
        (candidate.title, candidate.artist, candidate.note) for candidate in candidates
    }
    assert ("Song A", "Artist X", "split: - :left=title") in candidate_pairs
    assert any(candidate.title == "Artist X - Song A" for candidate in candidates)


def test_best_match_accepts_clean_title_and_artist():
    module = load_module()
    candidate = module.Candidate(title="Song A", artist="Artist X", note="test")
    result, score = module.best_match(
        candidate,
        [
            {"title": "Song A", "artist": "Artist X", "service": "iTunes"},
            {"title": "Song B", "artist": "Artist Y", "service": "Spotify"},
        ],
    )

    assert result["title"] == "Song A"
    assert score >= 0.95


def test_clean_title_removes_venues_and_instruments():
    module = load_module()
    assert module.clean_title("Karma Police (Live at BBC Radio 1)") == "Karma Police"
    assert module.clean_title("Tessellate for Like a Version") == "Tessellate"
    assert module.clean_title("Schism (Acoustic Guitar Cover)") == "Schism Cover"
    assert module.clean_title("5 Easy Licks [Hammond Organ]") == "5 Easy Licks"


def test_clean_artist_removes_db_tags():
    module = load_module()
    assert module.clean_artist("Daisy Chapman [gb25d]") == "Daisy Chapman"
    assert module.clean_artist("David Curci [us5d]") == "David Curci"


def test_suspicious_row_identifies_non_entities():
    module = load_module()
    assert (
        module.is_suspicious_row(
            {"Title": "Some Song", "Artist": "Greatest Hits Vol 2"}
        )
        == True
    )
    assert (
        module.is_suspicious_row({"Title": "Some Song", "Artist": "60s 70s 80s hits"})
        == True
    )
    assert (
        module.is_suspicious_row(
            {"Title": "Karaoke Version of Song", "Artist": "Unknown"}
        )
        == True
    )

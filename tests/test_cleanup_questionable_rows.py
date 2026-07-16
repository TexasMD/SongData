from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


def load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "cleanup_questionable_rows.py"
    spec = spec_from_file_location("cleanup_questionable_rows", script_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_title_candidates_strip_common_video_noise():
    module = load_module()
    candidates = module.title_candidates({"Title": "Artist X - Song A (Official Video)", "Artist": "Artist X Topic"})

    candidate_pairs = {(candidate.title, candidate.artist, candidate.note) for candidate in candidates}
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

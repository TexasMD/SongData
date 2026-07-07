from src.similarity import calculate_similarity

def test_calculate_similarity_bpm():
    target = {"recording_id": "1", "bpm": 120, "artist": "A", "key": "C"}
    candidates = [
        {"recording_id": "2", "bpm": 122, "artist": "B", "key": "D"}, # Close BPM
        {"recording_id": "3", "bpm": 140, "artist": "B", "key": "D"}, # Far BPM
    ]
    results = calculate_similarity(target, candidates)
    assert len(results) == 1
    assert results[0]["recording_id"] == "2"
    assert "Close BPM" in results[0]["reasons"]

def test_calculate_similarity_artist():
    target = {"recording_id": "1", "artist": "Artist X"}
    candidates = [
        {"recording_id": "2", "artist": "Artist X"},
        {"recording_id": "3", "artist": "Artist Y"},
    ]
    results = calculate_similarity(target, candidates)
    assert len(results) == 1
    assert results[0]["recording_id"] == "2"
    assert "Same Artist" in results[0]["reasons"]

def test_calculate_similarity_playlists():
    target = {"recording_id": "1", "playlists": "Rock;90s"}
    candidates = [
        {"recording_id": "2", "playlists": "Rock;Indie"},
        {"recording_id": "3", "playlists": "Jazz"},
    ]
    results = calculate_similarity(target, candidates)
    assert len(results) == 1
    assert results[0]["recording_id"] == "2"
    assert "Shared Playlists: Rock" in results[0]["reasons"]

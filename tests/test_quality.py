from src.quality import (
    _is_missing_spotify_mbid,
    _is_missing_bpm_key,
    _is_missing_musician_performance,
    generate_quality_report,
)


def test_is_missing_spotify_mbid():
    # Missing both
    assert _is_missing_spotify_mbid({}) is True
    assert _is_missing_spotify_mbid({"Title": "Song"}) is True

    # Has Spotify
    assert _is_missing_spotify_mbid({"Spotify Track ID": "123"}) is False
    assert _is_missing_spotify_mbid({"SpotifyID": "123"}) is False

    # Has MusicBrainz
    assert _is_missing_spotify_mbid({"MusicBrainz ID": "123"}) is False
    assert _is_missing_spotify_mbid({"MusicBrainzID": "123"}) is False

    # Has both
    assert (
        _is_missing_spotify_mbid({"Spotify Track ID": "123", "MusicBrainz ID": "456"})
        is False
    )


def test_is_missing_bpm_key():
    # Missing both
    assert _is_missing_bpm_key({}) is True
    assert _is_missing_bpm_key({"Title": "Song"}) is True

    # Has BPM
    assert _is_missing_bpm_key({"BPM": "120"}) is False

    # Has Key
    assert _is_missing_bpm_key({"Key": "C Major"}) is False

    # Has both
    assert _is_missing_bpm_key({"BPM": "120", "Key": "C Major"}) is False


def test_is_missing_musician_performance():
    # Missing
    assert _is_missing_musician_performance({}) is True
    assert _is_missing_musician_performance({"Title": "Song"}) is True

    # Has performance field
    assert _is_missing_musician_performance({"Tuning": "Standard"}) is False
    assert _is_missing_musician_performance({"Capo": "1"}) is False
    assert _is_missing_musician_performance({"Difficulty": "Easy"}) is False
    assert _is_missing_musician_performance({"Vocal Range": "Tenor"}) is False
    assert _is_missing_musician_performance({"Instrumentation": "Guitar"}) is False
    assert _is_missing_musician_performance({"Arrangement": "Acoustic"}) is False

    # Has dynamic Musician_ field
    assert _is_missing_musician_performance({"Musician_Guitar": "John Doe"}) is False


def test_generate_quality_report(monkeypatch):
    # Mock find_duplicates and group_by_version to return simple lists
    # so we don't depend on their full implementation here
    monkeypatch.setattr(
        "src.quality.find_duplicates", lambda records: [["Song1", "Song2"]]
    )
    monkeypatch.setattr(
        "src.quality.group_by_version",
        lambda records: {"Group1": ["Song1", "Song2"]},
    )

    records = [
        # Missing all
        {"Title": "Song 1", "Artist": "Artist 1"},
        # Has Spotify, missing others
        {"Title": "Song 2", "Artist": "Artist 2", "Spotify Track ID": "123"},
        # Has BPM, missing others
        {"Title": "Song 3", "Artist": "Artist 3", "BPM": "120"},
        # Has Performance, missing others
        {"Title": "Song 4", "Artist": "Artist 4", "Tuning": "Standard"},
        # Has all
        {
            "Title": "Song 5",
            "Artist": "Artist 5",
            "Spotify Track ID": "123",
            "BPM": "120",
            "Tuning": "Standard",
        },
    ]

    report = generate_quality_report(records)

    assert report["missing_spotify_mbid"] == 3  # Song 1, 3, 4
    assert report["missing_bpm_key"] == 3  # Song 1, 2, 4
    assert report["missing_musician_performance"] == 3  # Song 1, 2, 3

    # Check mocked returns
    assert report["duplicate_review_groups"] == 1
    assert report["version_review_groups"] == 1

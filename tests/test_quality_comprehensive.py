import pytest
from src.quality import generate_quality_report, format_report_as_json, format_report_as_markdown

def test_generate_quality_report_basic():
    records = [
        {
            "song_id": "1",
            "title": "Song 1",
            "artist": "Artist 1",
            "spotify_id": "spot1",
            "musicbrainz_id": "mb1",
            "bpm": "120",
            "key": "C"
        },
        {
            "song_id": "2",
            "title": "Song 2",
            "artist": "Artist 2",
            # Missing IDs and BPM/Key
        }
    ]

    report = generate_quality_report(records)

    assert report["total_records"] == 2
    assert report["missing_spotify_ids"] == 1
    assert report["missing_musicbrainz_ids"] == 1
    assert report["missing_bpm"] == 1
    assert report["missing_key"] == 1

def test_generate_quality_report_v2_fields():
    records = [
        {
            "Recording ID": "rec1",
            "Title": "Song 1",
            "Artist": "Artist 1",
            "Spotify Track ID": "spot1",
            "MusicBrainz ID": "mb1",
            "BPM": "120",
            "Key": "C"
        }
    ]
    report = generate_quality_report(records)
    assert report["missing_spotify_ids"] == 0
    assert report["missing_musicbrainz_ids"] == 0
    assert report["missing_bpm"] == 0
    assert report["missing_key"] == 0

def test_format_report_json():
    report = {"total_records": 10, "missing_bpm": 2}
    json_str = format_report_as_json(report)
    assert '"total_records": 10' in json_str
    assert '"missing_bpm": 2' in json_str

def test_format_report_markdown():
    report = {
        "total_records": 10,
        "missing_spotify_ids": 1,
        "missing_musicbrainz_ids": 2,
        "missing_bpm": 3,
        "missing_key": 4,
        "missing_musician_performance": 5,
        "duplicate_review_groups": 6,
        "version_review_groups": 7,
        "unverified_external_links": 8,
        "pending_antigravity_suggestions": 9,
        "external_link_verification_status": "Tested"
    }
    md_str = format_report_as_markdown(report)
    assert "# MusicDB Quality Report" in md_str
    assert "**Total Records:** 10" in md_str
    assert "**Missing Spotify IDs:** 1" in md_str

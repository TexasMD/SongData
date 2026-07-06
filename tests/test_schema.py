import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.schema import validate_record

def test_validate_record_v2():
    # Valid record with required fields
    valid = {
        "Recording ID": "rec1",
        "Song ID": "song1",
        "Title": "A",
        "Artist": "B"
    }
    assert not validate_record(valid)

    # Missing required field
    invalid_missing = {"Recording ID": "rec1", "Title": "A", "Artist": "B"}
    errors = validate_record(invalid_missing)
    assert len(errors) == 1
    assert "Song ID" in errors[0]

    # Invalid Energy
    invalid_energy = {
        "Recording ID": "rec1",
        "Song ID": "song1",
        "Title": "A",
        "Artist": "B",
        "Energy": "15"
    }
    errors = validate_record(invalid_energy)
    assert any("Energy must be between 1 and 10" in e for e in errors)

    # Invalid Difficulty
    invalid_diff = {
        "Recording ID": "rec1",
        "Song ID": "song1",
        "Title": "A",
        "Artist": "B",
        "Difficulty": "not-a-number"
    }
    errors = validate_record(invalid_diff)
    assert any("Difficulty must be an integer" in e for e in errors)

    # Invalid Energy Type
    invalid_energy_type = {
        "Recording ID": "rec1",
        "Song ID": "song1",
        "Title": "A",
        "Artist": "B",
        "Energy": "high"
    }
    errors = validate_record(invalid_energy_type)
    assert any("Energy must be an integer" in e for e in errors)

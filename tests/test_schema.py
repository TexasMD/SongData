import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.schema import validate_record

def test_validate_record():
    valid = {"Title": "A", "Artist": "B"}
    assert not validate_record(valid)

    invalid = {"Title": "A"}
    errors = validate_record(invalid)
    assert len(errors) == 1
    assert "Artist" in errors[0]

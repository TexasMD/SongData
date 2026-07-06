import pytest
import os
import sys

# Add the script to the path so we can import it
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../data/staging/jules'))

import import_antigravity_to_sqlite

class MockCursor:
    def execute(self, *args, **kwargs):
        pass
    def executemany(self, *args, **kwargs):
        pass

def test_missing_required_columns():
    csv_data = [
        {"Recording ID": "1", "Title": "Test", "Artist": "Test Artist"} # Missing fields
    ]
    with pytest.raises(ValueError, match="Missing required columns"):
        import_antigravity_to_sqlite.create_table_from_csv(MockCursor(), "test_table", csv_data, req_headers=import_antigravity_to_sqlite.REQ_MOOD)

def test_invalid_status_links():
    csv_data = [
        {"Status": "unsupported_status"}
    ]
    with pytest.raises(ValueError, match="Invalid Status 'unsupported_status'"):
        import_antigravity_to_sqlite.create_table_from_csv(MockCursor(), "test_table", csv_data, req_headers=import_antigravity_to_sqlite.REQ_LINKS, check_status=True)

def test_valid_status_links():
    csv_data = [
        {"Status": "verified_exact", "Other Field": "Value"}
    ]
    # Should not raise exception
    import_antigravity_to_sqlite.create_table_from_csv(MockCursor(), "test_table", csv_data, req_headers=import_antigravity_to_sqlite.REQ_LINKS, check_status=True)

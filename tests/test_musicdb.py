import unittest
import hashlib
import re

# --- Mock implementations of internal logic for testing ---

def normalize_string(s: str) -> str:
    """Removes emojis, strips whitespace, and lowercases for stable comparison."""
    if not isinstance(s, str):
        return ""
    # Strip emojis (basic heuristic)
    s = s.encode('ascii', 'ignore').decode('ascii')
    # Strip leading numbers/hyphens (e.g. "01 - Title")
    s = re.sub(r'^\d+\s*[-]\s*', '', s)
    return s.strip().lower()

def generate_stable_id(title: str, artist: str) -> str:
    """Generates a stable 13-character ID based on normalized title and artist."""
    t = normalize_string(title)
    a = normalize_string(artist)
    hash_input = f"{t}||{a}".encode('utf-8')
    return "R" + hashlib.md5(hash_input).hexdigest()[:12].upper()

def detect_duplicates(rows: list[dict]) -> list[list[dict]]:
    """Groups rows by stable ID to detect duplicates."""
    groups = {}
    for row in rows:
        rid = generate_stable_id(row.get("Title", ""), row.get("Artist", ""))
        groups.setdefault(rid, []).append(row)
    return [g for g in groups.values() if len(g) > 1]

def validate_schema(columns: list[str]) -> bool:
    """Ensures critical columns are present."""
    required = {"Title", "Artist", "Album", "Recording ID", "BPM", "Key"}
    return required.issubset(set(columns))

def execute_command(cmd_name: str, write_flag: bool) -> str:
    """Mock execution wrapper to test dry-run safety."""
    if cmd_name in ["verify", "import"] and not write_flag:
        return "DRY_RUN"
    return "EXECUTED"

# --- Test Suite ---

class TestMusicDB(unittest.TestCase):

    def test_normalization(self):
        # Test leading track numbers
        self.assertEqual(normalize_string("01 - Dancing Queen"), "dancing queen")
        self.assertEqual(normalize_string("12- Bohemian Rhapsody"), "bohemian rhapsody")
        # Test emojis (stripped by ascii ignore)
        self.assertEqual(normalize_string("Fire "), "fire")
        self.assertEqual(normalize_string("  Spaces  "), "spaces")

    def test_stable_id_generation(self):
        id1 = generate_stable_id("Dancing Queen", "ABBA")
        id2 = generate_stable_id("dancing queen ", "abba")
        id3 = generate_stable_id("Dancing Queen", "ABBA ")
        self.assertEqual(id1, id2)
        self.assertEqual(id1, id3)
        self.assertTrue(id1.startswith("R"))
        self.assertEqual(len(id1), 13)

    def test_duplicate_detection(self):
        rows = [
            {"Title": "Song A", "Artist": "Artist A", "Source": "Spotify"},
            {"Title": "Song B", "Artist": "Artist B", "Source": "Spotify"},
            {"Title": "song a", "Artist": "artist a", "Source": "iTunes"}
        ]
        dupes = detect_duplicates(rows)
        self.assertEqual(len(dupes), 1)
        self.assertEqual(len(dupes[0]), 2)
        self.assertEqual(dupes[0][0]["Source"], "Spotify")
        self.assertEqual(dupes[0][1]["Source"], "iTunes")

    def test_schema_validation(self):
        good_cols = ["Recording ID", "Song ID", "Title", "Artist", "Album", "BPM", "Key", "Genre"]
        bad_cols = ["Title", "Artist"] # Missing required ID and Performance fields
        self.assertTrue(validate_schema(good_cols))
        self.assertFalse(validate_schema(bad_cols))

    def test_dry_run_safety(self):
        # Without explicit write flag
        self.assertEqual(execute_command("import", False), "DRY_RUN")
        self.assertEqual(execute_command("verify", False), "DRY_RUN")
        # With explicit write flag
        self.assertEqual(execute_command("import", True), "EXECUTED")
        self.assertEqual(execute_command("verify", True), "EXECUTED")

if __name__ == '__main__':
    unittest.main()

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.promote_active_main_patch_candidate import PromotionError, promote


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestPromoteActiveMainPatchCandidate(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.active = root / "data" / "processed" / "Main_Song_Database.csv"
        self.candidate = root / "data" / "staging" / "codex" / "active_main_patch_candidate.csv"
        self.summary = root / "data" / "exports" / "codex" / "active_main_patch_summary.json"
        self.report = root / "data" / "exports" / "codex" / "promotion.json"
        self.backups = root / "data" / "backups"

        write_csv(self.active, ["Title", "Artist", "Spotify Track ID"], [["Song", "Artist", ""]])
        write_csv(
            self.candidate,
            ["Title", "Artist", "Spotify Track ID", "Legacy D Music Source Files"],
            [["Song", "Artist", "abc123", "legacy.csv"]],
        )
        self.summary.parent.mkdir(parents=True, exist_ok=True)
        self.summary.write_text(
            json.dumps(
                {
                    "active_sha_after": file_sha(self.active),
                    "patch_candidate_csv": str(self.candidate),
                    "patch_candidate_sha256": file_sha(self.candidate),
                    "active_rows": 1,
                    "candidate_rows": 1,
                    "patch_action_count": 2,
                    "skipped_review_count": 0,
                    "verification": {
                        "overwrite_violations": 0,
                        "staged_spotify_track_id_mismatches": 0,
                    },
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_dry_run_does_not_modify_active_csv(self):
        before = self.active.read_bytes()
        report = promote(self.summary, self.active, self.backups, self.report, write=False)
        self.assertFalse(report["active_database_modified"])
        self.assertEqual(before, self.active.read_bytes())
        self.assertEqual(report["added_columns"], ["Legacy D Music Source Files"])

    def test_write_creates_backup_and_replaces_active_csv(self):
        report = promote(self.summary, self.active, self.backups, self.report, write=True)
        self.assertTrue(report["active_database_modified"])
        self.assertTrue(Path(report["backup_path"]).exists())
        self.assertEqual(file_sha(self.active), file_sha(self.candidate))

    def test_refuses_when_active_hash_changed(self):
        write_csv(self.active, ["Title", "Artist", "Spotify Track ID"], [["Changed", "Artist", ""]])
        with self.assertRaises(PromotionError):
            promote(self.summary, self.active, self.backups, self.report, write=False)


if __name__ == "__main__":
    unittest.main()

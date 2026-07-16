import csv
import json
import unittest
from pathlib import Path
from uuid import uuid4

from src.commands.metadata_audit import run
from src.config import paths


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def make_temp_root() -> Path:
    root = Path.cwd() / "tmp" / f"test_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=False)
    return root


class TestMetadataAudit(unittest.TestCase):
    def test_metadata_audit_reports_dual_verification_and_normalization(self):
        root = make_temp_root()
        configured = paths(root)
        write_csv(
            configured.recordings_csv,
            [
                "Recording ID",
                "Song ID",
                "Title",
                "Artist",
                "Album",
                "Spotify Track ID",
                "Spotify Verified",
                "iTunes Verified",
                "MusicBrainz Recording ID",
                "MusicBrainz Verified",
                "Discogs Verified",
                "SecondHandSongs Verified URL",
                "WhoSampled Verified URL",
            ],
            [
                ["R1", "S1", "Beyoncé - \xa0Rebel Yell", "Beyoncé", "Album", "sp-1", "Yes", "", "mb-1", "Yes", "", "", ""],
                ["R2", "S2", "Plain Song", "Artist", "Album", "", "", "Yes", "", "", "", "", ""],
                ["R3", "S3", "Another Song", "Artist", "Album", "", "", "", "mb-3", "Yes", "Yes", "", ""],
            ],
        )

        rc = run(write=True, paths=configured)
        self.assertEqual(rc, 0)

        summary_path = configured.exports_dir / "codex" / "metadata_audit" / "summary.json"
        incidents_path = configured.exports_dir / "codex" / "metadata_audit" / "normalization_incidents.csv"
        underverified_path = configured.exports_dir / "codex" / "metadata_audit" / "underverified_rows.csv"

        self.assertTrue(summary_path.exists())
        self.assertTrue(incidents_path.exists())
        self.assertTrue(underverified_path.exists())

        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["total_recordings"], 3)
        self.assertEqual(summary["dual_verified_rows"], 2)
        self.assertEqual(summary["underverified_rows"], 1)
        self.assertGreaterEqual(summary["normalization_incidents"], 1)
        self.assertEqual(summary["source_coverage"]["Spotify"], 1)
        self.assertEqual(summary["source_coverage"]["MusicBrainz"], 2)

    def test_metadata_audit_main_supports_active_csv_shape(self):
        root = make_temp_root()
        configured = paths(root)
        write_csv(
            configured.active_main_csv,
            [
                "Title",
                "Base Title",
                "Artist",
                "Album",
                "Original Data",
                "Discogs Verified",
                "Spotify Verified",
                "MusicBrainz Verified",
                "iTunes Verified",
                "Spotify ID",
                "Spotify Track ID",
                "Spotify MusicBrainz ID",
                "Source Files",
            ],
            [[
                "Beyoncé - \xa0Rebel Yell",
                "Rebel Yell",
                "Beyoncé",
                "Album",
                "Song Title: Rebel Yell | Artist Names: Beyoncé",
                "Yes",
                "Yes",
                "",
                "",
                "sp-legacy",
                "sp-track",
                "mbid-legacy",
                "file1; file2",
            ]],
        )

        rc = run(write=True, paths=configured, input_csv=configured.active_main_csv)
        self.assertEqual(rc, 0)

        summary_path = configured.exports_dir / "codex" / "metadata_audit" / "summary_Main_Song_Database.json"
        incidents_path = configured.exports_dir / "codex" / "metadata_audit" / "normalization_incidents_Main_Song_Database.csv"
        underverified_path = configured.exports_dir / "codex" / "metadata_audit" / "underverified_rows_Main_Song_Database.csv"

        self.assertTrue(summary_path.exists())
        self.assertTrue(incidents_path.exists())
        self.assertTrue(underverified_path.exists())

        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["total_recordings"], 1)
        self.assertEqual(summary["dual_verified_rows"], 1)
        self.assertEqual(summary["underverified_rows"], 0)
        self.assertGreaterEqual(summary["normalization_incidents"], 1)
        self.assertEqual(summary["source_coverage"]["Spotify"], 1)
        self.assertEqual(summary["source_coverage"]["Discogs"], 1)
        self.assertEqual(summary["identifier_coverage"]["Spotify MusicBrainz ID"], 1)


if __name__ == "__main__":
    unittest.main()

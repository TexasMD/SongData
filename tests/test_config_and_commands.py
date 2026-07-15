import csv
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from src.commands import build_v2, quality_report
from src.config import paths


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def make_temp_root() -> Path:
    root = Path.cwd() / "tmp" / f"test_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=False)
    return root


class TestConfigAndCommands(unittest.TestCase):
    def test_paths_derive_from_musicdb_root(self):
        root = make_temp_root()
        with patch.dict("os.environ", {"MUSICDB_ROOT": str(root)}):
            configured = paths()

        self.assertEqual(configured.root, root.resolve())
        self.assertEqual(configured.active_main_csv, root.resolve() / "data" / "processed" / "Main_Song_Database.csv")
        self.assertEqual(configured.recordings_csv, root.resolve() / "SongDB_v2" / "recordings.csv")
        self.assertEqual(configured.sqlite_poc_path, root.resolve() / "data" / "staging" / "jules" / "poc.sqlite")
        self.assertEqual(configured.reference_db_path, root.resolve() / "data" / "staging" / "jules" / "reference_ids.sqlite")

    def test_build_v2_dry_run_does_not_call_subprocess(self):
        root = make_temp_root()
        configured = paths(root)
        configured.scripts_dir.mkdir(parents=True)
        (configured.scripts_dir / "build_songdb_v2.py").write_text("print('nope')", encoding="utf-8")

        output = io.StringIO()
        with patch("src.commands.build_v2.subprocess.run") as mocked_run, redirect_stdout(output):
            rc = build_v2.run(write=False, paths=configured)

        self.assertEqual(rc, 0)
        self.assertIn("DRY RUN", output.getvalue())
        mocked_run.assert_not_called()

    def test_build_v2_write_calls_existing_builder(self):
        root = make_temp_root()
        configured = paths(root)
        configured.scripts_dir.mkdir(parents=True)
        script = configured.scripts_dir / "build_songdb_v2.py"
        script.write_text("print('builder')", encoding="utf-8")

        with patch("src.commands.build_v2.subprocess.run") as mocked_run:
            mocked_run.return_value.returncode = 0
            rc = build_v2.run(write=True, paths=configured)

        self.assertEqual(rc, 0)
        mocked_run.assert_called_once()
        self.assertEqual(mocked_run.call_args.args[0][-1], str(script))

    def test_quality_report_counts_blank_fields(self):
        root = make_temp_root()
        configured = paths(root)
        write_csv(
            configured.recordings_csv,
            ["Title", "Spotify Track ID", "MusicBrainz Recording ID", "BPM", "Key"],
            [
                ["A", "spotify", "", "120", "C"],
                ["B", "", "mbid", "", ""],
                ["C", "", "", "", "G"],
            ],
        )

        report = quality_report.generate_quality_report(configured.recordings_csv)

        self.assertEqual(report["total_recordings"], 3)
        self.assertEqual(report["missing_spotify_ids"], 2)
        self.assertEqual(report["missing_musicbrainz_ids"], 2)
        self.assertEqual(report["missing_bpm"], 2)
        self.assertEqual(report["missing_key"], 1)


if __name__ == "__main__":
    unittest.main()

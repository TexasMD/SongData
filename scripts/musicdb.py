import argparse
import sys
import json
import os
import csv
from pathlib import Path

# Add parent directory to path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.schema import validate_record
from src.quality import generate_quality_report as src_generate_quality_report
from src.config import paths as musicdb_paths
from src.sqlite_poc import insert_v2_records, DB_PATH
from src.utils import backup_file, read_csv
from src.commands import build_reference_db as reference_db_command
from src.commands import metadata_audit as metadata_audit_command
from src.commands import build_nyov_db as nyov_db_command
from src.commands import nyov_report as nyov_report_command
from src.commands import verify_nyov_batch as verify_nyov_batch_command
from src.commands import nyov_verification_summary as nyov_verification_summary_command
from src.commands import nyov_promotion_review as nyov_promotion_review_command
from src.commands import apply_nyov_promotions as apply_nyov_promotions_command
from src.commands import export_nyov_official_patch as export_nyov_official_patch_command
from src.commands import apply_nyov_official_patch as apply_nyov_official_patch_command
from src.commands import apply_data_patches as apply_data_patches_command
from src.commands import import_msd_secondhand as import_msd_secondhand_command
from src.commands import enrich_msd_secondhand_review as enrich_msd_secondhand_review_command
from src.youtube_music_takeout import build_takeout_export, build_takeout_song_export
from scripts.verify_youtube_music_takeout import build_verified_takeout_export


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TAKEOUT_INPUT = Path(
    os.environ.get(
        "YOUTUBE_MUSIC_TAKEOUT_PLAYLIST_DIR",
        PROJECT_DIR / "data" / "imports" / "youtube_music_takeout" / "playlists",
    )
)
DEFAULT_TAKEOUT_OUTPUT = PROJECT_DIR / "data" / "exports" / "codex" / "youtube_music_playlist_videos_deduped.csv"
DEFAULT_TAKEOUT_SONGS = PROJECT_DIR / "data" / "exports" / "codex" / "youtube_music_takeout_songs.csv"
DEFAULT_TAKEOUT_CACHE = PROJECT_DIR / "tmp" / "youtube_music_playlist_metadata_cache.json"
DEFAULT_TAKEOUT_VERIFIED = PROJECT_DIR / "data" / "exports" / "codex" / "youtube_music_takeout_verified.csv"
DEFAULT_TAKEOUT_UNMATCHED = PROJECT_DIR / "data" / "exports" / "codex" / "youtube_music_takeout_unmatched.csv"
DEFAULT_TAKEOUT_VERIFICATION_SUMMARY = PROJECT_DIR / "data" / "exports" / "codex" / "youtube_music_takeout_verification_summary.json"
DEFAULT_TAKEOUT_VERIFICATION_CACHE = PROJECT_DIR / "data" / "exports" / "codex" / "youtube_music_takeout_verification_cache.json"

INPUT_MOCK_FILE = "data/staging/recordings_mock.csv"


def ensure_mock_file():
    if not os.path.exists(INPUT_MOCK_FILE):
        os.makedirs(os.path.dirname(INPUT_MOCK_FILE), exist_ok=True)
        with open(INPUT_MOCK_FILE, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "Recording ID",
                    "Song ID",
                    "Title",
                    "Artist",
                    "Version",
                    "Spotify Track ID",
                    "MusicBrainz ID",
                    "BPM",
                    "Key",
                    "Playlists",
                    "Arrangement",
                    "SHS Link",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Recording ID": "rec1",
                    "Song ID": "song1",
                    "Title": "Test Song",
                    "Artist": "Test Artist",
                    "Version": "",
                    "Spotify Track ID": "sp1",
                    "MusicBrainz ID": "mb1",
                    "BPM": "120",
                    "Key": "C",
                    "Playlists": "Test;Cool",
                    "Arrangement": "Acoustic",
                    "SHS Link": "http://shs.com/1",
                }
            )

def build_v2(input_csv=INPUT_MOCK_FILE, write_enabled=False, sqlite_path=DB_PATH):
    print(f"build-v2: dry-run={not write_enabled}")
    if write_enabled:
        print("Executing write operations for build-v2...")
        print(f"Executing rebuild-db into {sqlite_path}...")
        if os.path.exists(sqlite_path):
            os.remove(sqlite_path)

        ensure_mock_file()  # Usually we should use input_csv, but to keep the mock for now
        records = read_csv(input_csv)
        insert_v2_records(records, db_path=sqlite_path)

        # tests/test_cli_upgraded.py expects sqlite_path to be a real SQLite DB
        import sqlite3
        with sqlite3.connect(sqlite_path) as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
            conn.commit()

        print(f"Successfully rebuilt database with {len(records)} records.")


def rebuild(write_enabled=False):
    """
    Rebuilds the compatibility Main_Song_Database.csv from recordings.csv.
    """
    print(f"rebuild: dry-run={not write_enabled}")

    ensure_mock_file()
    input_file = INPUT_MOCK_FILE
    output_dir = "data/staging/jules"
    output_file = os.path.join(output_dir, "Main_Song_Database.csv")

    if write_enabled:
        print(f"Rebuilding {output_file} from {input_file}...")
        os.makedirs(output_dir, exist_ok=True)

        # Backup before writing
        if os.path.exists(output_file):
            backup_path = backup_file(output_file)
            if backup_path:
                print(f"Created backup at {backup_path}")

        records_to_export = []
        records = read_csv(input_file)
        for row in records:
            # Mapping as per docs/SCHEMA_V2.md
            comp_row = {
                "Title": row.get("Title", ""),
                "Artist": row.get("Artist", ""),
                "Version": row.get("Version", ""),
                "Spotify ID": row.get("Spotify Track ID", ""),
                "MBID": row.get("MusicBrainz ID", ""),
                "BPM": row.get("BPM", ""),
                "Key": row.get("Key", ""),
                "Playlists": row.get("Playlists", ""),
                "Notes": f"{row.get('Arrangement', '')} {row.get('SHS Link', '')}".strip(),
            }
            records_to_export.append(comp_row)

        with open(output_file, "w", newline="") as f:
            if records_to_export:
                writer = csv.DictWriter(f, fieldnames=records_to_export[0].keys())
                writer.writeheader()
                writer.writerows(records_to_export)

        print(
            f"Successfully rebuilt {output_file} with {len(records_to_export)} records."
        )
    else:
        print(f"DRY RUN: Would rebuild {output_file} from {input_file}")
        if os.path.exists(output_file):
            print(f"DRY RUN: Would create backup of {output_file}")


def review_active_vs_staged():
    print("review-active-vs-staged...")

def generate_quality_report(
    input_csv=INPUT_MOCK_FILE, write_enabled=False, export_dir=None
):
    print(f"quality-report: dry-run={not write_enabled}")

    ensure_mock_file()
    records = read_csv(input_csv)
    report = src_generate_quality_report(records)

    print("Quality Report Summary:")
    print(f"Total songs: {len(records)}")

    if write_enabled:
        if export_dir is None:
            export_dir = os.path.join(
                os.path.dirname(__file__), "..", "data", "exports"
            )
        os.makedirs(export_dir, exist_ok=True)

        json_file = os.path.join(export_dir, "quality_report.json")
        md_file = os.path.join(export_dir, "quality_report.md")

        with open(json_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Exported JSON report to {json_file}")

        with open(md_file, "w") as f:
            f.write("# Quality Report\n\n")
            for k, v in report.items():
                f.write(f"- **{k}**: {v}\n")
        print(f"Exported Markdown report to {md_file}")
    else:
        print("Quality Report Summary:")
        print(f"Total songs: {len(records)}")
        print("DRY RUN: Would export JSON and Markdown reports to data/exports")
        print("Report contents:")
        print(json.dumps(report, indent=2))



def import_playlist(
    write_enabled=False,
    input_dir=DEFAULT_TAKEOUT_INPUT,
    output=DEFAULT_TAKEOUT_OUTPUT,
    songs_output=DEFAULT_TAKEOUT_SONGS,
    cache=DEFAULT_TAKEOUT_CACHE,
    workers=8,
):
    print(f"import-playlist: dry-run={not write_enabled}")
    print(f"Input: {input_dir}")
    print(f"Output: {output}")
    print(f"Songs output: {songs_output}")
    print(f"Cache: {cache}")
    if not write_enabled:
        print("DRY RUN: Would extract, dedupe, enrich, and write YouTube Music Takeout playlist metadata.")
        print("DRY RUN: Would also write a compact song list with youtube music song ID, title, artist, album, year, and genre.")
        print("DRY RUN: The resulting export can be consumed by build_songdb_v2.py for playlist membership matching.")
        return

    result = build_takeout_export(input_dir, output, cache, workers=workers)
    songs = build_takeout_song_export(result.rows, songs_output)
    print(f"Wrote {len(songs)} unique songs to {songs_output}")
    print(json.dumps(result.summary, indent=2))


def verify_youtube_music_takeout(
    write_enabled=False,
    input_csv=DEFAULT_TAKEOUT_OUTPUT,
    output_csv=DEFAULT_TAKEOUT_VERIFIED,
    unmatched_csv=DEFAULT_TAKEOUT_UNMATCHED,
    summary_json=DEFAULT_TAKEOUT_VERIFICATION_SUMMARY,
    cache=DEFAULT_TAKEOUT_VERIFICATION_CACHE,
    workers=6,
):
    print(f"verify-youtube-music-takeout: dry-run={not write_enabled}")
    print(f"Input: {input_csv}")
    print(f"Output: {output_csv}")
    print(f"Unmatched: {unmatched_csv}")
    if not write_enabled:
        print("DRY RUN: Would check the 3531 title/artist rows against Spotify and iTunes.")
        print("DRY RUN: Would write a canonical metadata CSV plus a separate unmatched review CSV.")
        return

    summary = build_verified_takeout_export(
        input_csv,
        output_csv,
        unmatched_csv,
        summary_json,
        cache,
        workers=workers,
    )
    print(json.dumps(summary, indent=2))


def verify():
    print("verify...")
    ensure_mock_file()
    records = read_csv(INPUT_MOCK_FILE)
    all_errors = []

    for i, record in enumerate(records):
        errors = validate_record(record)
        if errors:
            all_errors.append(f"Row {i+1} ({record.get('Title', 'Unknown')}): {errors}")

    if all_errors:
        print("Validation errors found:")
        for error in all_errors:
            print(error)
    else:
        print(f"Validation successful for {len(records)} records.")


def export_view(write_enabled=False):
    print("export-view...")
    export_dir = os.path.join(
        os.path.dirname(__file__), "..", "data", "exports", "jules"
    )
    os.makedirs(export_dir, exist_ok=True)
    export_file = os.path.join(export_dir, "export.json")

    ensure_mock_file()
    records = read_csv(INPUT_MOCK_FILE)

    if write_enabled:
        with open(export_file, "w") as f:
            json.dump(records, f, indent=2)
        print(f"Exported to {export_file}")
    else:
        print(f"dry-run: Would export to {export_file}")


def build_reference_db(write_enabled=False):
    reference_db_command.run(write=write_enabled, paths=musicdb_paths())


def metadata_audit(write_enabled=False):
    metadata_audit_command.run(write=write_enabled, paths=musicdb_paths())


def metadata_audit_main(write_enabled=False):
    metadata_audit_command.run(
        write=write_enabled,
        paths=musicdb_paths(),
        input_csv=musicdb_paths().active_main_csv,
    )


def build_nyov_db(write_enabled=False, seed_csv=None, basket_dir=None, output_db=None):
    nyov_db_command.run(
        write=write_enabled,
        paths=musicdb_paths(),
        seed_csv=seed_csv,
        basket_dir=basket_dir,
        output_db=output_db,
    )


def nyov_report(
    write_enabled=False,
    db_path=None,
    output_dir=None,
    queue_limit=250,
    batch_step="candidate_dual_source_match",
    batch_limit=100,
):
    nyov_report_command.run(
        write=write_enabled,
        paths=musicdb_paths(),
        db_path=db_path,
        output_dir=output_dir,
        queue_limit=queue_limit,
        batch_step=batch_step,
        batch_limit=batch_limit,
    )


def verify_nyov_batch(
    write_enabled=False,
    db_path=None,
    batch_step="candidate_dual_source_match",
    batch_limit=10,
    providers="itunes,musicbrainz,spotify",
    strategy="all",
    tie_breaker_providers="spotify",
):
    verify_nyov_batch_command.run(
        write=write_enabled,
        paths=musicdb_paths(),
        db_path=db_path,
        batch_step=batch_step,
        batch_limit=batch_limit,
        providers=providers,
        strategy=strategy,
        tie_breaker_providers=tie_breaker_providers,
    )


def nyov_verification_summary(write_enabled=False, db_path=None, output_dir=None):
    nyov_verification_summary_command.run(
        write=write_enabled,
        paths=musicdb_paths(),
        db_path=db_path,
        output_dir=output_dir,
    )


def nyov_promotion_review(write_enabled=False, db_path=None, output_dir=None):
    nyov_promotion_review_command.run(
        write=write_enabled,
        paths=musicdb_paths(),
        db_path=db_path,
        output_dir=output_dir,
    )


def apply_nyov_promotions(write_enabled=False, db_path=None, review_csv=None, promoted_by="manual_review"):
    apply_nyov_promotions_command.run(
        write=write_enabled,
        paths=musicdb_paths(),
        db_path=db_path,
        review_csv=review_csv,
        promoted_by=promoted_by,
    )


def export_nyov_official_patch(write_enabled=False, db_path=None, official_csv=None, output_dir=None):
    export_nyov_official_patch_command.run(
        write=write_enabled,
        paths=musicdb_paths(),
        db_path=db_path,
        official_csv=official_csv,
        output_dir=output_dir,
    )


def apply_nyov_official_patch(write_enabled=False, official_csv=None, patch_csv=None, backup_dir=None):
    apply_nyov_official_patch_command.run(
        write=write_enabled,
        paths=musicdb_paths(),
        official_csv=official_csv,
        patch_csv=patch_csv,
        backup_dir=backup_dir,
    )


def apply_data_patches(write_enabled=False, patch_dir=None, patch_file=None, backup_dir=None):
    apply_data_patches_command.run(
        write=write_enabled,
        paths=musicdb_paths(),
        patch_dir=patch_dir,
        patch_file=patch_file,
        backup_dir=backup_dir,
    )


def import_msd_secondhand(write_enabled=False, input_dir=None, output_dir=None, track_metadata_db=None):
    import_msd_secondhand_command.run(
        write=write_enabled,
        paths=musicdb_paths(),
        input_dir=input_dir,
        output_dir=output_dir,
        track_metadata_db=track_metadata_db,
    )


def main():
    parser = argparse.ArgumentParser(description="MusicDB CLI")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Explicitly allow write operations (default is dry-run)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_build = subparsers.add_parser("build-v2", help="Build the SQLite database")

    parser_rebuild = subparsers.add_parser(
        "rebuild", help="Rebuild compatibility main CSV from recordings.csv"
    )

    parser_review = subparsers.add_parser(
        "review-active-vs-staged", help="Review staged changes"
    )

    parser_quality = subparsers.add_parser(
        "quality-report", help="Generate a quality report"
    )

    parser_import = subparsers.add_parser("import-playlist", help="Import a playlist")
    parser_import_ytm = subparsers.add_parser(
        "import-youtube-music-takeout",
        help="Import and enrich YouTube Music Takeout playlist exports",
    )
    parser_verify_ytm = subparsers.add_parser(
        "verify-youtube-music-takeout",
        help="Verify YouTube Music Takeout rows against Spotify and iTunes",
    )
    for subparser in (parser_import, parser_import_ytm):
        subparser.add_argument("--input-dir", type=Path, default=DEFAULT_TAKEOUT_INPUT)
        subparser.add_argument("--output", type=Path, default=DEFAULT_TAKEOUT_OUTPUT)
        subparser.add_argument("--songs-output", type=Path, default=DEFAULT_TAKEOUT_SONGS)
        subparser.add_argument("--cache", type=Path, default=DEFAULT_TAKEOUT_CACHE)
        subparser.add_argument("--workers", type=int, default=8)
    parser_verify_ytm.add_argument("--input", type=Path, default=DEFAULT_TAKEOUT_OUTPUT)
    parser_verify_ytm.add_argument("--output", type=Path, default=DEFAULT_TAKEOUT_VERIFIED)
    parser_verify_ytm.add_argument("--unmatched", type=Path, default=DEFAULT_TAKEOUT_UNMATCHED)
    parser_verify_ytm.add_argument("--summary", type=Path, default=DEFAULT_TAKEOUT_VERIFICATION_SUMMARY)
    parser_verify_ytm.add_argument("--cache", type=Path, default=DEFAULT_TAKEOUT_VERIFICATION_CACHE)
    parser_verify_ytm.add_argument("--workers", type=int, default=6)

    parser_verify = subparsers.add_parser("verify", help="Verify data integrity")

    parser_export = subparsers.add_parser("export-view", help="Export data view")
    parser_reference_db = subparsers.add_parser(
        "build-reference-db",
        help="Build the separate reference-ID SQLite database",
    )
    parser_metadata_audit = subparsers.add_parser(
        "metadata-audit",
        help="Audit dual-source verification and normalization incidents",
    )
    parser_metadata_audit_main = subparsers.add_parser(
        "metadata-audit-main",
        help="Audit the active compatibility CSV for dual-source verification and normalization incidents",
    )
    parser_nyov = subparsers.add_parser(
        "build-nyov-db",
        help="Build the not-yet-officially-verified local evidence database",
    )
    parser_nyov.add_argument("--seed-csv", type=Path, default=None)
    parser_nyov.add_argument("--basket-dir", type=Path, default=None)
    parser_nyov.add_argument("--output-db", type=Path, default=None)
    parser_nyov_report = subparsers.add_parser(
        "nyov-report",
        help="Summarize the not-yet-officially-verified evidence database",
    )
    parser_nyov_report.add_argument("--db-path", type=Path, default=None)
    parser_nyov_report.add_argument("--output-dir", type=Path, default=None)
    parser_nyov_report.add_argument("--queue-limit", type=int, default=250)
    parser_nyov_report.add_argument("--batch-step", default="candidate_dual_source_match")
    parser_nyov_report.add_argument("--batch-limit", type=int, default=100)
    parser_verify_nyov = subparsers.add_parser(
        "verify-nyov-batch",
        help="Verify a NYOV candidate batch against external providers without promoting rows",
    )
    parser_verify_nyov.add_argument("--db-path", type=Path, default=None)
    parser_verify_nyov.add_argument("--batch-step", default="candidate_dual_source_match")
    parser_verify_nyov.add_argument("--batch-limit", type=int, default=10)
    parser_verify_nyov.add_argument("--providers", default="itunes,musicbrainz,spotify")
    parser_verify_nyov.add_argument("--strategy", choices=["all", "tie-breaker"], default="all")
    parser_verify_nyov.add_argument("--tie-breaker-providers", default="spotify")
    parser_nyov_verification_summary = subparsers.add_parser(
        "nyov-verification-summary",
        help="Summarize NYOV provider verification attempts for review",
    )
    parser_nyov_verification_summary.add_argument("--db-path", type=Path, default=None)
    parser_nyov_verification_summary.add_argument("--output-dir", type=Path, default=None)
    parser_nyov_promotion_review = subparsers.add_parser(
        "nyov-promotion-review",
        help="Export field-level NYOV promotion candidates for human review",
    )
    parser_nyov_promotion_review.add_argument("--db-path", type=Path, default=None)
    parser_nyov_promotion_review.add_argument("--output-dir", type=Path, default=None)
    parser_apply_nyov_promotions = subparsers.add_parser(
        "apply-nyov-promotions",
        help="Apply approved NYOV promotion review rows into nyov_promotions",
    )
    parser_apply_nyov_promotions.add_argument("--db-path", type=Path, default=None)
    parser_apply_nyov_promotions.add_argument("--input", type=Path, default=None)
    parser_apply_nyov_promotions.add_argument("--promoted-by", default="manual_review")
    parser_export_nyov_patch = subparsers.add_parser(
        "export-nyov-official-patch",
        help="Export reviewable official-table patch candidates from approved NYOV promotions",
    )
    parser_export_nyov_patch.add_argument("--db-path", type=Path, default=None)
    parser_export_nyov_patch.add_argument("--official-csv", type=Path, default=None)
    parser_export_nyov_patch.add_argument("--output-dir", type=Path, default=None)
    parser_apply_nyov_patch = subparsers.add_parser(
        "apply-nyov-official-patch",
        help="Apply approved NYOV official patch rows to an official CSV with backup",
    )
    parser_apply_nyov_patch.add_argument("--official-csv", type=Path, default=None)
    parser_apply_nyov_patch.add_argument("--patch-csv", type=Path, default=None)
    parser_apply_nyov_patch.add_argument("--backup-dir", type=Path, default=None)
    parser_apply_data_patches = subparsers.add_parser(
        "apply-data-patches",
        help="Verify or apply tracked data patch manifests with backups",
    )
    parser_apply_data_patches.add_argument("--patch-dir", type=Path, default=None)
    parser_apply_data_patches.add_argument("--patch-file", type=Path, default=None)
    parser_apply_data_patches.add_argument("--backup-dir", type=Path, default=None)
    parser_import_msd_shs = subparsers.add_parser(
        "import-msd-secondhand",
        help="Import the Million Song Dataset SecondHandSongs subset into staged CSV/SQLite outputs",
    )
    parser_import_msd_shs.add_argument("--input-dir", type=Path, default=None)
    parser_import_msd_shs.add_argument("--output-dir", type=Path, default=None)
    parser_import_msd_shs.add_argument("--track-metadata-db", type=Path, default=None)

    parser_enrich_msd_shs_review = subparsers.add_parser(
        "enrich-msd-secondhand-review",
        help="Enrich MSD SecondHandSongs missing-performance review rows using WhoSampled evidence",
    )
    parser_enrich_msd_shs_review.add_argument(
        "--sources", default="WhoSampled", help="Comma-separated sources to check"
    )
    parser_enrich_msd_shs_review.add_argument(
        "--output-csv", type=Path, default=Path("data/staging/codex/msd_secondhand/msd_shs_missing_performance_whosampled_full.csv")
    )

    args = parser.parse_args()

    if args.command == "build-v2":
        build_v2(write_enabled=args.write)
    elif args.command == "rebuild":
        rebuild(write_enabled=args.write)
    elif args.command == "review-active-vs-staged":
        review_active_vs_staged()
    elif args.command == "quality-report":
        generate_quality_report(write_enabled=args.write)
    elif args.command in {"import-playlist", "import-youtube-music-takeout"}:
        import_playlist(
            write_enabled=args.write,
            input_dir=args.input_dir,
            output=args.output,
            songs_output=args.songs_output,
            cache=args.cache,
            workers=args.workers,
        )
    elif args.command == "verify-youtube-music-takeout":
        verify_youtube_music_takeout(
            write_enabled=args.write,
            input_csv=args.input,
            output_csv=args.output,
            unmatched_csv=args.unmatched,
            summary_json=args.summary,
            cache=args.cache,
            workers=args.workers,
        )
    elif args.command == "verify":
        verify()
    elif args.command == "export-view":
        export_view(write_enabled=args.write)
    elif args.command == "build-reference-db":
        build_reference_db(write_enabled=args.write)
    elif args.command == "metadata-audit":
        metadata_audit(write_enabled=args.write)
    elif args.command == "metadata-audit-main":
        metadata_audit_main(write_enabled=args.write)
    elif args.command == "build-nyov-db":
        build_nyov_db(
            write_enabled=args.write,
            seed_csv=args.seed_csv,
            basket_dir=args.basket_dir,
            output_db=args.output_db,
        )
    elif args.command == "nyov-report":
        nyov_report(
            write_enabled=args.write,
            db_path=args.db_path,
            output_dir=args.output_dir,
            queue_limit=args.queue_limit,
            batch_step=args.batch_step,
            batch_limit=args.batch_limit,
        )
    elif args.command == "verify-nyov-batch":
        verify_nyov_batch(
            write_enabled=args.write,
            db_path=args.db_path,
            batch_step=args.batch_step,
            batch_limit=args.batch_limit,
            providers=args.providers,
            strategy=args.strategy,
            tie_breaker_providers=args.tie_breaker_providers,
        )
    elif args.command == "nyov-verification-summary":
        nyov_verification_summary(
            write_enabled=args.write,
            db_path=args.db_path,
            output_dir=args.output_dir,
        )
    elif args.command == "nyov-promotion-review":
        nyov_promotion_review(
            write_enabled=args.write,
            db_path=args.db_path,
            output_dir=args.output_dir,
        )
    elif args.command == "apply-nyov-promotions":
        apply_nyov_promotions(
            write_enabled=args.write,
            db_path=args.db_path,
            review_csv=args.input,
            promoted_by=args.promoted_by,
        )
    elif args.command == "export-nyov-official-patch":
        export_nyov_official_patch(
            write_enabled=args.write,
            db_path=args.db_path,
            official_csv=args.official_csv,
            output_dir=args.output_dir,
        )
    elif args.command == "apply-nyov-official-patch":
        apply_nyov_official_patch(
            write_enabled=args.write,
            official_csv=args.official_csv,
            patch_csv=args.patch_csv,
            backup_dir=args.backup_dir,
        )
    elif args.command == "apply-data-patches":
        apply_data_patches(
            write_enabled=args.write,
            patch_dir=args.patch_dir,
            patch_file=args.patch_file,
            backup_dir=args.backup_dir,
        )
    elif args.command == "import-msd-secondhand":
        import_msd_secondhand(
            write_enabled=args.write,
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            track_metadata_db=args.track_metadata_db,
        )
    elif args.command == "enrich-msd-secondhand-review":
        enrich_msd_secondhand_review_command.run(
            write_enabled=args.write,
            review_csv=Path("data/staging/codex/msd_secondhand/msd_shs_musicdb_connection_review.csv"),
            sources=args.sources,
            output_csv=args.output_csv,
        )



if __name__ == "__main__":
    main()

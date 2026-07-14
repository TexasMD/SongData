import argparse
import sys
import os
import logging

# Add parent directory to path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import paths
from src.commands import build_v2_local, rebuild, quality_report_local, verify, export_view
from src.commands.placeholders import import_playlist, review_active_vs_staged

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    parser = argparse.ArgumentParser(description="MusicDB CLI")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Explicitly allow write operations (default is dry-run)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_build = subparsers.add_parser("build-v2", help="Build the SQLite database")
    parser_rebuild = subparsers.add_parser("rebuild", help="Rebuild compatibility main CSV from recordings.csv")
    parser_review = subparsers.add_parser("review-active-vs-staged", help="Review staged changes")
    parser_quality = subparsers.add_parser("quality-report", help="Generate a quality report")
    parser_import = subparsers.add_parser("import-playlist", help="Import a playlist")
    parser_verify = subparsers.add_parser("verify", help="Verify data integrity")
    parser_export = subparsers.add_parser("export-view", help="Export data view")

    args = parser.parse_args()
    p = paths()

    if args.command == "build-v2":
        build_v2_local.run(write=args.write, paths=p)
    elif args.command == "rebuild":
        rebuild.run(write=args.write, paths=p)
    elif args.command == "review-active-vs-staged":
        review_active_vs_staged(paths=p)
    elif args.command == "quality-report":
        quality_report_local.run(write=args.write, paths=p)
    elif args.command == "import-playlist":
        import_playlist(write=args.write, paths=p)
    elif args.command == "verify":
        verify.run(write=args.write, paths=p)
    elif args.command == "export-view":
        export_view.run(write=args.write, paths=p)


if __name__ == "__main__":
    main()

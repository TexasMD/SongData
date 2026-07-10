import logging
import argparse
import sys
import os

# Add parent directory to path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.commands.build import build_v2
from src.commands.rebuild import rebuild
from src.commands.quality import generate_quality_report
from src.commands.verify import verify
from src.commands.export import export_view
from src.commands.misc import review_active_vs_staged, import_playlist

def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
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

    parser_verify = subparsers.add_parser("verify", help="Verify data integrity")

    parser_export = subparsers.add_parser("export-view", help="Export data view")

    args = parser.parse_args()

    if args.command == "build-v2":
        build_v2(write_enabled=args.write)
    elif args.command == "rebuild":
        rebuild(write_enabled=args.write)
    elif args.command == "review-active-vs-staged":
        review_active_vs_staged()
    elif args.command == "quality-report":
        generate_quality_report(write_enabled=args.write)
    elif args.command == "import-playlist":
        import_playlist(write_enabled=args.write)
    elif args.command == "verify":
        verify()
    elif args.command == "export-view":
        export_view(write_enabled=args.write)

if __name__ == "__main__":
    main()

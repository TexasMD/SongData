import argparse
import pandas as pd
import sys
from pathlib import Path

# Ensure root directory is in sys.path
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.cover_scraper import scrape_covers

def main():
    parser = argparse.ArgumentParser(description="Bulk scrape cover songs from a CSV list of songs.")
    parser.add_argument("--input", "-i", required=True, help="Input CSV file path")
    parser.add_argument("--output", "-o", required=True, help="Output CSV file path")
    parser.add_argument("--title-col", default="Title", help="Name of the title column (default: Title)")
    parser.add_argument("--artist-col", default="Artist", help="Name of the artist column (default: Artist)")

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: Input file '{input_path}' does not exist.")
        sys.exit(1)

    print(f"Reading input from {input_path}...")
    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)

    if args.title_col not in df.columns:
        print(f"Error: Title column '{args.title_col}' not found in CSV.")
        sys.exit(1)

    if args.artist_col not in df.columns:
        print(f"Error: Artist column '{args.artist_col}' not found in CSV.")
        sys.exit(1)

    all_covers = []

    print(f"Found {len(df)} rows to process.")
    for index, row in df.iterrows():
        title = str(row[args.title_col]).strip()
        artist = str(row[args.artist_col]).strip()

        if not title or title.lower() == 'nan':
            continue

        print(f"[{index + 1}/{len(df)}] Scraping covers for: '{title}' by '{artist}'...")
        try:
            covers = scrape_covers(title, artist)
            for cover in covers:
                cover['query_title'] = title
                cover['query_artist'] = artist
                all_covers.append(cover)
            print(f"  -> Found {len(covers)} covers.")
        except Exception as e:
            print(f"  -> Error scraping '{title}' by '{artist}': {e}")

    if all_covers:
        out_df = pd.DataFrame(all_covers)
        out_df.to_csv(output_path, index=False)
        print(f"Successfully wrote {len(all_covers)} covers to {output_path}")
    else:
        print("No covers found for any of the input songs.")
        # Create empty file with headers
        pd.DataFrame(columns=["query_title", "query_artist", "title", "artist", "musicbrainz_recording_id", "cover_song", "original_title", "original_artist", "original_year", "source"]).to_csv(output_path, index=False)

if __name__ == "__main__":
    main()

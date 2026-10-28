# Scrape Metadata Script Usage

The `scrape_metadata.py` script is a command-line tool designed to parse HTML files from various music data sources (Discogs, MusicBrainz, Spotify, and MediaWiki-based sites like the Elvis Costello Wiki) and aggregate their metadata into a single CSV file.

## Prerequisites

Before running the script, ensure you have the necessary dependencies installed:
```bash
python3 -m pip install -r requirements.txt
```
*(This installs `beautifulsoup4`, which is required for HTML parsing).*

## Command Format

Run the script from the root of the repository using the following format:
```bash
python3 scripts/scrape_metadata.py <input_directory> <output_csv_file>
```

### Arguments:
1. **`input_directory`**: The path to the folder containing the `.html` files you wish to scrape.
2. **`output_csv_file`**: The desired file path where the resulting CSV should be saved.

## Example Usage

```bash
python3 scripts/scrape_metadata.py /tmp/file_attachments/metadatasamples data/exports/metadata_output.csv
```

## Output CSV Structure

The script automatically detects the source schema and extracts data into the following CSV columns:
- **Filename**: Original HTML file name.
- **Source**: Identified platform (Discogs, MusicBrainz, Wiki, Spotify, or Unknown).
- **Title**: The parsed `<title>` of the webpage.
- **JSON_LD**: Serialized JSON representation of any Schema.org data found (common in Discogs).
- **MetaTags**: Serialized JSON of OpenGraph (`og:`) and Twitter (`twitter:`) meta tags (common in Spotify and Discogs).
- **Properties**: Serialized JSON of key-value pairs from definition lists (`<dl>`), primarily for MusicBrainz.
- **Infobox**: Serialized JSON of key-value pairs from Fandom/Wiki infobox tables.
- **Tables**: Serialized JSON containing any generic table rows extracted from the page.

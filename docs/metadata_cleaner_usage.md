# How to Use the Improved Metadata Cleaner

The script provided is a highly robust, unified "core engine" for metadata cleaning that perfectly implements the 8 error categories from the Deepseek analysis document.

Because it's designed as a pure data-transformation function (rather than a standalone CLI tool), the best way to use it is to **import it into your existing pipeline scripts** (like `scripts/cleanup_questionable_rows.py` or `scripts/safe_mojibake_pipeline.py`) to process your rows.

## 1. The Main Entry Point: `clean_row()`
The primary function you will interact with is `clean_row(work, artist, known_artists, canonical)`.

**Inputs it expects:**
*   `work` (str): The raw song/work title.
*   `artist` (str): The raw artist name.
*   `known_artists` (set): A set of strings containing verified, lowercase artist names (e.g., `{"radiohead", "portishead", "alt-j"}`). The engine uses this for safe entity splitting, fixing swapped columns, and decoding leetspeak.
*   `canonical` (dict): A dictionary mapping lowercase names to their correct display casing (e.g., `{"alt-j": "alt-J", "rufus du sol": "RÜFÜS DU SOL"}`).

**Output it returns:**
A dictionary containing the cleaned fields, extracted tags, and a highly detailed audit log of what changed and why.

## 2. Integration Example
To use this script to process your actual data, you would save it as `src/metadata_engine.py` (or similar) and write a wrapper loop like this:

```python
import csv
from src.metadata_engine import clean_row, MusicBrainzClient

def process_csv(input_csv, output_csv):
    known_artists = {"portishead", "radiohead", "alt-j", "elephant revival"}
    canonical = {"alt-j": "alt-J", "rufus du sol": "RÜFÜS DU SOL"}

    results = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_title = row.get("Title", "")
            raw_artist = row.get("Artist", "")

            cleaned_data = clean_row(raw_title, raw_artist, known_artists, canonical)

            new_row = {
                "Original_Title": raw_title,
                "Original_Artist": raw_artist,
                "Cleaned_Title": cleaned_data["work"],
                "Cleaned_Artist": cleaned_data["artist"],
                "Extracted_Venue": cleaned_data["venue"],
                "Extracted_Instrument": cleaned_data["instrument"],
                "Quarantined": cleaned_data["quarantined"],
                "Change_Log": str(cleaned_data["changes"])
            }
            results.append(new_row)

    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
```

## 3. How to use the `MusicBrainzClient`
The script includes a highly optimized API client for MusicBrainz. Because the `clean_row` function relies heavily on knowing if an artist *actually exists* before splitting names or swapping columns, you can use the client to dynamically build your `known_artists` list:

```python
mb_client = MusicBrainzClient(cache_path='mb_cache.json')

# Search for a suspicious string to see if it's a real artist
result = mb_client.search_artist("Alex Goot")

if result['valid']:
    print(f"Found! Official name: {result['canonical_name']} (ID: {result['mbid']})")

    # Add to your engine's dictionaries dynamically:
    known_artists.add(result['canonical_name'].lower())
    canonical[result['canonical_name'].lower()] = result['canonical_name']
```

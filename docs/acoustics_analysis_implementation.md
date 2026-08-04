# Acoustics Analysis Script Implementation Guide

## Overview
The `scripts/acoustics_analysis.py` script matches songs from a provided list (`songlist.txt`) against the main database (`data/processed/Main_Song_Database.csv`) to extract their acoustic and psychoacoustic metadata (e.g., BPM, Energy Level, Danceability, Moods, Vibe).

## Requirements
*   **Python:** 3.8+ (developed with 3.12).
*   **No external packages required:** Only standard library modules (`csv`, `json`, `os`) are used.
*   **Data Dependencies:**
    *   `songlist.txt`: A tab-separated file (or similar simple format) where the first two columns are Title and Artist.
    *   `data/processed/Main_Song_Database.csv`: The main canonical song database.

## Execution
Run the script from the root directory of the repository:
```bash
python3 scripts/acoustics_analysis.py
```

## How It Works
1.  **Loading Input:** Parses `songlist.txt` to extract target Titles and Artists, cleaning up artifact formatting (like leading/trailing quotes).
2.  **Cross-Referencing:** Iterates over the `Main_Song_Database.csv`. It uses a simple case-insensitive exact string match on Title and Artist.
3.  **Data Extraction:** If a match is found, it extracts relevant metrics matching the Spotify data columns present in the database.
4.  **Output:** Saves a structured JSON report to `data/exports/jules/acoustics_report.json`, summarizing the matching success rate and detailing the acoustic metrics for each matched song.

## Extending the Script
*   **Fuzzy Matching:** If the matching rate is low, the `target["Title"].lower() == db_title` logic could be replaced with Levenshtein distance matching (e.g., via the `Levenshtein` package) to handle slight spelling variations or parentheticals (like "(Remastered)").
*   **Adding Missing Data:** If a matched song lacks data in the DB, the script could be extended to use `spotipy` to query the Spotify API in real-time to fill the gaps, though this would change its status from a simple data extractor to an active data fetcher.

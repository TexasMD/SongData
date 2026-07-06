# Antigravity to SQLite Merge Plan

This plan outlines the process of merging Antigravity's latest CSV outputs into a SQLite staging database for review.

## Inputs
- `data/staging/antigravity/mood_event_tag_suggestions.csv`
- `data/staging/antigravity/performance_metadata_suggestions.csv`
- `data/staging/antigravity/external_link_verification.csv`

## Target Database
- `data/staging/jules/music_antigravity_review.sqlite`

## Staging Tables
The following tables will be created in the SQLite database to hold the raw data from the Antigravity CSVs:

1. `antigravity_mood_event_suggestions`: Data from `mood_event_tag_suggestions.csv`.
2. `antigravity_performance_suggestions`: Data from `performance_metadata_suggestions.csv`.
3. `antigravity_external_link_suggestions`: Data from `external_link_verification.csv`.

## Review Views
The following views will be created to facilitate the review of the suggested data:

1. `view_nonblank_tag_suggestions`:
   - Filters `antigravity_mood_event_suggestions` for rows where `Suggested Value` is not blank or null.
2. `view_bpm_key_rows`:
   - Filters `antigravity_performance_suggestions` for rows where the `Field` is either 'BPM' or 'Key'.
3. `view_external_search_urls`:
   - Filters `antigravity_external_link_suggestions` for rows where the source is 'Search Query'.
4. `view_verified_link_candidates`:
   - Filters `antigravity_external_link_suggestions` for rows where the status is 'verified_exact' or similar high-confidence indicators.

## Safety and Constraints
- Do not modify `data/processed/Main_Song_Database.csv`.
- Do not overwrite canonical SQLite tables.
- Keep generated search links separate from verified exact links.
- Only perform write operations when the `--write` flag is provided.

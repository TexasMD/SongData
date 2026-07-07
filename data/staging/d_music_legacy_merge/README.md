# D Music Legacy Merge Report

Generated: 2026-07-04T18:42:51.820019+00:00

## Decision

Use `C:\codex_work\projects\SongDB` as the canonical project. Treat `D:\Music\Main_Song_Database` as a legacy source to mine for missing values and historical analysis.

## Inputs

- Canonical: `C:\codex_work\projects\SongDB\data\processed\Main_Song_Database.csv`
- Legacy: `D:\Music\Main_Song_Database\data\processed\Main_Song_Database.csv`

## Results

- Canonical rows: 9642
- Legacy rows: 9369
- Candidate rows: 9648
- Canonical rows enriched from legacy: 7041
- Legacy-only rows appended to candidate: 6
- Ambiguous duplicate key groups skipped: 1076

## Outputs

- Candidate CSV: `C:\codex_work\projects\SongDB\data\staging\d_music_legacy_merge\merged_candidate_Main_Song_Database.csv`
- Legacy-only appended rows: `C:\codex_work\projects\SongDB\data\staging\d_music_legacy_merge\d_music_only_appended_rows.csv`
- Ambiguous matches: `C:\codex_work\projects\SongDB\data\staging\d_music_legacy_merge\ambiguous_matches.csv`
- JSON summary: `C:\codex_work\projects\SongDB\data\staging\d_music_legacy_merge\merge_summary.json`

## Safety Notes

The active `Main_Song_Database.csv` was not modified.

The D: scripts were not copied into active scripts. One legacy script contains hardcoded Spotify credentials and brittle absolute paths. Rotate that Spotify app secret before using any related automation again.

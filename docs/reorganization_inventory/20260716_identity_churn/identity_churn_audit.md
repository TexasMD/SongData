# Identity churn audit - 2026-07-16

This audit reviews the remaining generated CSV churn after clean scalar and playlist patches were promoted.

## Findings

- `recordings.csv`: 20 added IDs and 52 removed IDs. 0 replacement pairs matched by normalized title/artist/version/album/duration; 20 added and 52 removed remain unpaired.
- `songs.csv`: 16 added IDs and 52 removed IDs. 0 replacement pairs matched by normalized canonical title/artist/release/year; 16 added and 52 removed remain unpaired.
- `external_links.csv`: 63 row additions and 63 row removals. 0 rows matched as link identity replacements when recording/song IDs changed but site and URL signature stayed stable.
- `Main_Song_Database.csv`: 22 added row versions and 22 removed row versions; this needs source-level review before promotion.

## Generated artifacts

- `identity_churn_summary.json`
- `recordings_id_replacements.csv`
- `recordings_unpaired_added.csv`
- `recordings_unpaired_removed.csv`
- `songs_id_replacements.csv`
- `songs_unpaired_added.csv`
- `songs_unpaired_removed.csv`
- `external_link_id_replacements.csv`
- `recordings_possible_id_matches.csv`
- `songs_possible_id_matches.csv`
- `main_database_changed_rows_added.csv`
- `main_database_changed_rows_removed.csv`

## Possible fuzzy matches

- `recordings_possible_id_matches.csv`: 8 candidate old/new ID relationships above the fuzzy threshold.
- `songs_possible_id_matches.csv`: 6 candidate old/new ID relationships above the fuzzy threshold.

These are review leads, not approved replacements.

## Recommendation

Do not promote the generated CSV files wholesale. The fuzzy matches are useful
review leads, but the strict matcher found no clean replacement pairs and the
unpaired additions/removals show this is still a rebuild/identity-generation
issue rather than a clean data patch. Delegate a second review to Jules or
Antigravity before accepting any ID replacement as official.

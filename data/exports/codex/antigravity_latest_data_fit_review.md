# Antigravity Data Fit Review

## Verdict

The latest Antigravity CSVs fit their intended purpose as SQLite staging/review inputs. They do not fit promotion into canonical `recordings` or `external_links` fields yet.

## Findings

- Recording IDs: all rows map to known `SongDB_v2/recordings.csv` IDs.
- Mood/event: 9,672 rows, but only 15 rows have nonblank tag suggestions. Suggested tags are mostly Last.fm genre descriptors and are mostly outside `tag_options.csv`.
- Performance: 9,672 rows, all Low confidence. BPM/key values exactly duplicate existing `SongDB_v2` values; default tuning/capo/difficulty/instrumentation is applied to every row and should not be promoted.
- External links: 29,016 rows, but 0 verified URLs. These are search-query URLs only.

## Recommendation For Jules

Merge into SQLite as staging tables only:

- `antigravity_mood_event_suggestions`
- `antigravity_performance_suggestions`
- `antigravity_external_link_suggestions`

Add review views for nonblank tags, BPM/key suggestions, and external search URLs. Do not overwrite canonical SQLite tables or source CSVs from this batch.

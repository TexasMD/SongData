# SQLite Antigravity Review Findings

Database inspected:

`D:\Music\MusicDB\data\staging\jules\music_antigravity_review.sqlite`

Views inspected:

- `v_antigravity_tag_review`
- `v_antigravity_bpm_key_review`

## Verdict

The Antigravity data is useful only as a staging/search/review layer. I would not promote these results into canonical tables or the active CSV.

## Tag Review Findings

Rows inspected: 15

All 15 tag-review rows are flagged.

Main issues:

- Suggested tags are mostly Last.fm genre/descriptive tokens, not controlled mood/event/situation vocabulary.
- Every tag-review row contains at least one token outside `tag_options`.
- Examples of inappropriate tokens for mood/event/situation fields: `90s`, `70s`, `female vocalists`, `2pac`, `rap`, `hip-hop`, `pop`, `rock`, `metal`, `country`, `alternative`, `covers`, `soft rock`, `classic rock`.
- One row repeats `female vocalists` twice.
- Confidence is only Medium, not High.

Most likely action:

- Do not promote these directly.
- Either map a small number manually to controlled tags or return to Antigravity with stricter vocabulary constraints.

Detailed flags:

`data\exports\codex\sqlite_antigravity_review\v_antigravity_tag_review_flags.csv`

## BPM/Key Review Findings

Rows inspected: 1,019

All 1,019 BPM/key review rows are flagged.

Main issues:

- Every row is Low confidence.
- Every row uses `Generative Suggestion` as source.
- 1,007 rows duplicate existing canonical BPM/key values already in SQLite `recordings`.
- The remaining 12 rows did not join to SQLite `recordings`, so the apparent new BPM/key values are not trustworthy in this review DB.
- BPM values are in plausible numeric range, and key format is syntactically valid, but source/confidence make them unsuitable for promotion.

Most likely action:

- Do not promote BPM/key values from this batch.
- Use the view only to verify SQLite staging mechanics.
- Rebuild the SQLite prototype from current `SongDB_v2` before further review, because some Antigravity IDs do not join.

Detailed flags:

- `data\exports\codex\sqlite_antigravity_review\v_antigravity_bpm_key_review_flags.csv`
- `data\exports\codex\sqlite_antigravity_review\v_antigravity_bpm_key_review_nonredundant_flags.csv`

## SQLite Join Integrity

Antigravity rows missing a matching SQLite `recordings` row:

- mood suggestions: 27
- performance suggestions: 27
- external-link suggestions: 81, because there are three link rows per missing recording ID
- BPM/key review rows with missing recording join: 12

This suggests `music_antigravity_review.sqlite` is stale or was built from a different recording snapshot than the latest Antigravity CSVs.

## Recommendation To Jules

1. Keep the Antigravity tables as staging tables only.
2. Rebuild `music_antigravity_review.sqlite` from current `SongDB_v2` before deeper review.
3. Do not update canonical `recordings`, `songs`, or `external_links` from these views.
4. Add a SQLite QA view/report for Antigravity rows that fail to join `recordings`.
5. Add controlled-vocabulary validation for tag suggestions.

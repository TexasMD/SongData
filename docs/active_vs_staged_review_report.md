# Active vs Staged MusicDB Review Report

Generated: 2026-07-04T21:55:27.336223+00:00

## Files Compared

- Active main DB: `D:\Music\MusicDB\data\processed\Main_Song_Database.csv`
- Staged conservative candidate: `D:\Music\MusicDB\data\staging\d_music_legacy_merge\merged_candidate_Main_Song_Database.csv`

## Snapshot Evidence

- Active rows: 9,672
- Staged rows: 9,648
- Active columns: 58
- Staged columns: 60
- Active SHA256: `91c026c9a99f38a11de04a09a754b80f333b93ff4eb600a7d2076fd22694592e`
- Staged SHA256: `b4b99aaf3210c1bd70de2e0807443012c7ee43b6d02a87a5670f47d0428e2911`

## Schema Differences

- Active-only columns: Spotify ID
- Staged-only columns: Legacy D Music Spotify ID, Legacy D Music Verification Notes, Legacy D Music Source Files

## Row-Level Findings

- Row-count delta, active minus staged: 24
- Active-only row signatures: 63
- Staged-only row signatures: 39
- Signature count difference groups: 99
- Song keys only in active: 0
- Song keys only in staged: 0
- Active duplicate song-key groups: 1,087
- Staged duplicate song-key groups: 1,067

## Unambiguous Song-Key Comparison

- Unambiguous song keys compared: 7,251
- Field differences in unambiguous matches: 6,289

Top field-difference counts:

| Field | Difference Type | Count |
| --- | --- | ---: |
| MusicBrainz Verified | staged_only_value | 1,810 |
| Spotify Track ID | staged_only_value | 1,322 |
| Energy | staged_only_value | 856 |
| Vibe | staged_only_value | 856 |
| BPM | staged_only_value | 855 |
| Spotify Verified | staged_only_value | 481 |
| Genre | staged_only_value | 75 |
| Genre | conflict_both_nonblank | 22 |
| Duration | conflict_both_nonblank | 7 |
| Album | conflict_both_nonblank | 4 |
| Spotify Verified | conflict_both_nonblank | 1 |

## Spotify ID Review

| Status | Count |
| --- | ---: |
| already_same | 544 |
| conflict_spotify_id_differs_from_track_id | 82 |
| no_legacy_spotify_id | 7,388 |
| safe_to_copy_spotify_id_to_spotify_track_id | 1,658 |

- Spotify ID conflicts between unambiguous active/staged matches: 0

## Output Tables

- `data/exports/active_vs_staged_review/active_only_rows.csv`
- `data/exports/active_vs_staged_review/staged_only_rows.csv`
- `data/exports/active_vs_staged_review/signature_count_differences.csv`
- `data/exports/active_vs_staged_review/field_differences_unambiguous_song_keys.csv`
- `data/exports/active_vs_staged_review/field_difference_summary.csv`
- `data/exports/active_vs_staged_review/spotify_id_normalization_review.csv`
- `data/exports/active_vs_staged_review/spotify_id_conflicts_between_active_and_staged.csv`
- `data/exports/active_vs_staged_review/duplicate_song_key_groups.csv`
- `data/exports/active_vs_staged_review/summary.json`

## Recommendation

Do not replace the active database with the staged candidate wholesale.

The active database has more rows and includes a legacy `Spotify ID` column. The staged candidate has more explicit legacy provenance columns and was produced by a more conservative merge. The safest path is to keep the active database as the current source of truth, then apply targeted improvements from this review:

1. Normalize safe `Spotify ID` values into `Spotify Track ID` where the review marks them safe.
2. Review active-only and staged-only row signatures before deleting or appending anything.
3. Review both-nonblank conflicts for album, duration, year, and Spotify identifiers before promotion.
4. Preserve the staged candidate's legacy provenance columns in the next canonical schema.

This report is read-only. No database rows were changed.

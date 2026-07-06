# Codex Issue #3 Patch Candidate

Generated: 2026-07-05T04:13:36.202048+00:00

## Inputs

- Active DB: `D:\Music\MusicDB\data\processed\Main_Song_Database.csv`
- Staged candidate: `D:\Music\MusicDB\data\staging\d_music_legacy_merge\merged_candidate_Main_Song_Database.csv`
- Spotify review: `D:\Music\MusicDB\data\exports\active_vs_staged_review\spotify_id_normalization_review.csv`
- Field differences: `D:\Music\MusicDB\data\exports\active_vs_staged_review\field_differences_unambiguous_song_keys.csv`

## Outputs

- Patch candidate: `D:\Music\MusicDB\data\staging\codex\active_main_patch_candidate.csv`
- Patch actions: `D:\Music\MusicDB\data\exports\codex\active_main_patch_actions.csv`
- Skipped/manual-review rows: `D:\Music\MusicDB\data\exports\codex\active_main_patch_skipped_review.csv`
- Summary JSON: `D:\Music\MusicDB\data\exports\codex\active_main_patch_summary.json`
- Verification JSON: `D:\Music\MusicDB\data\exports\codex\active_main_patch_verification.json`

## Safety

- Active DB modified: `False`
- Active SHA before: `91c026c9a99f38a11de04a09a754b80f333b93ff4eb600a7d2076fd22694592e`
- Active SHA after: `91c026c9a99f38a11de04a09a754b80f333b93ff4eb600a7d2076fd22694592e`
- Overwrite violations: 0
- Staged-only Spotify Track IDs represented in candidate: 1,322 / 1,322
- Staged-only Spotify Track ID mismatches: 0

## Candidate Shape

- Active rows: 9,672
- Candidate rows: 9,672
- Active columns: 58
- Candidate columns: 61
- Added columns: Legacy D Music Spotify ID, Legacy D Music Verification Notes, Legacy D Music Source Files

## Patch Actions

- Total proposed cell/field actions: 21,791

| Action Type | Count |
| --- | ---: |
| safe_spotify_id_normalization | 1,658 |
| staged_only_metadata_copy | 4,933 |
| staged_provenance_copy | 15,200 |

| Field | Count |
| --- | ---: |
| Legacy D Music Source Files | 7,034 |
| Legacy D Music Verification Notes | 6,303 |
| Legacy D Music Spotify ID | 1,863 |
| MusicBrainz Verified | 1,810 |
| Spotify Track ID | 1,658 |
| Energy | 856 |
| Vibe | 856 |
| BPM | 855 |
| Spotify Verified | 481 |
| Genre | 75 |

## Left For Manual Review

- Skipped/manual-review entries: 218
- Active Spotify ID conflicts: 82
- Active-only row signatures: 63
- Staged-only row signatures: 39

## Recommendation

Review the patch actions and skipped-review CSVs before any promotion. If accepted, run `python scripts\promote_active_main_patch_candidate.py` first as a dry run. A real promotion requires `python scripts\promote_active_main_patch_candidate.py --write`, which validates reviewed hashes and row counts, creates a timestamped backup, then replaces `data/processed/Main_Song_Database.csv` with the reviewed candidate.

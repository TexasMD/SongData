# Remaining Dirty Tree Triage

This triage covers the uncommitted files left after commit `97d3de3`
(`Stabilize repo hygiene and test discovery`).

## Summary

The remaining changes are not one cleanup. They are at least five separate
work packages:

1. YouTube Music Takeout import, verification, and SongDB v2 merge support.
2. Reference-ID registry, metadata audit, and API read model.
3. Display/search normalization for mangled or percent-escaped source text.
4. Documentation/coordination updates reflecting issues and product goals.
5. Local workbench artifacts in `basket/` and root scratch scripts.

Do not commit these together. Split them into reviewable commits after rebasing
the cleanup branch onto current `origin/main`.

## Commit Candidates

These appear to be source/doc/test changes that should be reviewed as logical
feature commits, not archived:

### Reference-ID Registry

- `src/reference_db.py`
- `src/commands/build_reference_db.py`
- `src/commands/metadata_audit.py`
- `docs/reference_id_database.md`
- `data/source_registry.csv`
- `data/staging/jules/MusicDB.sqlite` should not be committed as a binary data
  artifact without an explicit data policy decision.
- Related modified files:
  - `api/main.py`
  - `scripts/musicdb.py`
  - `src/config.py`
  - `tests/test_cli.py`
  - `tests/test_config_and_commands.py`

Recommendation: split into one code/doc commit plus a separate generated-data
decision. Keep `reference_ids.sqlite` and generated audit outputs local unless
explicitly approved.

### YouTube Music Takeout Import and Verification

- `src/youtube_music_takeout.py`
- `scripts/verify_youtube_music_takeout.py`
- related `scripts/musicdb.py` CLI additions
- related `scripts/build_songdb_v2.py` updates
- tests:
  - `tests/test_verify_youtube_music_takeout.py`
  - `tests/test_youtube_music_takeout.py`

Recommendation: keep as a feature branch/commit only after removing hardcoded
personal default paths from `scripts/musicdb.py` or making them required CLI
arguments/config values.

### Display and Search Normalization

- `src/normalization.py`
- `src/db_access.py`
- `src/vibe_search.py`
- `api/main.py`
- tests:
  - `tests/test_api_display_normalization.py`
  - `tests/test_display_normalization.py`
  - relevant portions of `tests/test_db_access_and_vibe.py`

Recommendation: keep as a focused behavior commit because it improves API/UI
display safety and search matching for mangled source text.

### Questionable Row Cleanup

- `scripts/cleanup_questionable_rows.py`
- `scripts/normalize_csv_documents.py`
- `tests/test_normalize_csv_documents.py`
- related docs/workstream notes

Recommendation: keep as a separate cleanup-tool commit only if the scripts are
documented as dry-run/report-first and do not directly mutate active data without
backup and explicit `--write`.

## Data and Generated Artifact Decisions

These need an explicit data policy decision before commit:

- `data/processed/Main_Song_Database.csv`
- `SongDB_v2/external_links.csv`
- `SongDB_v2/manifest.json`
- `SongDB_v2/playlist_membership.csv`
- `SongDB_v2/recordings.csv`
- `SongDB_v2/songs.csv`

Recommendation: do not include them in a reorganization commit. If these are
canonical derived data, commit them only with rebuild command, row counts, and
source summary. If generated, keep them local.

## Documentation Candidates

- `.github/ISSUE_TEMPLATE/agent-task.md`
- `AGENT_COORDINATION.md`
- `README.md`
- `SongDB_v2/README.txt`
- `docs/WORKSTREAMS.md`
- `docs/agent_operating_model.md`
- `docs/github_coordination.md`
- `docs/proposed_improvement_plan.md`
- `plan.md`

Recommendation: split evergreen docs from transient planning. Root-level
`plan.md` should likely be merged into `docs/` or archived, not kept as a root
planning file.

## Archive-to-D Candidates

These are untracked local workbench/scratch files and should be moved outside
the Git working tree, preserving them under
`D:\Music\MusicDB_local_artifacts\phase2_dirty_tree_triage\20260715_022740\`:

- `basket/needs clen.txt`
- `basket/reverify_spotify.ps1`
- `basket/reverify_spotify.py`
- `basket/reverify_spotify_parallel.ps1`
- `basket/reverify_spotify_parallel.py`
- `basket/run_coverdata_from_spotify_reverified.ps1`
- `basket/watch_coverdata_status.ps1`
- `basket/whosampled_cover_extractor.py`
- `basket/whosampled_cover_extractor_instructions.md`
- `find_conflicts.ps1`

Recommendation: archive now. Promote any of these back into `scripts/` later
only after review, naming cleanup, CLI integration, and tests.

## Manual Review Blockers

- `basket/coverdata_shs_ci.py` is tracked and modified even though it lives in a
  workbench-style folder. Review before deciding whether to keep it tracked,
  move it to `scripts/`, or retire it.
- `data/staging/jules/MusicDB.sqlite` is tracked and modified. Decide whether
  this binary belongs in Git. Prefer reproducible build scripts over committing
  local SQLite outputs.

## Recommended Next Sequence

1. Archive the untracked workbench/scratch files listed above to the D: artifact
   folder.
2. Commit this triage report as documentation.
3. Use `git stash push --include-untracked` only after the remaining files are
   split or explicitly preserved, because the active DB and tracked generated
   files are still modified.
4. Rebase this branch onto `origin/main`.
5. Re-apply or split remaining changes into the feature groups above.

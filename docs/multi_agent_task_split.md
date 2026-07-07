# Multi-Agent Task Split for MusicDB

## Goal

Divide MusicDB work between Codex, Antigravity, and Jules without corrupting the active database.

The active database remains:

`D:\Music\MusicDB\data\processed\Main_Song_Database.csv`

Do not replace it wholesale with the staged candidate. Keep the active DB as the current source of truth, then selectively apply useful metadata and provenance from the staged candidate.

## Recommended Ownership

| Agent | Best Role | Should Write To | Should Not Do |
| --- | --- | --- | --- |
| Codex | Integration owner, schema decisions, final data promotion | `docs`, `scripts`, `data\exports`, reviewed writes to `data\processed` | Blind bulk enrichment or unreviewed external lookups |
| Antigravity | Bulk research/enrichment, tagging, web-heavy verification | `data\staging\antigravity`, `data\exports\antigravity` | Overwrite active main DB or store API keys in scripts |
| Jules | Automation, tests, CLI, repo hygiene, SQLite prototype | `scripts`, `tests`, `docs`, `data\staging\jules` | Decide music metadata truth without review |

## Workstream 1: Make MusicDB Canonical

Owner: Codex

Tasks:

1. Keep `D:\Music\MusicDB` as canonical.
2. Keep `C:\codex_work\projects\SongDB` as prior working source.
3. Keep `D:\Music\Main_Song_Database` as legacy archive only.
4. Maintain `README.md`, `AGENT_COORDINATION.md`, and system docs.
5. Create backups before any active DB write.

Deliverables:

- Updated documentation.
- Backup manifest for any data write.
- Final promotion notes when staged data is applied.

## Workstream 2: Resolve Active vs Staged Candidate

Owner: Codex

Inputs:

- `data\processed\Main_Song_Database.csv`
- `data\staging\d_music_legacy_merge\merged_candidate_Main_Song_Database.csv`
- `data\exports\active_vs_staged_review\`

Tasks:

1. Normalize safe `Spotify ID` values into `Spotify Track ID`.
2. Preserve staged provenance columns:
   - `Legacy D Music Spotify ID`
   - `Legacy D Music Verification Notes`
   - `Legacy D Music Source Files`
3. Review the 63 active-only row signatures.
4. Review the 39 staged-only row signatures.
5. Review the 82 active rows where `Spotify ID` conflicts with `Spotify Track ID`.
6. Review album, duration, genre, and verification conflicts.

Deliverables:

- `data\staging\codex\active_main_patch_candidate.csv`
- `data\exports\codex\active_main_patch_summary.json`
- A reviewed promotion script.

## Workstream 3: Promote `recordings.csv` as the Working Layer

Owner: Codex with Jules support

Codex tasks:

1. Define the final schema for recordings, songs, external links, playlists, tags, and performance notes.
2. Decide which fields remain in the compatibility main CSV.
3. Define identity rules for versions, covers, remixes, live tracks, and compilations.

Jules tasks:

1. Add schema validation tests.
2. Add a command to rebuild normalized tables.
3. Add tests that prove no active DB write happens without an explicit `--write`.

Deliverables:

- Schema document.
- Validation script.
- Tests.
- Rebuild command.

## Workstream 4: Improve Mood, Event, and Playlist Tagging

Owner: Antigravity

Tasks:

1. Start with playlist rows, especially NRG.
2. Assign mood tags, event tags, situation tags, setlist role, and crowd energy.
3. Use controlled vocabulary from `SongDB_v2\tag_options.csv`; propose additions separately.
4. Include confidence and rationale.

Output format:

`data\staging\antigravity\mood_event_tag_suggestions.csv`

Required columns:

- `Recording ID`
- `Title`
- `Artist`
- `Suggested Field`
- `Suggested Value`
- `Confidence`
- `Rationale`
- `Source`

Codex should review and promote accepted tags.

## Workstream 5: Add Musician-Performance Fields

Owner: Antigravity

Tasks:

1. Fill key, BPM, time signature, tuning, capo, guitar difficulty, bass difficulty, drum difficulty, vocal range, instrumentation, and arrangement notes.
2. Prioritize songs in playlists and likely performance songs.
3. Prefer verified or sourced data.
4. Do not guess exact values without marking confidence.

Output format:

`data\staging\antigravity\performance_metadata_suggestions.csv`

Required columns:

- `Recording ID`
- `Title`
- `Artist`
- `Field`
- `Suggested Value`
- `Instrument`
- `Confidence`
- `Source URL`
- `Notes`

## Workstream 6: Verify SecondHandSongs, WhoSampled, and Ultimate Guitar Links

Owner: Antigravity

Tasks:

1. Verify exact SecondHandSongs pages.
2. Verify exact WhoSampled pages.
3. Verify Ultimate Guitar official tab pages.
4. If no official tab exists, select the best popular matching tab.
5. Mark no-match rows explicitly instead of leaving ambiguity.

Output format:

`data\staging\antigravity\external_link_verification.csv`

Required columns:

- `Recording ID`
- `Title`
- `Artist`
- `Site`
- `Search URL`
- `Verified URL`
- `Link Status`
- `Match Type`
- `Confidence`
- `Last Checked`
- `Notes`

Allowed link statuses:

- `verified_exact`
- `official_tab_verified`
- `best_tab_verified`
- `no_good_match`
- `needs_review`

## Workstream 7: Improve Automation and Quality Checks

Owner: Jules

Tasks:

1. Create a single CLI entrypoint, for example `scripts\musicdb.py`.
2. Add subcommands:
   - `build-v2`
   - `review-active-vs-staged`
   - `quality-report`
   - `import-playlist`
   - `verify`
   - `export-view`
3. Add tests for:
   - normalization
   - stable ID generation
   - duplicate detection
   - dry-run behavior
   - schema validation
4. Add a quality report that summarizes missing identifiers, missing BPM/key, duplicate groups, missing external links, and unreviewed staged suggestions.

Deliverables:

- `scripts\musicdb.py`
- `tests\`
- `data\exports\quality_report.json`
- `data\exports\quality_report.md`

## Workstream 8: Consider SQLite While Preserving CSV

Owner: Jules, with Codex review

Tasks:

1. Build a SQLite proof of concept from existing CSVs.
2. Do not make SQLite the only copy of the data.
3. Keep CSV export commands.
4. Add views for:
   - playlist songs
   - mood/event filters
   - musician-performance readiness
   - external link verification status
   - duplicate/version review

Deliverables:

- `data\staging\jules\MusicDB.sqlite`
- `scripts\export_sqlite_to_csv.py`
- `docs\sqlite_prototype_notes.md`

## Suggested Prompts

### Prompt for Codex

Use `D:\Music\MusicDB` as the canonical project. Read `AGENT_COORDINATION.md`, `docs\active_vs_staged_review_report.md`, and `docs\proposed_improvement_plan.md`. Do not replace `data\processed\Main_Song_Database.csv` wholesale. Create a reviewed patch candidate that selectively applies staged metadata and provenance to the active DB, starting with safe Spotify ID normalization and staged-only metadata fields. Write outputs under `data\staging\codex` and `data\exports\codex`.

### Prompt for Antigravity

Use `D:\Music\MusicDB` as the canonical project. Do not overwrite `data\processed\Main_Song_Database.csv`. Your job is enrichment only. Read `AGENT_COORDINATION.md` and use `SongDB_v2\recordings.csv` as input. Create staged CSV suggestions for mood/event tags, musician-performance metadata, and verified SecondHandSongs/WhoSampled/Ultimate Guitar links. Include confidence, source URL, and notes for every suggestion. Write outputs under `data\staging\antigravity`.

### Prompt for Jules

Use `D:\Music\MusicDB` as the canonical project. Do not modify the active main CSV. Read `AGENT_COORDINATION.md` and `docs\proposed_improvement_plan.md`. Your job is automation and quality. Create a CLI entrypoint, tests, schema validation, quality reports, and a SQLite proof of concept that preserves CSV export. Write code under `scripts` and tests under `tests`; write generated outputs under `data\staging\jules` or `data\exports`.

## Integration Cadence

1. Each agent works in its assigned output folders.
2. Codex reviews staged outputs.
3. Codex creates a promotion candidate.
4. A backup is made.
5. A dry-run summary is generated.
6. Only then is the active main DB modified.

## First Three Moves

1. Codex: create a patch candidate for safe Spotify ID normalization.
2. Antigravity: enrich the NRG playlist with mood/event and performance metadata.
3. Jules: add the CLI/quality-report/test framework.

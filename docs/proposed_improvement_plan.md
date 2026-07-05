# Proposed MusicDB Improvement Plan

## Executive Recommendation

Make `D:\Music\MusicDB` the canonical music database system.

Keep `data/processed/Main_Song_Database.csv` as the current compatibility/source CSV for now, but gradually shift day-to-day work to the normalized `SongDB_v2` tables, especially `SongDB_v2/recordings.csv`.

The long-term target is a music system that can answer practical questions quickly:

- What should I play for this mood, event, or setting?
- What songs fit this tempo, key, or instrumentation?
- What can I play on guitar, bass, or drums tonight?
- Which version of this song is the original, the cover, the remix, or the live version?
- Where are the best tabs, sample/covers data, and external references?

## Current State

As of this plan:

- Active main database: `data/processed/Main_Song_Database.csv`
- Main rows: 9,672
- Main columns: 58
- Structured recordings: 9,672
- Structured recording columns: 67
- Structured songs: 9,533
- External-link rows: 29,016
- Playlist-membership rows: 223

Coverage highlights:

- Album filled: 9,114 rows
- Duration filled: 9,080 rows
- Genre filled: 8,724 rows
- Year filled: 9,101 rows
- Spotify Track ID filled: 2,785 rows
- Spotify popularity filled: 2,785 rows
- BPM filled: 1,018 rows
- Key filled: 1,019 rows
- Playlist membership filled: 223 rows
- Exact SecondHandSongs URLs: 0 rows
- Exact WhoSampled URLs: 0 rows
- Exact Ultimate Guitar tab URLs: 0 rows
- Musician-performance fields such as tuning, capo, difficulty, vocal range, and instrumentation: 0 rows

## Guiding Principles

1. Preserve the active main CSV until the normalized system is proven.
2. Treat exact external URLs as verified data, not guessed data.
3. Keep generated search links separate from verified exact links.
4. Use one row per distinct recording or version.
5. Prefer the first-published album, single, or soundtrack for the primary release.
6. Store greatest-hits, deluxe, remaster, anthology, and compilation releases as alternates.
7. Do not merge live versions, remixes, acoustic versions, edits, covers, or instrumentals unless intentionally interchangeable.
8. Use environment variables for credentials. Do not store API keys in scripts.
9. Make every destructive action reversible through backups, staging files, or reports.

## Target Architecture

### Operational Tables

The normalized system should move toward these tables:

- `songs.csv`: written song or title/artist identity.
- `recordings.csv`: specific recording/version; primary working table.
- `works.csv`: composition-level grouping, ideally with MusicBrainz Work IDs.
- `releases.csv`: album, single, soundtrack, compilation, or reissue data.
- `playlist_membership.csv`: normalized playlist membership.
- `external_links.csv`: SecondHandSongs, WhoSampled, Ultimate Guitar, MusicBrainz, Spotify, Discogs, and other links.
- `performance_notes.csv`: guitar, bass, drums, vocals, tuning, capo, difficulty, and arrangement notes.
- `tags.csv`: controlled mood, event, situation, energy, and setlist-role tags.
- `source_observations.csv`: raw facts from Spotify, MusicBrainz, Discogs, iTunes, SecondHandSongs, WhoSampled, or manual review.

### Preferred Identifiers

- Internal stable ID: `Recording ID`
- Specific recording/version: `MusicBrainz Recording ID` when verified
- Written composition: `MusicBrainz Work ID` when verified
- Commercial audio code: `ISRC`
- Spotify-specific track: `Spotify Track ID`
- Legacy preserved ID: `Legacy Spotify ID`

## Phase 1: Stabilize the Canonical System

Goal: make `D:\Music\MusicDB` safe, auditable, and clearly canonical.

Tasks:

1. Keep `D:\Music\MusicDB` as the canonical project root.
2. Keep `D:\Music\Main_Song_Database` archived as legacy source input only.
3. Keep `C:\codex_work\projects\SongDB` as a prior working/source reference, not the main database.
4. Commit or snapshot the current MusicDB state before further data changes.
5. Create a `data/backups` or timestamped backup before any write operation.
6. Keep all API credentials in environment variables.
7. Rotate exposed legacy Spotify and Discogs credentials.

Acceptance criteria:

- No active script contains literal credentials.
- All active scripts compile.
- `SongDB_v2` can be rebuilt from the active main CSV.
- The README names `D:\Music\MusicDB` as the canonical project.

## Phase 2: Resolve Source-of-Truth Differences

Goal: decide whether the active 9,672-row database or the conservative 9,648-row staged candidate is the best source of truth.

Tasks:

1. Generate a review report for rows in the 9,672-row active main DB that are not in the 9,648-row staged candidate.
2. Review the 1,076 ambiguous duplicate groups from the legacy merge.
3. Normalize `Spotify ID` into `Spotify Track ID` where it is clearly the same identifier.
4. Keep legacy-only or questionable values in clearly marked legacy fields.
5. Produce a proposed final `Main_Song_Database_candidate.csv`.
6. Promote the candidate only after row counts, schema, and sample records are verified.

Acceptance criteria:

- Every appended or removed row has a report trail.
- Ambiguous duplicates are not automatically merged.
- The promoted database has a clear backup.
- `SongDB_v2` is regenerated after promotion.

## Phase 3: Make Recordings the Working Layer

Goal: make `SongDB_v2/recordings.csv` the primary table for actual use.

Tasks:

1. Add stable IDs to the main database or treat `Recording ID` as the operational key.
2. Stop using title/artist alone as a merge key.
3. Add `Version Type` with values such as original, cover, remix, live, acoustic, radio_edit, extended, instrumental, demo.
4. Add `Primary Release Type` with values such as album, single, soundtrack, compilation, greatest_hits, deluxe, remaster.
5. Add `First Published Release` and `First Published Date` when known.
6. Create validation reports for missing title, artist, album, duration, year, and identifier fields.

Acceptance criteria:

- A song with multiple versions can be represented without title hacks.
- Greatest-hits references do not overwrite original release references.
- Every row has a stable internal recording identifier.

## Phase 4: Enrich Mood, Event, and Playlist Use

Goal: make the database useful for quickly gathering songs by mood, circumstance, or event.

Tasks:

1. Expand `tag_options.csv` into a more complete controlled vocabulary.
2. Add normalized tag assignments instead of relying only on semicolon text columns.
3. Create starter tag groups:
   - mood: dark, bright, wistful, aggressive, romantic, dreamy, anthemic, funny, melancholy
   - situation: road_trip, late_night, dinner, work_focus, rainy_day, pregame, afterparty
   - event: wedding, cookout, halloween, workout, bar_band, house_party
   - setlist role: opener, closer, encore, peak_energy, breather, transition
4. Import more playlists into `playlist_membership.csv`.
5. Build saved views or export files for common use cases.

Acceptance criteria:

- At least the playlist songs have mood/event tags.
- Common queries can be answered without manually filtering dozens of columns.
- Playlist membership is stored in a normalized table.

## Phase 5: Add Musician-Performance Data

Goal: make the database useful when playing guitar, bass, drums, or vocals.

Tasks:

1. Fill BPM and key coverage beyond the current roughly 1,019 rows.
2. Add or populate:
   - time signature
   - tuning
   - capo
   - guitar difficulty
   - bass difficulty
   - drum difficulty
   - vocal range
   - instrumentation
   - main riff or hook
   - solo
   - arrangement notes
3. Start with high-value playlists, especially NRG and any performance/setlist playlists.
4. Add confidence/source fields for each musical fact.
5. Create a musician-ready export for songs that have enough performance data.

Acceptance criteria:

- NRG playlist songs have BPM/key coverage where available.
- Performance fields distinguish verified/manual entries from inferred data.
- A band-practice export can be generated from the database.

## Phase 6: Verify External Links

Goal: turn generated search links into verified exact resources.

Tasks:

1. Verify SecondHandSongs exact pages for originals and covers.
2. Verify WhoSampled exact pages for sampled, covered, or remixed songs.
3. Verify Ultimate Guitar official tab URLs.
4. If no official Ultimate Guitar tab exists, store the best matching popular tab.
5. Add link status values:
   - search_link_generated
   - verified_exact
   - no_good_match
   - needs_review
6. Store last-checked dates.

Acceptance criteria:

- Verified URLs are never populated from guesses.
- Search URLs remain available as discovery links.
- Ultimate Guitar links distinguish official from best-available user tabs.

## Phase 7: Improve Automation and Quality Control

Goal: make updates repeatable and safer.

Tasks:

1. Add a single `musicdb.py` command-line entrypoint with subcommands:
   - `build-v2`
   - `audit-duplicates`
   - `import-playlist`
   - `verify`
   - `export-view`
   - `quality-report`
2. Add a quality report script for coverage counts and duplicate warnings.
3. Add tests for normalization, ID generation, and non-destructive merge behavior.
4. Add dry-run mode to every script that can modify data.
5. Use reports in `data/exports` for every import, merge, and verification pass.

Acceptance criteria:

- A routine update can be run from documented commands.
- Each write action has a dry run and a summary report.
- Quality metrics can be compared before and after each batch.

## Phase 8: Consider SQLite

Goal: move beyond wide CSVs when the normalized model stabilizes.

Recommendation:

Keep CSVs for portability, but consider adding `MusicDB.sqlite` as the working database once the schema settles.

Benefits:

- Better joins across recordings, links, playlists, tags, and performance notes.
- Faster filtering.
- Fewer accidental duplicate rows.
- Easier saved views.
- Better audit tables.

Acceptance criteria:

- CSV export remains available.
- SQLite can be rebuilt from source CSVs.
- No data is trapped in a binary-only format.

## Priority Order

1. Rotate exposed credentials.
2. Resolve active-vs-staged source-of-truth differences.
3. Promote `recordings.csv` as the working table.
4. Add quality reports and dry-run workflows.
5. Import/tag priority playlists.
6. Fill BPM/key/performance fields for high-value songs.
7. Verify exact external URLs.
8. Add SQLite only after the table model stabilizes.

## Immediate Next Action

Create a review report comparing:

- `data/processed/Main_Song_Database.csv`
- `data/staging/d_music_legacy_merge/merged_candidate_Main_Song_Database.csv`

The report should identify:

- rows only in the active main DB
- rows only in the staged candidate
- rows with conflicting Spotify IDs
- rows with conflicting album/year/duration
- rows safe to normalize from `Spotify ID` into `Spotify Track ID`

That report should come before any promotion or replacement of the active main database.

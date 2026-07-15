# Reference ID Database

This document defines the separate reference layer for MusicDB.

## Purpose

The main SongDB v2 tables remain the working database. The reference DB is a read-only companion that:

- keeps source inventory in one place
- preserves identifier crosswalks from existing exports
- exposes a stable, web-reachable read model for lookups and review
- separates verified links from search-only discovery links

## Inputs

- `data\source_registry.csv`
- `data\source_metadata_matrix.csv`
- `data\processed\Main_Song_Database.csv`
- `data\exports\codex\youtube_music_takeout_verified.csv`
- `data\exports\codex\youtube_music_takeout_unmatched.csv`
- `data\staging\jules\antigravity_cover_candidates.csv`
- `data\staging\jules\music_antigravity_review.sqlite`
- `SongDB_v2\songs.csv`
- `SongDB_v2\recordings.csv`
- `SongDB_v2\external_links.csv`

## Build Artifact

The reference database is built at:

- `data\staging\jules\reference_ids.sqlite`

The build should be repeatable and derived from the cleaned CSV exports.

## Tables

### `source_registry`

Describes the sources used by MusicDB and their access model.

### `source_metadata_matrix`

Tracks what metadata each primary source can supply and how it should be matched.

### `reference_entities`

One row per title, artist, album, song, or recording entity.

Entity kinds currently emitted:

- `title`
- `artist`
- `album`
- `song`
- `recording`

### `reference_identifiers`

One row per identifier or verified/discovery URL attached to an entity.

### `source_observations`

Raw source-layer facts preserved from the active compatibility CSV and the antigravity review SQLite tables, including provider-specific IDs, verification flags, metadata fields, external-link suggestions, mood/event suggestions, and performance metadata from Spotify, MusicBrainz, iTunes, Discogs, WhoSampled, SecondHandSongs, and MusicDB-canonical columns.

## Population Rules

- Keep internal IDs, source IDs, and URLs separate.
- Do not fabricate missing IDs.
- Do not promote search links to verified links without exact match review.
- Use exact IDs from the cleaned exports whenever possible.
- Preserve source status notes so downstream tools can distinguish verified, search-only, and legacy values.
- Keep separate entity rows for title, artist, album, song, and recording identity layers.
- Preserve source observations for the active compatibility CSV so provider-level metadata can be cross-checked later.

## Web Exposure

The FastAPI app exposes the reference layer as read-only endpoints:

- `/api/reference/sources`
- `/api/reference/matrix`
- `/api/reference/entities`
- `/api/reference/identifiers`
- `/api/reference/source-observations`

These endpoints are meant for reference and review, not editing.

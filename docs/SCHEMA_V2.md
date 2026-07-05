# MusicDB Schema V2

## Overview
MusicDB V2 promotes `recordings.csv` as the primary operational working layer. This document defines the schema and identity rules for the database.

## 1. Recordings (Working Layer)
The `recordings.csv` file is the source of truth for all unique audio captures.

| Field | Description | Requirement |
|-------|-------------|-------------|
| `Recording ID` | Stable hash of Title, Artist, and Version | Required (PK) |
| `Song ID` | Stable hash of Title and Artist | Required (FK) |
| `Title` | The name of the track | Required |
| `Artist` | The primary artist | Required |
| `Version` | Descriptive version (e.g., "Live", "Radio Edit", "Remix") | Optional |
| `Spotify Track ID` | Exact Spotify Track ID | Recommended |
| `MusicBrainz ID` | MusicBrainz Recording ID | Recommended |
| `ISRC` | International Standard Recording Code | Optional |

## 2. External Links
Links to external databases and resources.

| Field | Description |
|-------|-------------|
| `Recording ID` | FK to Recordings |
| `SHS Link` | SecondHandSongs URL |
| `WhoSampled Link` | WhoSampled URL |
| `UG Link` | Ultimate Guitar Tab URL |
| `Video Link` | YouTube/Vimeo Official Video |

## 3. Performance Metadata
Metadata useful for musicians and live performance.

| Field | Description |
|-------|-------------|
| `Recording ID` | FK to Recordings |
| `BPM` | Beats Per Minute |
| `Key` | Musical Key (e.g., "Am", "G#") |
| `Tuning` | Instrument tuning |
| `Capo` | Capo position |
| `Difficulty` | 1-5 scale |
| `Vocal Range` | e.g., "G2-A4" |
| `Instrumentation`| List of instruments |
| `Arrangement` | Notes on the arrangement |

## 4. Tags & Playlists
Categorization for organization and discovery.

| Field | Description |
|-------|-------------|
| `Recording ID` | FK to Recordings |
| `Mood` | e.g., "Melancholic", "Energetic" |
| `Event` | e.g., "Wedding", "Club" |
| `Situation` | e.g., "Driving", "Focus" |
| `Setlist Role` | e.g., "Opener", "Closer" |
| `Energy` | 1-10 scale |
| `Playlists` | Semicolon-separated list of playlist names |

## Identity Rules

### Stable IDs
- **Recording ID**: `hash(normalize(Title) + "|" + normalize(Artist) + "|" + normalize(Version))`
- **Song ID**: `hash(normalize(Title) + "|" + normalize(Artist))`

### Versioning
- **Original**: Version field is empty.
- **Cover**: Same `Song ID` but different `Artist` and `Recording ID`.
- **Remix**: `Version` contains "Remix".
- **Live**: `Version` contains "Live".
- **Edit**: `Version` contains "Edit" or "Radio Edit".

## Compatibility: Main_Song_Database.csv
To maintain compatibility with existing tools, the `rebuild` command will export a flattened CSV with the following mapping:

| Main CSV Field | Source V2 Field |
|----------------|-----------------|
| `Title` | `Title` |
| `Artist` | `Artist` |
| `Version` | `Version` |
| `Spotify ID` | `Spotify Track ID` |
| `MBID` | `MusicBrainz ID` |
| `BPM` | `BPM` |
| `Key` | `Key` |
| `Playlists` | `Playlists` |
| `Notes` | Combined `Arrangement` + `SHS Link` |

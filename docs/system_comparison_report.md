# MusicDB System Comparison

Generated for:

- `D:\Music\MusicDB`
- `C:\codex_work\projects\SongDB`
- `D:\Music\Main_Song_Database`

## Likely Root Cause

There are three overlapping systems because the older `D:\Music\Main_Song_Database` project was later enriched in `C:\codex_work\projects\SongDB`, then copied/merged into `D:\Music\MusicDB`. The best long-term move is to make `D:\Music\MusicDB` the canonical project and treat the other two as source/legacy references.

## Database Comparison

| Location | Role | Main Rows | Main Columns | Notes |
| --- | ---: | ---: | ---: | --- |
| `D:\Music\MusicDB` | Recommended canonical project | 9,672 | 58 | Most comprehensive active main CSV; includes `Spotify ID` plus rich SongDB columns. |
| `C:\codex_work\projects\SongDB` | Codex working source | 9,642 | 57 | Clean project architecture; no legacy verification scripts. |
| `D:\Music\Main_Song_Database` | Legacy source | 9,369 | 21 | Older source with useful verification flags and raw cleaned CSVs. |

## Architecture Comparison

`C:\codex_work\projects\SongDB` has the cleanest architecture:

- `data/processed`
- `data/raw`
- `data/exports`
- `data/staging`
- `scripts`
- `docs`
- `playlists`
- `SongDB_v2`

`D:\Music\MusicDB` now has the same architecture, plus archived legacy source material from `D:\Music\Main_Song_Database`.

`D:\Music\Main_Song_Database` should not remain an active working project. It is best treated as archived input.

## Script Comparison

| Script Area | D MusicDB | C SongDB | D Main Legacy | Recommendation |
| --- | --- | --- | --- | --- |
| Playlist import/audit/merge | Present | Present | Missing | Keep D MusicDB versions. |
| v2 database builder | Present | Present | Missing | Keep D MusicDB version; it now preserves legacy `Spotify ID` fallback. |
| Legacy D merge | Present | Present | Missing | Keep as staging-only merger. |
| Library analysis | Present | Missing | Present | Keep, but modernize later to use `data/processed`. |
| Verification scripts | Present, now sanitized | Missing | Present with hardcoded credentials | Use only the sanitized D MusicDB versions. |
| Old merge script | Present, now safe wrapper | Missing | Missing | Keep wrapper; do not restore old destructive behavior. |

## Connections and Credentials

Active D MusicDB scripts now use environment variables. Legacy scripts in `D:\Music\Main_Song_Database` still contain hardcoded credentials and should not be used.

Credentialed sources:

- Spotify: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`
- Discogs: `DISCOGS_TOKEN`

Non-secret or public sources:

- iTunes Search API
- MusicBrainz API, with `MUSICBRAINZ_USER_AGENT`
- SecondHandSongs search links
- WhoSampled search links
- Ultimate Guitar search links

## Column Comparison

`D:\Music\MusicDB\data\processed\Main_Song_Database.csv` has the richest active main schema:

- all core song fields
- legacy `Spotify ID`
- playlist membership
- rich Spotify import fields
- duplicate merge fields

`SongDB_v2\recordings.csv` is the better long-term working table because it separates recording/version identity from playlist links, external links, and musician metadata.

## Implemented Improvements

- Removed hardcoded credentials from active D MusicDB verification scripts.
- Changed verification scripts to read credentials from environment variables.
- Changed verification scripts to default to dry-run unless `--write` is passed.
- Replaced the old destructive `merge_databases.py` with a staging-only compatibility wrapper.
- Added `.env.example`.
- Added `data/source_registry.csv`.
- Added this comparison report.
- Added external connection documentation.
- Updated the v2 builder so `Spotify ID` can be used as a fallback for `Spotify Track ID`.

## Recommended Next Steps

1. Rotate the Spotify and Discogs credentials exposed in legacy scripts.
2. Review the active 9,672-row MusicDB against the staged 9,648-row conservative merge before deciding which main CSV should be canonical.
3. Continue using `SongDB_v2\recordings.csv` as the rational long-term shape.
4. Gradually verify exact SecondHandSongs, WhoSampled, and Ultimate Guitar URLs rather than guessing them at scale.

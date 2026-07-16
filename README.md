# SongData

Coordination repository for the `D:\Music\MusicDB` music database system.

## Canonical Local System

The active local project is:

`D:\Music\MusicDB`

The active source database is:

`D:\Music\MusicDB\data\processed\Main_Song_Database.csv`

Do not replace the active database wholesale with the staged candidate. The active DB remains the source of truth until a reviewed promotion script and backup are created.

## What This GitHub Repo Is For

Use this repo to coordinate work between Codex, Antigravity, and Jules:

- task ownership
- issue tracking
- schema decisions
- scripts and tests
- documentation
- staged-review summaries
- non-sensitive sample fixtures

## What Should Stay Local Unless Explicitly Approved

- full music database CSVs
- raw exports
- backups
- `.env` files
- API keys, tokens, client secrets, passwords
- large generated artifacts

## Agent Roles

- Codex: integration owner and final promoter into the active DB.
- Antigravity: enrichment worker for tags, performance metadata, and external-link verification.
- Jules: automation, tests, CLI, quality reports, and SQLite prototype.

## Product Goals

The long-term user-facing goals for this project are to:

- import user-approved playlists directly from Spotify, iTunes, Amazon Music, and YouTube Music
- incorporate those playlists into the database as first-class library data
- link songs, artists, and albums to the user’s preferred source platform
- create mood-based, goal-based, event-based, and situation-based playlists
- suggest music the user does not already have in their history
- find cover songs and related versions for songs already in the database
- support creation of the user’s own versions or arrangements of songs they like
- provide links to lyrics and sheet music or tablature
- show simplified keyboard guidance for songs
- show visual pitch or note representations for vocals
- require double verification of song metadata using at least two reputable sources
- clean song metadata for font, symbol, and encoding problems
- retain reference IDs from every source for title, performance, artist, album, and other useful entities
- determine what metadata each primary source provides, including Spotify, iTunes, YouTube Music, cover.info, MusicBrainz, and Discogs
- maintain a cleaned, reliable reference-ID database that can be published as a web-reachable source of truth

Start with `docs/COORDINATION.md` and `docs/WORKSTREAMS.md`.

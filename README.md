# SongDB

Local music database project for organizing songs, versions, playlists, mood/event tags, musician metadata, and external research links.

## Current Layout

- `data/processed/Main_Song_Database.csv` - current source-of-truth CSV imported from the earlier flat database.
- `SongDB_v2/` - structured generated database built from the main CSV.
- `playlists/` - source playlist text files, such as `PLAYLIST - NRG.txt`.
- `scripts/` - import, audit, merge, and v2-build scripts.
- `data/exports/` - generated reports and import summaries.
- `data/source_registry.csv` - source/API registry and credential policy.
- `data/raw/` - place for future unmodified source exports.
- `docs/` - design notes and operating rules.
- `backups/` - timestamped CSV backups from previous data-changing operations.

## Common Commands

Run these from `C:\codex_work\projects\SongDB`.

```powershell
python .\scripts\build_songdb_v2.py
python .\scripts\audit_playlist_duplicates.py --playlist NRG
python .\scripts\add_playlist_to_songdb.py ".\playlists\PLAYLIST - NRG.txt"
python .\scripts\merge_d_music_legacy.py
python .\scripts\verification_pass.py --limit 25
```

Use `merge_safe_playlist_duplicates.py` cautiously. It modifies `data/processed/Main_Song_Database.csv`; make a backup first unless the current workflow already did.

Verification scripts are dry-run by default. Pass `--write` only when you intend to modify the main database.

## Data Rules

- Keep one row per distinct recording/version in `SongDB_v2/recordings.csv`.
- Prefer the first-published album, single, or soundtrack release as the primary album/release.
- Keep greatest-hits, anthology, compilation, deluxe, remaster, and anniversary releases in alternate-release fields.
- Do not merge live versions, remixes, acoustic versions, radio edits, extended versions, demos, instrumentals, or covers unless they are intentionally interchangeable.
- Use `MusicBrainz Recording ID` as the preferred external identifier for a specific recorded version when verified.
- Use `MusicBrainz Work ID` later to group covers and different recordings of the same written composition.
- Treat Spotify IDs as useful but platform-specific; do not use them as the only merge rule.

## External Links

`SongDB_v2` includes generated search links and blank verified-link fields for:

- SecondHandSongs
- WhoSampled
- Ultimate Guitar

For Ultimate Guitar, prefer an official tab. If no official tab exists, use the most popular or highest-rated matching tab.

## Legacy D: Music Merge

`D:\Music\Main_Song_Database` has been treated as a legacy data source, not the active project. Run `scripts/merge_d_music_legacy.py` to build a non-destructive candidate merge in `data/staging/d_music_legacy_merge/`.

The merge script:

- keeps `data/processed/Main_Song_Database.csv` unchanged
- enriches unambiguous rows from the D: database
- appends D-only rows to the candidate file
- skips ambiguous duplicate groups for review
- archives D: raw/processed CSV inputs under `data/raw/d_music_legacy/`

Do not promote D: scripts into active use without review. One legacy script contained hardcoded Spotify credentials and brittle absolute paths.

## Credentials

Active scripts read credentials from environment variables instead of storing secrets in source files.

Expected variables:

- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `DISCOGS_TOKEN`
- `MUSICBRAINZ_USER_AGENT`

See `.env.example`, `data/source_registry.csv`, and `docs/external_connections.md`.

The legacy `D:\Music\Main_Song_Database` scripts still contain exposed credentials. Rotate those service credentials before using related automations again.

## System Comparison

See `docs/system_comparison_report.md` and `docs/implementation_plan.md` for the comparison of:

- `D:\Music\MusicDB`
- `C:\codex_work\projects\SongDB`
- `D:\Music\Main_Song_Database`

See `docs/proposed_improvement_plan.md` for the fuller phased improvement plan.

See `docs/active_vs_staged_review_report.md` for the review comparing the active 9,672-row main database against the staged 9,648-row conservative candidate.

See `AGENT_COORDINATION.md` and `docs/multi_agent_task_split.md` for dividing work between Codex, Antigravity, and Jules.

See `docs/github_coordination.md` for the GitHub PR and issue map in `TexasMD/SongData`.

# MusicDB Data Policy

## Default Position

The full music database lives locally at `D:\Music\MusicDB`.

This GitHub repository is for coordination, documentation, scripts, tests, issue tracking, and small non-sensitive fixtures.

## Do Not Commit Without Explicit Approval

- full `Main_Song_Database.csv`
- full `SongDB_v2` generated CSVs
- raw music-library exports
- backups
- `.env` files
- API keys, tokens, client secrets, passwords
- large generated artifacts

## Safe to Commit

- docs
- coordination files
- scripts without credentials
- tests
- schema definitions
- small fixtures or anonymized samples
- issue and PR templates
- quality-report formats

## Local Staging Convention

Agents should write staged outputs locally:

- Codex: `D:\Music\MusicDB\data\staging\codex`
- Antigravity: `D:\Music\MusicDB\data\staging\antigravity`
- Jules: `D:\Music\MusicDB\data\staging\jules`

Generated reports may go under:

- `D:\Music\MusicDB\data\exports\codex`
- `D:\Music\MusicDB\data\exports\antigravity`
- `D:\Music\MusicDB\data\exports\jules`

## Promotion Rule

Only Codex should promote reviewed staged outputs into the active local database.

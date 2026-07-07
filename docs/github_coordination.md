# GitHub Coordination

GitHub repository:

https://github.com/TexasMD/SongData

## Coordination PR

- Draft PR #2: https://github.com/TexasMD/SongData/pull/2

Purpose:

- Establish GitHub as the coordination layer for MusicDB.
- Add repo README, coordination rules, workstreams, data policy, issue template, and PR template.
- Keep full databases, backups, raw exports, `.env` files, and credentials local unless explicitly approved.

## Initial Issues

- #3 Codex: reconcile active MusicDB with staged conservative candidate  
  https://github.com/TexasMD/SongData/issues/3

- #4 Antigravity: enrich mood/event tags and musician-performance metadata  
  https://github.com/TexasMD/SongData/issues/4

- #5 Antigravity: verify SecondHandSongs, WhoSampled, and Ultimate Guitar links  
  https://github.com/TexasMD/SongData/issues/5

- #6 Jules: add MusicDB CLI, tests, quality reports, and SQLite prototype  
  https://github.com/TexasMD/SongData/issues/6

- #7 Codex/Jules: promote recordings.csv as the MusicDB working layer  
  https://github.com/TexasMD/SongData/issues/7

## Local Remote

The local `D:\Music\MusicDB` git repo has this remote:

```powershell
origin https://github.com/TexasMD/SongData.git
```

## Local Safety Rule

Do not push full local database files to GitHub without explicit approval.

Use GitHub for coordination and code review; keep full data local unless a later data-publishing policy says otherwise.

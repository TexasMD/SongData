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

## Current Coordination Issue

- #58 MusicDB coordination: central task map for SongData  
  https://github.com/TexasMD/SongData/issues/58

Purpose:

- Keep the full MusicDB and song-data task map durable in GitHub.
- Add cover-update work, source-query timestamps, and ongoing coordination items to the repo.

## Split Follow-On Issues

- #61 Add normalized title/artist/album search columns
  https://github.com/TexasMD/SongData/issues/61

- #62 Build the SQLite prototype views for the working layer
  https://github.com/TexasMD/SongData/issues/62

- #63 NRG playlist enrichment: mood/event/performance suggestions
  https://github.com/TexasMD/SongData/issues/63

- #64 Verify exact SecondHandSongs links for covers and originals
  https://github.com/TexasMD/SongData/issues/64

- #65 Verify exact WhoSampled links for samples, covers, and remixes
  https://github.com/TexasMD/SongData/issues/65

- #66 Verify Ultimate Guitar tabs with official-first preference
  https://github.com/TexasMD/SongData/issues/66

- #67 MusicDB CLI: schema validation, dry-run enforcement, and quality report coverage
  https://github.com/TexasMD/SongData/issues/67

- #68 Jules: comprehensive code review and improvement suggestions
  https://github.com/TexasMD/SongData/issues/68

- #72 Jules review: code health audit for src, scripts, and API paths
  https://github.com/TexasMD/SongData/issues/72

- #73 Jules review: test coverage gaps and regression guardrails
  https://github.com/TexasMD/SongData/issues/73

- #74 Jules review: scraping system baseline verification and alternatives
  https://github.com/TexasMD/SongData/issues/74

## Local Remote

The local `D:\Music\MusicDB` git repo has this remote:

```powershell
origin https://github.com/TexasMD/SongData.git
```

## Local Safety Rule

Do not push full local database files to GitHub without explicit approval.

Use GitHub for coordination and code review; keep full data local unless a later data-publishing policy says otherwise.

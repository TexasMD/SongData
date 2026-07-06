# Agent Coordination Rules

## Canonical Project

`D:\Music\MusicDB` is the canonical local project.

The active source database is:

`D:\Music\MusicDB\data\processed\Main_Song_Database.csv`

## Core Rule

Only Codex promotes changes into the active main database.

Antigravity and Jules should produce staged outputs, scripts, tests, docs, or reports. They should not directly overwrite the active CSV.

Antigravity and Jules should not depend on direct private messages. Use GitHub issues or PR comments for agent-to-agent handoffs, following `docs/AGENT_MESSAGE_BRIDGE.md`.

## Required Safety Rules

- Make a backup before any write to `data\processed\Main_Song_Database.csv`.
- Use dry-run mode before write mode.
- Keep API credentials in environment variables.
- Never commit `.env`, API keys, tokens, client secrets, or passwords.
- Keep full CSV databases local unless explicitly approved for GitHub.
- Preserve CSV exports even if SQLite is added later.
- Keep generated search links separate from verified exact links.
- Include source, confidence, and notes for enriched metadata.

## Staging Folders

Use these local output folders:

- Codex: `D:\Music\MusicDB\data\staging\codex`
- Antigravity: `D:\Music\MusicDB\data\staging\antigravity`
- Jules: `D:\Music\MusicDB\data\staging\jules`

Use these local report folders:

- Codex: `D:\Music\MusicDB\data\exports\codex`
- Antigravity: `D:\Music\MusicDB\data\exports\antigravity`
- Jules: `D:\Music\MusicDB\data\exports\jules`

## Promotion Requirements

A staged change can be promoted only when it has:

1. A source file or script that produced it.
2. A summary report with row counts.
3. A backup path.
4. A clear list of changed fields.
5. A representative spot check.
6. A dry-run result before write mode.

## Current Review Artifacts

Before active-vs-staged merge work, read these local files:

- `D:\Music\MusicDB\docs\active_vs_staged_review_report.md`
- `D:\Music\MusicDB\data\exports\active_vs_staged_review\summary.json`
- `D:\Music\MusicDB\data\exports\active_vs_staged_review\spotify_id_normalization_review.csv`
- `D:\Music\MusicDB\data\exports\active_vs_staged_review\field_differences_unambiguous_song_keys.csv`

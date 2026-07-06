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
- agent-to-agent handoffs through GitHub issues and PR comments
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

Start with `docs/COORDINATION.md`, `docs/WORKSTREAMS.md`, and `docs/AGENT_MESSAGE_BRIDGE.md`.

# MusicDB Agent Coordination

## Canonical Project

`D:\Music\MusicDB` is the canonical project.

The active source database is:

`D:\Music\MusicDB\data\processed\Main_Song_Database.csv`

Do not replace this file wholesale with the staged candidate. Treat it as the current source of truth until a reviewed promotion plan says otherwise.

## Core Rule

Only one agent should write to the active main database.

Recommended owner:

- Codex: integration owner and final promoter
- Antigravity: bulk enrichment and research worker
- Jules: automation, tests, CLI, and repo hardening

Antigravity and Jules should write reviewable outputs under `data\staging`, `data\exports`, `scripts`, `tests`, or `docs`. They should not directly overwrite `data\processed\Main_Song_Database.csv`.

## Required Safety Rules

- Make a backup before any write to `data\processed\Main_Song_Database.csv`.
- Use dry-run mode first for any script that modifies data.
- Keep API credentials in environment variables only.
- Do not commit `.env` or literal API keys.
- Preserve CSV exports even if a SQLite database is added later.
- Keep generated search links separate from verified exact links.
- Record sources and confidence for enriched metadata.

## Current Review Artifacts

Use these before making merge decisions:

- `docs\active_vs_staged_review_report.md`
- `data\exports\active_vs_staged_review\summary.json`
- `data\exports\active_vs_staged_review\active_only_rows.csv`
- `data\exports\active_vs_staged_review\staged_only_rows.csv`
- `data\exports\active_vs_staged_review\field_differences_unambiguous_song_keys.csv`
- `data\exports\active_vs_staged_review\spotify_id_normalization_review.csv`

## Promotion Rule

A staged change can be promoted only when it has:

1. A source file or script that produced it.
2. A summary report with row counts.
3. A backup path.
4. A clear list of changed fields.
5. A spot check of representative records.

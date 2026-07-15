---
name: Agent task
description: Coordinate MusicDB work for Codex, Antigravity, or Jules
title: "[Agent] Short task title"
labels: []
assignees: []
---

## Owner

- [ ] Codex
- [ ] Antigravity
- [ ] Jules

## Workstream

- [ ] Canonical system
- [ ] Active vs staged reconciliation
- [ ] Questionable row cleanup and verification
- [ ] Recordings working layer
- [ ] Mood/event tagging
- [ ] Musician-performance metadata
- [ ] External link verification
- [ ] Automation and quality checks
- [ ] SQLite prototype

## Goal

Describe the concrete task and desired outcome.

## Inputs

List local files, reports, or tables used as inputs.

## Outputs

List expected staged files, scripts, docs, tests, or reports.

## Safety

- [ ] Does not overwrite `data/processed/Main_Song_Database.csv`
- [ ] Uses dry-run first if any write is possible
- [ ] Does not include credentials or `.env` contents
- [ ] Includes source/confidence for metadata suggestions
- [ ] Includes row counts or summary report

## Acceptance Criteria

- [ ] Output is reviewable
- [ ] Counts are included where relevant
- [ ] Edge cases or conflicts are documented
- [ ] Codex can promote or reject the staged result

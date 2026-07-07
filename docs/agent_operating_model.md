# MusicDB Agent Operating Model

## Goal

Move routine work away from Codex while keeping Codex as the integration owner for active database changes.

## Authority Model

Only Codex should promote changes into:

`data\processed\Main_Song_Database.csv`

Jules and Antigravity should produce reviewable artifacts, not active database writes.

## Roles

| Agent | Primary Role | Owns | Does Not Own |
| --- | --- | --- | --- |
| Codex | Integrator and final promoter | schema decisions, active DB promotions, backup/write gates, final conflict resolution | bulk enrichment, broad web research, routine CLI hardening |
| Jules | Automation and repo hardening | CLI, tests, quality reports, SQLite rebuild outputs, GitHub PR hygiene | music metadata truth decisions, active DB writes |
| Antigravity | Enrichment and verification | mood/event tags, performance metadata, external link verification, sourced suggestions | active DB writes, schema migrations, unsourced guesses |

## Shared Rules

1. Never overwrite `data\processed\Main_Song_Database.csv` directly.
2. Any write-capable script must default to dry-run.
3. Any active DB write must create a timestamped backup first.
4. Suggestions must include row identifiers, source, confidence, and rationale.
5. Generated search links are not verified exact links.
6. CSV remains the source of truth unless Codex explicitly promotes a new source-of-truth policy.

## Folder Ownership

| Folder | Owner | Notes |
| --- | --- | --- |
| `data\staging\antigravity` | Antigravity | sourced enrichment suggestions only |
| `data\exports\antigravity` | Antigravity | summaries and spot-check reports |
| `data\staging\jules` | Jules | SQLite/build artifacts and safe prototypes |
| `data\exports\jules` | Jules | quality reports and automation summaries |
| `data\staging\codex` | Codex | review decisions and promotion candidates |
| `data\exports\codex` | Codex | promotion reports, action manifests, validation summaries |
| `scripts`, `src`, `tests` | Jules with Codex review | code changes through GitHub PRs |
| `docs` | all agents | coordination notes, decisions, handoffs |

## Handoff Contract

Every agent handoff should include:

- `Status`: `not_started`, `in_progress`, `ready_for_review`, `blocked`, or `done`
- `Owner`: Codex, Jules, or Antigravity
- `Inputs`: exact files used
- `Outputs`: exact files created or modified
- `Counts`: row counts, action counts, and unresolved counts
- `Safety`: whether active DB was modified; backup path if yes
- `Validation`: tests, dry-runs, spot checks, or reason not run
- `Questions`: concrete decisions needed from another agent or user

## Ready For Codex Review

An artifact is ready for Codex review only when it has:

1. A machine-readable CSV/JSON output.
2. A human-readable summary.
3. Source and confidence fields where metadata is proposed.
4. No direct active DB write.
5. A clear recommendation for each row: accept, reject, or needs review.

## Codex Review Pattern

Codex should use the same pattern for all incoming staged work:

1. Read staging output and summary.
2. Produce a decision CSV under `data\staging\codex`.
3. Run dry-run apply script.
4. Create active DB backup.
5. Apply only accepted decisions with `--write`.
6. Rebuild derived outputs.
7. Run tests and quality report.
8. Post GitHub issue update with paths, counts, backup, and validation.

## Work Queue

### Jules

1. Finish GitHub/local repo sync plan.
2. Upgrade `quality-report` to emit JSON and Markdown.
3. Generalize safe apply framework for staged decisions.
4. Add direct unit tests around config and command modules.
5. Expand SQLite PoC with rebuildable views.

### Antigravity

1. Enrich playlist rows, starting with NRG.
2. Suggest mood/event/situation/setlist-role tags.
3. Suggest performance metadata with source and confidence.
4. Verify exact SecondHandSongs, WhoSampled, and Ultimate Guitar links.
5. Mark no-match cases explicitly.

### Codex

1. Keep active DB writes gated and backed up.
2. Review staged outputs.
3. Promote accepted decisions.
4. Maintain coordination docs and issue status.

## Communication Cadence

- Jules posts PRs or issue comments when an automation artifact is ready.
- Antigravity posts CSV paths and summary counts when enrichment batches are ready.
- Codex posts promotion evidence only after validation.
- Use GitHub issues for durable coordination; use local docs for detailed operating rules.

## Suggested Status Update Format

```text
Status:
Owner:
Inputs:
Outputs:
Counts:
Safety:
Validation:
Blocked/Questions:
Next:
```

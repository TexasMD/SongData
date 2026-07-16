# MusicDB Reorganization Implementation Plan

## Likely Root Cause

The project feels disorganized because one repo is currently carrying five different responsibilities without hard boundaries:

1. application source code and tests
2. canonical local music data
3. generated exports, backups, logs, caches, and SQLite databases
4. one-off workbench files in `basket`, `tmp`, and root-level scratch files
5. GitHub coordination material for Codex, Jules, and Antigravity

The target state is not a broad rewrite. The target state is a repo with clear ownership boundaries, one command surface, predictable data/artifact locations, and narrow tests that catch regressions without walking local backup trees.

## Current-State Findings

- Local `main` is 5 commits behind `origin/main` after `git fetch --prune origin`.
- The working tree is dirty across code, docs, tracked CSV data, SQLite data, tests, and generated artifacts.
- GitHub repo: `TexasMD/SongData`, public, default branch `main`.
- Open GitHub PR: `#60 Integrate Parse API for WhoSampled scraping`. It is mergeable but should not be merged until evaluated against the current working scraping baseline.
- Open coordination/review issues include `#58`, `#61` through `#69`, and `#72` through `#74`.
- Existing docs already describe the product direction, but no doc currently governs repo layout, generated artifacts, or cleanup order.
- `.gitignore` ignores `*.csv` and `*.sqlite`, but the repo already tracks CSV and SQLite files. That contradiction makes it unclear which data files are source fixtures versus local generated data.
- `data/backups/pre_refactor_20260705_022521` contains a recursive-looking copy of `data/backups`, with about 1,693 files under that one backup tree. Broad scans and root-level test collection can hit this path.
- `python -m compileall -q src scripts api` succeeds.
- `python scripts\musicdb.py --help` succeeds and shows the current command surface.
- `python -m pytest tests --collect-only -q` collects 66 tests quickly.
- `python -m pytest --collect-only -q` from the repo root timed out after 2 minutes, consistent with test discovery or filesystem traversal crossing generated/local artifact folders.
- `npm run build` in `frontend` succeeds, with a large chunk warning.

## Desired Repo Contract

Use these boundaries as the organizing rule:

- `src/`: reusable Python library code only.
- `src/commands/`: implementation of CLI subcommands.
- `scripts/musicdb.py`: thin CLI dispatcher only.
- `scripts/`: migration or operational entrypoints that are intentionally invoked by the CLI or documented runbooks.
- `api/`: FastAPI app and API-specific wiring.
- `frontend/`: Vite/React app only, with `node_modules`, `dist`, and build metadata ignored.
- `tests/`: tests that use temp roots and never write to active data.
- `SongDB_v2/`: checked-in small or policy-approved canonical derived tables only.
- `data/processed/`: active local database, not blindly pushed.
- `data/staging/<owner>/`: reviewable staged outputs.
- `data/exports/<owner>/`: generated reports and review outputs.
- `data/backups/`: local backups only, ignored and excluded from scans.
- `basket/`: local scratch/workbench only, not part of production workflows.
- `docs/`: durable project, data, API, agent, and operating-model docs.
- `tmp/`: disposable local temp output only.

## Implementation Phases

### Phase 0: Freeze and Preserve the Current State

Goal: make the cleanup reversible before moving files or rewriting code.

Tasks:

1. Create a reorganization branch from the current local state, for example `codex/reorganize-musicdb`.
2. Save a full dirty-tree inventory with:
   - `git status --short --branch`
   - `git diff --stat`
   - `git ls-files -m`
   - `git ls-files --others --exclude-standard`
3. Classify every dirty file into one of these buckets:
   - keep as source/doc/test
   - generated artifact to ignore
   - local data to keep outside Git
   - obsolete scratch file to archive
   - needs manual review before deciding
4. Do not fast-forward local `main` until local dirty changes are classified and either committed, stashed, or archived.

Acceptance:

- No unclassified modified or untracked file remains.
- The plan records exactly which files are safe to delete, ignore, commit, or move.
- Active `data\processed\Main_Song_Database.csv` is not replaced or reformatted as part of this phase.

### Phase 1: Fix Filesystem Hygiene and Tooling Boundaries

Goal: make repo-wide tools safe and fast again.

Tasks:

1. Create a manifest for `data/backups/pre_refactor_20260705_022521`.
2. Move recursive/local backup trees out of the repo or quarantine them under a clearly ignored external path.
3. Add `pytest.ini` or `pyproject.toml` test configuration with explicit `testpaths = tests`.
4. Tighten `.gitignore` so generated/local artifacts are ignored without hiding intentional source fixtures:
   - ignore `data/backups/`
   - ignore `data/exports/`
   - ignore `data/logs/`
   - ignore `tmp/`
   - ignore `frontend/dist/`
   - ignore `frontend/node_modules/`
   - ignore `__pycache__/` and `.pytest_cache/`
   - replace broad `*.csv` / `*.sqlite` rules with path-specific data rules
5. Add a repo-safety test that asserts known heavy/local artifact folders are ignored and that root pytest collection stays inside `tests`.

Acceptance:

- `python -m pytest --collect-only -q` no longer times out.
- `git status --ignored --short` shows generated folders as ignored, not ambiguous untracked work.
- The repo can be scanned without descending into backup recursion.

### Phase 2: Reconcile With GitHub Main and Open PRs

Goal: bring local state and GitHub state back into a single understandable line of history.

Tasks:

1. Rebase or merge the preserved cleanup branch onto `origin/main` after Phase 0 classification.
2. Compare local changes against the 5 newer remote commits now on `origin/main`.
3. Review PR `#60` separately:
   - confirm whether the Parse API dependency is acceptable
   - compare against the current working scraping baseline
   - require tests proving equal or better WhoSampled behavior
   - document rollback if the endpoint fails or becomes unavailable
4. Update `docs/github_coordination.md` after deciding the fate of PR `#60` and issues `#68`, `#69`, `#72`, `#73`, and `#74`.

Acceptance:

- Local branch is based on current `origin/main`.
- PR `#60` has a clear merge, close, or defer recommendation.
- Open GitHub issues map to actual implementation phases instead of duplicate vague review tasks.

### Phase 3: Consolidate the Python Command Architecture

Goal: stop adding one-off scripts when a typed command module should exist.

Tasks:

1. Move command behavior out of `scripts/musicdb.py` and into `src/commands/*`.
2. Keep `scripts/musicdb.py` as an argparse-only dispatcher.
3. Remove production command behavior that writes mock data unless explicitly marked as test-only.
4. Move hardcoded personal paths into config, environment variables, or required CLI arguments.
5. Replace direct imports from `scripts.*` inside production CLI paths with `src.*` imports.
6. Group legacy scripts by status:
   - active command backend
   - migration tool
   - data repair tool
   - deprecated/archive candidate
7. Add command tests for dry-run/write behavior and path safety for every mutating command.

Acceptance:

- Every CLI subcommand has a `src.commands.<name>.run(...)` implementation.
- Every mutating command defaults to dry-run and requires `--write`.
- No production command relies on `data/staging/recordings_mock.csv`.
- No production command defaults to a personal OneDrive path.

### Phase 4: Clarify Data Policy and Tracked Fixtures

Goal: make it obvious what data can be versioned and what must stay local.

Tasks:

1. Create a data classification doc with these classes:
   - active private data
   - checked-in small fixtures
   - checked-in schema/reference examples
   - generated reports
   - staging outputs
   - backups
2. Decide whether the tracked CSVs under `SongDB_v2/` are source artifacts, fixtures, or generated outputs.
3. If `SongDB_v2/` remains tracked, document the exact rebuild command and required validation counts.
4. Move large/local spreadsheets, zips, logs, and exploratory scripts out of `basket/` into ignored local workbench storage unless intentionally promoted.
5. Add fixture-specific naming under `tests/fixtures/` for small checked-in test data.

Acceptance:

- `.gitignore`, README, and tests agree on what data belongs in Git.
- No full backup, raw takeout zip, local credential file, or generated SQLite database is accidentally staged.
- Small checked-in fixtures are named and documented.

### Phase 5: Normalize API and Database Access

Goal: make API/database paths configurable, read-only by default, and testable.

Tasks:

1. Move default SQLite paths into `src.config.MusicDBPaths`.
2. Remove hardcoded absolute paths from `src/db_access.py`.
3. Keep read-only SQLite connections as the default.
4. Preserve parameterized SQL and expand unsafe-query tests to cover `ATTACH`, `PRAGMA`, `DETACH`, `CREATE`, and `REPLACE`.
5. Add tests proving API endpoints can run against temp test databases.
6. Split API route groups if `api/main.py` keeps growing.

Acceptance:

- Tests do not require `D:\Music\MusicDB\data\staging\jules\music_antigravity_review.sqlite`.
- API endpoints work with a temp DB in tests.
- Unsafe SQL coverage matches the current GitHub main security fixes.

### Phase 6: Documentation and GitHub Issue Cleanup

Goal: turn scattered docs into an operating manual.

Tasks:

1. Keep `README.md` short and orienting.
2. Move detailed operational rules into:
   - `docs/OPERATING_MODEL.md`
   - `docs/DATA_POLICY.md`
   - `docs/COMMANDS.md`
   - `docs/RELEASE_AND_PROMOTION.md`
   - `docs/GITHUB_COORDINATION.md`
3. Retire or merge obsolete root-level files:
   - `plan.md`
   - `commit_message.txt`
   - `conflict_resolution.md`
   - `EXPLANATION_FOR_GITHUB_CONFLICTS.md`
   - stale review suggestion docs after their useful items become issues
4. Convert this plan into GitHub issues grouped by phase.
5. Close or update overlapping review issues once the new phase issues exist.

Acceptance:

- The root directory contains only current project entrypoints and evergreen docs.
- GitHub issues reflect the implementation sequence and are not a pile of overlapping review requests.

### Phase 7: Verification Gate

Goal: define when the reorganization is actually done.

Required commands:

```powershell
python -m compileall -q src scripts api
python -m pytest --collect-only -q
python -m pytest tests -q
python scripts\musicdb.py --help
npm run build
git status --short --ignored
```

Required manual checks:

- Active main database row count is unchanged unless a separate approved promotion task changed it.
- `SongDB_v2` rebuild counts match the documented manifest.
- No secrets, zips, full backups, or raw private exports are staged.
- Open PR `#60` is either resolved or explicitly deferred with rationale.

## Recommended First Implementation Slice

Start with Phase 0 and Phase 1 only.

That first slice is small enough to review and high enough leverage to make every later cleanup safer. The first PR should not refactor application logic. It should:

1. add test/path configuration,
2. fix ignore rules,
3. classify the dirty tree,
4. remove or relocate recursive backup artifacts with a manifest,
5. document data/artifact boundaries.

Only after that should the code reorganization begin.

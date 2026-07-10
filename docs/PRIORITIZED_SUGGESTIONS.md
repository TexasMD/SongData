# Prioritized Code Review Suggestions

Based on `CODE_REVIEW_SUGGESTIONS.md` and current project rules (especially memory rules on safety and DB management), here is the review and prioritized execution list:

## Priority 1: Safe SQLite Connections (Suggestion 4)
*   **Relevance:** Critical. System memory explicitly requires: "Always manage SQLite database connections securely using `with contextlib.closing(sqlite3.connect(...)) as conn:` to prevent unclosed connection resource leaks."
*   **Action:** Refactor `src/sqlite_poc.py` to use context managers for DB connections.
*   **Status:** Done (as part of this patch).

## Priority 2: Refactor Testing (Suggestion 6)
*   **Relevance:** High. Current tests rely heavily on slow `subprocess` calls.
*   **Action:** Refactor `tests/test_cli.py` to import and call CLI functions directly using mock `argparse.Namespace` or keyword arguments.
*   **Status:** Pending.

## Priority 3: Path/Environment Management (Suggestion 1)
*   **Relevance:** Medium-High. Hardcoded paths make local testing vs production tricky.
*   **Action:** Centralize path config using environment variables (`MUSICDB_ROOT`) without checking in `.env`.
*   **Status:** Pending.

## Priority 4: Logging Refactor (Suggestion 2)
*   **Relevance:** Medium. `print()` statements are noisy.
*   **Action:** Replace `print` with Python `logging` for the CLI.
*   **Status:** Pending.

## Priority 5: Schema Validation Upgrade (Suggestion 3)
*   **Relevance:** Low. Pydantic is great but a large refactoring dependency for a simple CSV tool.
*   **Status:** Deferred.

## Priority 6: Duplicate Detection Fuzzy Matching (Suggestion 5)
*   **Relevance:** Low (for Jules). This alters business logic and would better belong in Antigravity or Codex data-quality work streams.
*   **Status:** Deferred.

## Priority 7: Modular CLI (Suggestion 7)
*   **Relevance:** Low. Current `scripts/musicdb.py` is fine.
*   **Status:** Deferred.

## Suggestion Inter-Dependencies

Acting upon certain suggestions will directly impact others:

1. **Priority 4 (Logging Refactor) affects Priority 2 (Refactor Testing):**
   Currently, the tests assert on standard output (e.g., `assert "dry-run=True" in result.stdout`). If we switch to using the standard Python `logging` module, the test assertions will break and must be updated to use `pytest`'s `caplog` fixture instead of `capsys`. Therefore, it's highly recommended to do Priority 4 before or simultaneously with Priority 2.

2. **Priority 7 (Modular CLI) affects Priority 2 (Refactor Testing):**
   Refactoring the CLI to be modular involves moving functions out of `scripts/musicdb.py`. If we refactor `test_cli.py` to import directly from `scripts/musicdb.py` (as Priority 2 suggests), we will have to rewrite those imports when Priority 7 is executed. Modularizing the CLI should ideally precede the final test refactoring.

3. **Priority 3 (Path/Environment Management) affects Priority 2 and 7:**
   Centralizing paths via `MUSICDB_ROOT` will change how mock files and output directories are defined in CLI tests, as well as where CLI modules look for configuration.

**Recommended Execution Order:**
To minimize rework, the ideal execution order should be:
1. Path/Environment Management (Priority 3)
2. Modular CLI (Priority 7)
3. Logging Refactor (Priority 4)
4. Refactor Testing (Priority 2) - *Implemented last so tests lock in the finalized structure and logging output.*

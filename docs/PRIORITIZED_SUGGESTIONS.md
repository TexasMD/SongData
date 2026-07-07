# Prioritized Code Review Suggestions

Based on `CODE_REVIEW_SUGGESTIONS.md` and current project rules (especially memory rules on safety and DB management), here is the review and prioritized execution list:

## Priority 1: Safe SQLite Connections (Suggestion 4)
*   **Relevance:** Critical. System memory explicitly requires: "Always manage SQLite database connections securely using `with contextlib.closing(sqlite3.connect(...)) as conn:` to prevent unclosed connection resource leaks."
*   **Action:** Refactor `src/sqlite_poc.py` to use context managers for DB connections.
*   **Status:** Done (as part of this patch).

## Priority 2: Refactor Testing (Suggestion 6)
*   **Relevance:** High. Current tests rely heavily on slow `subprocess` calls.
*   **Action:** Refactor `tests/test_cli.py` to import and call CLI functions directly using mock `argparse.Namespace` or keyword arguments.
*   **Status:** Done.

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

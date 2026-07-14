# Recommended Order of Implementation for Code Improvements

Based on a review of `CODE_REVIEW_SUGGESTIONS.md` and the current state of the codebase, here is the ordered list of suggestions prioritized by their impact on maintainability and correctness.

## 1. Environment & Path Management (Suggestion 1)
* **Status:** Partially Implemented / Pending
* **Reasoning:** `src/config.py` was introduced, but the CLI entrypoint (`scripts/musicdb.py`) still hardcodes paths (e.g., `INPUT_MOCK_FILE`, `DB_PATH`). Centralizing all path usage prevents accidental writes to the wrong environment and makes the tool safer.

## 2. Refactor Testing (Suggestion 6)
* **Status:** Pending
* **Reasoning:** The tests in `tests/test_cli.py` still rely heavily on `subprocess.run` to execute the CLI script. Refactoring tests to directly import and call functions from `scripts/musicdb.py` or `src/commands/` using mocked `argparse.Namespace` objects (or kwargs) will significantly speed up test execution and allow better mocking.

## 3. Standardized Logging (Suggestion 2)
* **Status:** Pending
* **Reasoning:** The CLI relies extensively on `print()` statements for output. Upgrading this to Python's `logging` module will allow better filtering (e.g., hiding verbose dry-run details in non-debug modes) and help in automation scenarios.

## 4. Modular CLI (Suggestion 7)
* **Status:** Partially Implemented / Pending
* **Reasoning:** While some commands have been moved to `src/commands/` (like `build_v2` and `quality_report`), `scripts/musicdb.py` still contains substantial execution logic (e.g., the `rebuild` loop and `verify` logic). Moving all execution logic into `src/commands/` will keep the entrypoint clean.

## 5. Schema Definition & Validation Upgrade (Suggestion 3)
* **Status:** Deferred
* **Reasoning:** Migrating to Pydantic or Marshmallow would be beneficial, but it introduces a large refactoring dependency for a simple tool. This can be deferred until the data model becomes significantly more complex.

## 6. Duplicate Detection Fuzzy Matching (Suggestion 5)
* **Status:** Deferred
* **Reasoning:** While fuzzy matching improves data quality, it alters core business logic and is better suited as part of a separate data-quality workstream (e.g., Antigravity or Codex data tasks) rather than an immediate refactoring chore.

---

### Note on Completed Items
* **Safe SQLite Connections (Suggestion 4):** This is **Done**. `src/sqlite_poc.py` correctly implements context managers using `contextlib.closing(sqlite3.connect(...))` as required by project rules.

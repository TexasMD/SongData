1. **Create `tests/test_utils.py`:** Create a new test file to house tests for `src/utils.py`.
2. **Implement Test Cases for `backup_file`:**
    *   `test_backup_file_success`: Create a temporary file (using pytest's `tmp_path`), mock `src.utils.datetime` to produce a deterministic timestamp, call `backup_file`, verify the returned path, verify the backup file is created, and check that the contents match the original.
    *   `test_backup_file_nonexistent`: Call `backup_file` on a file that does not exist and ensure it returns `""`.
3. **Verify tests:** Run `PYTHONPATH=. pytest tests/test_utils.py` to ensure the new tests pass and catch potential bugs.
4. **Pre-commit checks:** Complete pre commit steps to make sure proper testing, verifications, reviews and reflections are done.
5. **Submit PR:** Create a commit and submit the branch with a descriptive message.

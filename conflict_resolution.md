# Conflict Resolution Log

The merge of `origin/main` into `jules/promote-recordings-layer-17522284852471433934` resulted in several conflicts due to overlapping modifications and structural differences introduced in `main`. Here is a detailed breakdown of the conflicts and their resolutions:

## `scripts/musicdb.py`
**Conflict:** The `main` branch included the original script definitions, while the PR branch added the `rebuild` subcommand and its implementation, along with `import csv`.
**Resolution:** Accepted the PR's implementation, incorporating `import csv`, the `rebuild(args)` function, and the corresponding `rebuild` subcommand parser registration while preserving the core layout and commands from `main`.

## `src/quality.py`
**Conflict:** Both branches made modifications to how missing fields were reported, specifically `SpotifyID`/`Spotify Track ID` and the logic for `musician-performance` fields.
**Resolution:** Reconciled by adopting a hybrid approach to support both `SCHEMA_V2.md` keys and legacy keys (`record.get("Spotify Track ID") or record.get("SpotifyID")`). Adapted the `has_performance` check to incorporate both explicit fields ("Tuning", "Capo", etc.) and dynamic `Musician_` prefixed fields from `main`.

## `src/schema.py`
**Conflict:** The required fields and extended field lists diverged significantly. `main` had basic fields (`Title`, `Artist`), whereas the PR strictly required `Recording ID` and `Song ID` and introduced extended constants (`EXTERNAL_LINK_FIELDS`, `PERFORMANCE_FIELDS`, `TAG_FIELDS`) and value-based validations for `Energy` and `Difficulty`.
**Resolution:** Accepted the PR's expanded schema definition. Kept `Recording ID`, `Song ID`, `Title`, and `Artist` as required. To prevent validation failures on legacy `main` records, added logic to skip the `Recording ID` and `Song ID` requirement if the record appears to be a V1 format. The extended validations for `Energy` and `Difficulty` were preserved.

## `tests/test_cli.py`
**Conflict:** The PR branch introduced new tests for `rebuild` and safety checks (`test_rebuild_dry_run`, `test_rebuild_write`, `test_safety_active_db_not_modified`), which conflicted contextually with the existing tests in `main`.
**Resolution:** Merged both sets of tests, appending the new PR-specific tests beneath the original `test_dry_run_default` and `test_explicit_write`.

## `tests/test_schema.py`
**Conflict:** The basic validation tests in `main` failed against the strict new schema introduced in the PR branch.
**Resolution:** Replaced the `main` branch tests with the updated V2 tests (`test_validate_record_v2`) from the PR, ensuring they validate the new structure, including `Recording ID` and `Song ID`, as well as checking boundary conditions for fields like `Energy`.

# Data patches

This directory holds small, reviewable data patch manifests that are safe to
track in Git. Generated exports and full local database files stay out of Git
unless explicitly promoted.

Scalar update manifests should identify the target file, row key, target column,
old value, new value, source review artifact, approval basis, and backup path.
Append-row manifests set `patch_action` to `append_row`, include `target_file`,
and include the target CSV columns to append.

Verify all tracked patch manifests:

```powershell
python scripts\musicdb.py apply-data-patches
```

Apply them with backups:

```powershell
python scripts\musicdb.py --write apply-data-patches
```

Use `--patch-file` to verify or apply one manifest at a time.

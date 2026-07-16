# Relocated Phase 0/1 Artifacts

The local backup tree was moved out of the Git working tree after writing:

- `backup_manifest_summary.csv`
- `backup_manifest_files.csv`

Moved path:

- From: `D:\Music\MusicDB\data\backups`
- To: `D:\Music\MusicDB_local_artifacts\phase0_1_relocated_artifacts\20260715_022740\data\backups`

Reason:

- `data\backups\pre_refactor_20260705_022521` contained a recursive-looking backup copy with 1,693 files and about 2.56 GB of data.
- Broad repo scans and root-level pytest collection could descend into that tree.

After the move, `D:\Music\MusicDB\data\backups` was recreated as an empty local directory for scripts that expect the path to exist.

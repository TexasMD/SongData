# Remaining dirty tree triage - 2026-07-16

This report separates the local generated/database changes that remain after the NYOV and playlist-membership patch manifests were promoted.

## Summary

| Area | Current rows | HEAD rows | Delta | Impression |
| --- | ---: | ---: | ---: | --- |
| `SongDB_v2/playlist_membership.csv` | 2919 | 223 | 2696 | Append-only YouTube Music Takeout membership import; captured in `data/patches/playlist_membership_youtube_takeout_append_20260716.csv`. |
| `SongDB_v2/recordings.csv` | 9672 | 9704 | -32 | Mixed regeneration: 20 added IDs, 52 removed IDs, plus scalar text cleanups. Promote scalar cleanup only; leave ID churn for a separate rebuild review. |
| `SongDB_v2/songs.csv` | 9529 | 9565 | -36 | Mixed regeneration: 16 added IDs, 52 removed IDs, plus scalar text cleanups. Promote scalar cleanup only; leave ID churn for a separate rebuild review. |
| `SongDB_v2/external_links.csv` | 29016 | 29016 | 0 | Row count unchanged but 63 rows added and 63 removed; likely follows recording-ID regeneration, so do not promote as a clean patch yet. |
| `data/processed/Main_Song_Database.csv` | 9672 | 9672 | 0 | Row count unchanged with 22 row-set replacements; needs keyed review before any promotion. |
| `data/staging/jules/MusicDB.sqlite` | n/a | n/a | n/a | Binary generated database sidecar; keep local unless rebuilt through a documented generation command. |
| `basket/PLAYLIST - Energetic songs2.txt` | n/a | n/a | n/a | New raw basket input; keep local/raw until imported through the NYOV basket process. |
| `basket/PLAYLIST - HIGH ENERGY.txt` | n/a | n/a | n/a | New raw basket input; keep local/raw until imported through the NYOV basket process. |

## Scalar patch manifests created

- `data/patches/recordings_scalar_cleanup_20260716.csv`: 56 field updates across 34 existing rows in `SongDB_v2/recordings.csv`.
  Field counts: `Title`=15, `Canonical Title`=13, `Artist`=12, `Album`=6, `Covering Artist`=6, `Genre`=1, `SecondHandSongs Search URL`=1, `WhoSampled Search URL`=1, `Ultimate Guitar Search URL`=1.
  Skipped 1 update already represented by an existing patch manifest and 0 ID-churn update.
- `data/patches/songs_scalar_cleanup_20260716.csv`: 33 field updates across 33 existing rows in `SongDB_v2/songs.csv`.
  Field counts: `Canonical Title`=13, `Canonical Artist`=12, `Preferred Primary Release`=6, `Genre Family`=2.
  Skipped 0 update already represented by an existing patch manifest and 1 ID-churn update.

## Recommendation

Promote the scalar cleanup manifests through `apply-data-patches`; keep added/removed `songs.csv`, `recordings.csv`, and `external_links.csv` ID churn out of Git until a rebuild review explains why those identities changed. Keep the SQLite sidecar and basket text files local/raw for now.

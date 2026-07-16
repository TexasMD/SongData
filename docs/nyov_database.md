# NYOV Evidence Database

The not-yet-officially-verified database is a staging layer for song evidence
that should not be promoted directly into the official MusicDB tables.

Default seed collection:

- `basket\MyMusicBasefiltered_fixed.csv`
- collection name: `NYOV`

Default output:

- `data\staging\codex\nyov.sqlite`

Build command:

```powershell
python scripts\musicdb.py --write build-nyov-db
```

The first build inventories local basket evidence only. It imports CSV, TXT,
XLSX, DOCX, and ZIP-contained CSV/TXT files into these tables:

- `nyov_source_files`
- `nyov_entities`
- `nyov_source_observations`
- `nyov_identifiers`
- `nyov_verification_attempts`
- `nyov_conflicts`
- `nyov_promotions`

Verification policy:

- `nyov_seed_unverified`: present in the seed file but not externally verified.
- Strong verification should require Spotify plus one other reliable source,
  such as iTunes, MusicBrainz, or YouTube Music.
- Each verified field must keep source, identifier, query timestamp, and raw
  provider response evidence.
- Ambiguous matches remain in `nyov_conflicts` until reviewed.
- Promotion into official MusicDB tables should be a separate reviewed step.

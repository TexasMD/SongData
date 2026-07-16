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

Report command:

```powershell
python scripts\musicdb.py nyov-report
python scripts\musicdb.py --write nyov-report
python scripts\musicdb.py --write nyov-report --batch-step candidate_dual_source_match --batch-limit 100
```

The write-enabled report creates:

- `data\exports\codex\nyov_report\summary.json`
- `data\exports\codex\nyov_report\verification_queue.csv`
- `data\exports\codex\nyov_report\verification_batch_candidate_dual_source_match.csv`
- `data\exports\codex\nyov_report\verification_batch_candidate_dual_source_match_evidence.csv`

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

Verification queue buckets:

- `candidate_dual_source_match`: local evidence already includes Spotify plus
  MusicBrainz, iTunes, or YouTube Music identifiers.
- `candidate_spotify_only`: local evidence includes Spotify identifiers only.
- `candidate_non_spotify_identifier`: local evidence includes identifiers, but
  not Spotify.
- `candidate_local_evidence_only`: more than seed evidence exists, but no
  recognized identifiers have been extracted.
- `seed_only`: the song exists only as an NYOV seed row so far.

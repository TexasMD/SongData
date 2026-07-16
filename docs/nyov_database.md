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

Provider verification command:

```powershell
python scripts\musicdb.py verify-nyov-batch
python scripts\musicdb.py --write verify-nyov-batch --batch-step candidate_dual_source_match --batch-limit 10 --providers itunes,musicbrainz,spotify
python scripts\musicdb.py --write verify-nyov-batch --batch-step candidate_dual_source_match --batch-limit 10 --providers itunes,musicbrainz --strategy tie-breaker --tie-breaker-providers spotify
```

`verify-nyov-batch` records provider lookups in `nyov_verification_attempts`.
It does not promote fields into official MusicDB tables.

Provider strategies:

- `--strategy all`: query every selected provider for every batch row.
- `--strategy tie-breaker`: query primary `--providers` first, then query
  `--tie-breaker-providers` only when the primary results are ambiguous.

Verification summary command:

```powershell
python scripts\musicdb.py nyov-verification-summary
python scripts\musicdb.py --write nyov-verification-summary
```

The write-enabled summary creates:

- `data\exports\codex\nyov_verification_summary\summary.json`
- `data\exports\codex\nyov_verification_summary\entity_summary.csv`

Promotion review command:

```powershell
python scripts\musicdb.py nyov-promotion-review
python scripts\musicdb.py --write nyov-promotion-review
```

The write-enabled review creates:

- `data\exports\codex\nyov_promotion_review\promotion_review_candidates.csv`

This is a review file only. It does not promote data into official MusicDB
tables.

Approved promotion apply command:

```powershell
python scripts\musicdb.py apply-nyov-promotions
python scripts\musicdb.py --write apply-nyov-promotions --input data\exports\codex\nyov_promotion_review\promotion_review_candidates.csv --promoted-by manual_review
```

Only rows with `review_decision` set to `approve` are written into
`nyov_promotions`. This still does not write to official MusicDB tables.

Official patch export command:

```powershell
python scripts\musicdb.py export-nyov-official-patch
python scripts\musicdb.py --write export-nyov-official-patch
```

The write-enabled patch export creates:

- `data\exports\codex\nyov_official_patch\official_patch_candidates.csv`

This is still a review file only. It compares approved NYOV promotions against
the selected official CSV and flags exact matches, ambiguous matches, and rows
that require manual matching.

Official patch apply command:

```powershell
python scripts\musicdb.py apply-nyov-official-patch
python scripts\musicdb.py --write apply-nyov-official-patch
```

The apply command only applies rows with `patch_action=update_existing` and
`official_match_status=matched_exact_title_artist`. It creates a timestamped
backup before writing the selected official CSV.

Clean data patch manifests:

```powershell
python scripts\musicdb.py apply-data-patches
python scripts\musicdb.py --write apply-data-patches
```

Tracked patch manifests live in `data\patches`. They are intentionally small
and reviewable, while generated exports and full local database files remain
local unless explicitly promoted.

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

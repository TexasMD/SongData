# Handoff: NYOV Policy And Rubric Review

Use this prompt with Google Jules or Antigravity.

```text
You are reviewing the MusicDB NYOV verification policy and first-batch
promotion rubric.

Repository: https://github.com/TexasMD/SongData
Branch: codex/reorganize-musicdb
Primary docs:
- docs/nyov_database.md
- docs/nyov_verification_policy_rubric.md
- docs/musicdb_internet_data_source_research.md
- docs/reference_id_database.md
- docs/DATA_POLICY.md

Relevant commands:
- python scripts/musicdb.py --write build-nyov-db
- python scripts/musicdb.py --write nyov-report --batch-step candidate_dual_source_match --batch-limit 100
- python -m pytest tests/test_nyov_db.py tests/test_config_and_commands.py -q

Context:
The NYOV database stages song evidence from local CSV, TXT, XLSX, DOCX, and
ZIP-contained CSV/TXT files under D:\Music\MusicDB\basket. The seed collection
is basket\MyMusicBasefiltered_fixed.csv. The first local build produced 3,173
seed entities, 165,384 observations, and 74,373 identifiers. The current report
classifies 576 seed entities as candidate_dual_source_match, meaning local
evidence includes Spotify plus MusicBrainz, iTunes, or YouTube Music.

Review goal:
Critique whether docs/nyov_verification_policy_rubric.md is strict enough to
prevent bad promotions while still practical for batch verification. Focus on
source tiering, field-level verification, subjective metadata handling, and the
first-batch promotion strategy.

Please produce:
1. A short risk review listing any policy gaps or ambiguous rules.
2. A revised rubric if you recommend changes.
3. A recommended minimum schema for future verification_attempt and promotion
   records.
4. A recommendation on whether YouTube Music video IDs should count as Tier 1
   evidence, and under what conditions.
5. A recommendation on whether SecondHandSongs should be Tier 1 for cover and
   original-song relationship facts.

Constraints:
- Do not commit generated SQLite databases or generated CSV reports.
- Do not rewrite unrelated project architecture.
- Keep changes small and reviewable.
- If you propose code changes, include tests and keep them scoped to NYOV
  verification/promotion behavior.
```

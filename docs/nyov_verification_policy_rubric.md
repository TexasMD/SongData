# NYOV Verification Policy And Rubric

This policy governs promotion from the not-yet-officially-verified collection
into official MusicDB tables. NYOV evidence is useful, but it is not official
until the promoted fields have source-backed verification records.

## Verification Principles

- Preserve evidence before judgment. Store raw provider payloads, source names,
  provider IDs, query timestamps, match scores, and reviewed decisions.
- Verify fields, not just rows. A recording can have reliable title and artist
  data while album, release date, BPM, mood, or danceability remains uncertain.
- Prefer provider identifiers over display text. Display text is mutable; IDs
  are the durable join surface.
- Treat cover/performance relationships separately from recording identity.
  A cover match should not automatically prove that album, release year, or
  performer metadata is correct for the specific recording.
- Require human review for conflicts, low-confidence matches, and subjective
  tags before official promotion.

## Source Tiers

Tier 1 sources are suitable for foundational identity verification:

- Spotify
- Apple/iTunes
- MusicBrainz
- YouTube Music, when linked to a stable video or music entity ID

Tier 2 sources are useful supporting evidence:

- SecondHandSongs
- WhoSampled
- Discogs
- Last.fm
- publisher, label, or artist official pages

Tier 3 sources are leads only:

- playlist names
- scraped search results without stable IDs
- user-edited local CSVs without provenance
- generic web snippets

Relationship Tier 1 sources are suitable for cover/original/sample/remix
relationship verification when the exact work, performance, or relationship page
has been matched:

- SecondHandSongs
- WhoSampled
- MusicBrainz work relationships, when present

These sources should be treated as high-confidence for relationship facts only.
They do not automatically verify foundational recording identity fields such as
album, release date, duration, ISRC, or provider track IDs.

Whenever MusicDB seeks cover-song relationships for a recording, it should query
all three relationship sources: `cover.info`, `SecondHandSongs`, and
`WhoSampled`. One successful source is supporting evidence, not a reason to skip
the other two. MusicBrainz work relationships can be queried as an additional
open-data source, but should not replace the three relationship sources.

## Foundational Field Promotion

Foundational fields include title, artist, album, track number, release date,
duration, ISRC, provider track IDs, and MusicBrainz recording/work IDs.

Promotion rubric:

- `verified_strong`: Spotify plus one Tier 1 source agree on normalized title
  and primary artist, and any promoted provider IDs are captured.
- `verified_supported`: one Tier 1 source plus one Tier 2 source agree, or two
  non-Spotify Tier 1 sources agree.
- `needs_review`: sources disagree, a source match is fuzzy, the same title and
  artist point to multiple recordings, or album/release metadata conflicts.
- `not_verified`: only seed/local evidence exists, no stable source ID exists,
  or the match depends on playlist/context clues alone.

Minimum promotion evidence:

- source name
- source entity type
- source entity ID or URL
- query timestamp in UTC
- normalized comparison fields
- raw response or raw row snapshot
- match decision and reviewer or automation version

## Verification Attempt Schema

Each `nyov_verification_attempts` row should capture the provider lookup used
to judge one NYOV entity:

- `attempt_id`
- `nyov_id`
- `provider`
- `provider_entity_type`
- `provider_entity_id`
- `provider_url`
- `query_title`
- `query_artist`
- `query_album`
- `queried_at`
- `result_json`
- `match_status`
- `match_score`
- `title_match_status`
- `artist_match_status`
- `album_match_status`
- `duration_match_status`
- `isrc_match_status`
- `verifier`
- `verifier_version`
- `notes`

Each `nyov_promotions` row should be field-level, not whole-row-only:

- `promotion_id`
- `nyov_id`
- `target_table`
- `target_key`
- `target_field`
- `promoted_value`
- `verification_level`
- `evidence_json`
- `promoted_at`
- `promoted_by`
- `notes`

## Subjective Field Promotion

Subjective fields include mood, vibe, energy, danceability, situation tags, and
event tags. These should not be promoted with the same confidence language as
foundational identity fields.

Subjective rubric:

- `derived_consensus`: at least two independent data sources or models produce
  materially compatible tags, and the tag fits local listening/use-case review.
- `derived_single_source`: one reputable source or model suggests the tag.
- `manual_curated`: a human intentionally assigned the tag for project use.
- `experimental`: generated or inferred tag awaiting review.

Subjective fields should keep provenance even when manually curated. The
official database can use them for filtering and UI features, but they should
remain separable from factual identity verification.

## First Batch Recommendation

Start with `candidate_dual_source_match` rows from:

```powershell
python scripts\musicdb.py --write nyov-report --batch-step candidate_dual_source_match --batch-limit 100
```

Review the generated file:

- `data\exports\codex\nyov_report\verification_batch_candidate_dual_source_match.csv`

The first batch should prove the promotion workflow on a high-confidence set
before attempting lower-confidence buckets.

## Empty Source Retry Rule

If one cover relationship source returns zero rows while another relationship
source returns 10 or more rows for the same title/artist query, treat the empty
result as suspicious rather than negative evidence. The system should retry that
source once or use its best available alternate path before recording the source
as empty.

After retry:

- if rows are found, keep them with normal source provenance;
- if the source is still empty, record the check as
  `suspicious_empty_after_retry` or equivalent review evidence;
- do not use the empty result to overrule the source that returned substantial
  relationship evidence.

## Open Policy Questions

- Should YouTube Music count as Tier 1 only when a stable music entity exists,
  or is a stable video ID enough?
- Should subjective tag promotion require human review for every tag, or only
  for tags used in public UI filters?
- What confidence threshold should force a conflict row instead of an automated
  promotion candidate?

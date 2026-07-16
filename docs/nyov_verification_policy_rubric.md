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

## Open Policy Questions

- Should YouTube Music count as Tier 1 only when a stable music entity exists,
  or is a stable video ID enough?
- Should SecondHandSongs be Tier 1 for cover/original relationship facts, while
  remaining Tier 2 for recording identity?
- Should subjective tag promotion require human review for every tag, or only
  for tags used in public UI filters?
- What confidence threshold should force a conflict row instead of an automated
  promotion candidate?

# MusicDB Internet Data Source Research

Generated: 2026-07-06

## Verdict

The best path is not one giant source. MusicDB should combine:

1. canonical open metadata sources for identity and release facts,
2. audio-feature datasets for BPM/key/mood candidates,
3. tag/listening datasets for mood and situational tags,
4. specialist sources for covers, samples, and tabs,
5. strict staging and confidence rules before promotion.

No source should write directly to `data\processed\Main_Song_Database.csv`.

## Highest-Value Sources

### MusicBrainz

Use for:

- artist, release, recording, work IDs
- ISRCs
- recording/work relationships
- cover/original relationships when encoded
- canonical release/release-group structure

Access:

- database dumps
- web service API

Fit:

- Best canonical backbone.
- Strong match key for other open datasets.

Links:

- https://musicbrainz.org/doc/MusicBrainz_Database/Download
- https://musicbrainz.org/doc/MusicBrainz_API

### ListenBrainz

Use for:

- open listening data
- popularity/listening context
- MusicBrainz-linked user behavior
- possible playlist/tag recommendation context

Access:

- public data dumps
- API

Fit:

- Good for popularity and context, not exact song facts.

Links:

- https://listenbrainz.org/data/
- https://listenbrainz.readthedocs.io/

### AcousticBrainz / Essentia

Use for:

- BPM
- key
- danceability/energy-style features
- acoustic descriptors
- mood/genre candidates

Access:

- historical AcousticBrainz dumps
- local Essentia feature extraction where audio files are available

Fit:

- High-value for BPM/key/mood, but AcousticBrainz is historical and may be incomplete.
- Treat as candidate values with source and confidence.

Links:

- https://acousticbrainz.org/
- https://essentia.upf.edu/

### Discogs

Use for:

- releases
- masters
- labels
- genres/styles
- release dates
- country/format details

Access:

- API
- data dumps

Fit:

- Strong release metadata complement to MusicBrainz.
- Best used for album/release normalization, not mood.

Links:

- https://www.discogs.com/developers
- https://data.discogs.com/

### Wikidata

Use for:

- crosswalk IDs
- MusicBrainz IDs
- Discogs IDs
- genre/person/work facts
- Wikipedia-linked context

Access:

- SPARQL endpoint
- dumps

Fit:

- Good ID bridge and fact-checking layer.

Links:

- https://query.wikidata.org/
- https://www.wikidata.org/wiki/Wikidata:Data_access

### TheAudioDB

Use for:

- artist/album/track metadata
- videos
- fan-focused metadata
- MusicBrainz-linked lookups

Access:

- API

Fit:

- Useful enrichment source, but must be staged and verified.

Links:

- https://www.theaudiodb.com/api_guide.php

## Audio Feature And Tag Datasets

### Million Song Dataset

Use for:

- Echo Nest-era audio analysis
- tempo/key/time signature candidates
- Last.fm tag joins

Fit:

- Valuable if matched by artist/title/track ID.
- Older catalog coverage is good; modern tracks are weaker.

Links:

- http://millionsongdataset.com/
- http://millionsongdataset.com/pages/getting-dataset/

### Last.fm Datasets / LFM-1b

Use for:

- user tags
- listening behavior
- artist/track popularity context

Fit:

- Good for candidate tags, but raw tags must be mapped into MusicDB controlled vocabulary.
- Do not directly promote tags like `90s`, `female vocalists`, or `seen live` into mood/event fields.

Links:

- http://millionsongdataset.com/lastfm/
- http://www.cp.jku.at/datasets/LFM-1b/

### Music4All

Use for:

- Spotify-linked metadata
- tags
- audio features
- lyrics-derived and genre/mood metadata depending on subset

Fit:

- Potentially high value for BPM/key/tag enrichment if licensing and IDs fit.
- Stage only; validate against Spotify/MusicBrainz IDs.

Links:

- https://sites.google.com/view/contact4music4all
- https://github.com/ilaria-manco/music4all

### Kaggle / Hugging Face / Zenodo Spotify Datasets

Use for:

- historical Spotify audio features
- popularity
- genre classifications
- playlist-derived labels

Fit:

- Useful as candidate data only.
- Must verify license, source provenance, and whether track IDs still resolve.
- Avoid relying on undocumented scraped fields.

Search targets:

- Kaggle: Spotify tracks/audio features datasets
- Hugging Face datasets: music metadata/audio features
- Zenodo: MIR/music metadata datasets

## Covers, Samples, And Version Relationships

### SecondHandSongs

Use for:

- originals
- covers
- versions
- performance/release relationships

Fit:

- Excellent target for cover/original data.
- Use API or permitted access only.

Links:

- https://secondhandsongs.com/page/API

### WhoSampled

Use for:

- samples
- covers
- remixes

Fit:

- Very valuable but access/licensing are restrictive.
- Treat as manual verification unless an approved API/data route exists.

Links:

- https://www.whosampled.com/

### MusicBrainz Work Relationships

Use for:

- original composition grouping
- cover/performance relationships when present

Fit:

- Safer open alternative for at least some cover/version relationships.

Links:

- https://musicbrainz.org/relationships

## Tabs, Chords, And Performance Data

### Songsterr

Use for:

- guitar/bass/drum tab availability
- arrangement clues

Fit:

- Better API posture than scraping random tab sites.
- Use for link discovery and review.

Links:

- https://www.songsterr.com/a/wa/api/

### Ultimate Guitar

Use for:

- official/best tab verification

Fit:

- Useful to verify manually.
- Do not scrape aggressively or assume search result links are verified.

Links:

- https://www.ultimate-guitar.com/

### Chord / Tab Research Datasets

Use for:

- chord progressions
- guitar difficulty heuristics
- arrangement metadata

Fit:

- Useful if licensed and mapped to recordings.
- Keep separate from exact tab URLs.

Search targets:

- Chordonomicon
- guitar tabs dataset
- chord progression dataset

## Live / Setlist Context

### setlist.fm

Use for:

- songs commonly performed live
- opener/closer/encore/setlist-role hints

Fit:

- Useful for setlist-role candidate tags, not recording facts.

Links:

- https://api.setlist.fm/docs/

## Sources To Treat Carefully

- AllMusic: excellent editorial metadata, but no general public data export.
- Rate Your Music: useful human genre consensus, but no official public API for bulk import.
- WhoSampled: high value, but access constraints.
- Ultimate Guitar: high value for tabs, but verify manually and respect terms.
- Random GitHub/Kaggle Spotify dumps: inspect licensing and provenance first.

## Recommended Import Strategy

### Phase 1: Build Source Registry

Create `data\staging\codex\source_registry_candidates.csv` with:

- source name
- URL
- data types
- access method
- license/terms
- allowed use
- match keys
- confidence default
- review owner

### Phase 2: ID Crosswalk

Prioritize sources that provide:

- MusicBrainz Recording ID
- MusicBrainz Work ID
- ISRC
- Spotify Track ID
- Discogs release/master IDs

### Phase 3: Candidate Tables

Do not write directly to canonical fields. Create source-observation style tables:

- `source_observations.csv`
- `bpm_key_candidates.csv`
- `tag_candidates.csv`
- `external_link_candidates.csv`
- `cover_relationship_candidates.csv`

### Phase 4: Confidence Rules

Suggested defaults:

- High: exact API match by MBID/ISRC/Spotify ID from official/open source
- Medium: exact artist/title/release match from reputable source
- Low: search result, fuzzy match, generative guess, community tag

### Phase 5: Promotion

Promote only when:

- exact match key is recorded
- source URL is recorded
- confidence is Medium or High
- Codex/user review accepts the candidate
- backup and dry-run apply script exist

## Best Immediate Work Packets

### Jules

1. Build a source registry CSV.
2. Add importers that write source-observation tables only.
3. Add quality reports showing missing fields by source availability.
4. Add SQLite views for source candidates and confidence.

### Antigravity

1. Investigate SecondHandSongs API route for cover/original data.
2. Investigate MusicBrainz work relationship coverage for existing recordings.
3. Investigate Music4All/Million Song/Last.fm datasets for BPM/key/tag joins.
4. Verify if Songsterr can provide safe tab-link candidates.

### Codex

1. Define promotion rules.
2. Review source registry.
3. Build accepted-candidate apply scripts with backups.


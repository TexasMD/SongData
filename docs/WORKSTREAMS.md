# MusicDB Workstreams

## Workstream 1: Canonical System

Owner: Codex

Goal: keep `D:\Music\MusicDB` as the canonical system and maintain documentation, backups, and final promotion control.

Deliverables:

- updated README and coordination docs
- backup manifest for promoted writes
- final promotion notes

## Workstream 2: Active vs Staged Reconciliation

Owner: Codex

Goal: keep the active 9,672-row DB as source of truth while selectively applying useful staged metadata and provenance.

Initial tasks:

- normalize safe `Spotify ID` values into `Spotify Track ID`
- preserve staged provenance columns
- review active-only and staged-only row signatures
- review the 82 Spotify ID conflicts in active
- produce a patch candidate and summary

## Workstream 3: Recordings as Working Layer

Owner: Codex with Jules support

Goal: promote `SongDB_v2\recordings.csv` as the operational table without breaking CSV compatibility.

Deliverables:

- schema document
- validation rules
- rebuild command
- compatibility notes for `Main_Song_Database.csv`

## Workstream 4: Mood, Event, and Playlist Tagging

Owner: Antigravity

Goal: create staged tag suggestions for mood, event, situation, setlist role, and crowd energy.

Output:

`data\staging\antigravity\mood_event_tag_suggestions.csv`

Required columns:

- `Recording ID`
- `Title`
- `Artist`
- `Suggested Field`
- `Suggested Value`
- `Confidence`
- `Rationale`
- `Source`

## Workstream 5: Musician-Performance Metadata

Owner: Antigravity

Goal: fill key, BPM, tuning, capo, difficulty, vocal range, instrumentation, and arrangement notes.

Output:

`data\staging\antigravity\performance_metadata_suggestions.csv`

Required columns:

- `Recording ID`
- `Title`
- `Artist`
- `Field`
- `Suggested Value`
- `Instrument`
- `Confidence`
- `Source URL`
- `Notes`

## Workstream 6: External Link Verification

Owner: Antigravity

Goal: verify exact SecondHandSongs, WhoSampled, and Ultimate Guitar links.

Output:

`data\staging\antigravity\external_link_verification.csv`

Allowed statuses:

- `verified_exact`
- `official_tab_verified`
- `best_tab_verified`
- `no_good_match`
- `needs_review`

## Workstream 7: Automation and Quality Checks

Owner: Jules

Goal: make MusicDB updates repeatable and testable.

Deliverables:

- `scripts\musicdb.py`
- `tests\`
- schema validation
- quality reports
- dry-run enforcement

## Workstream 8: SQLite Prototype

Owner: Jules with Codex review

Goal: evaluate SQLite while preserving CSV export.

Deliverables:

- `data\staging\jules\MusicDB.sqlite`
- export script back to CSV
- SQLite prototype notes

## Integration Cadence

1. Each agent writes staged outputs.
2. Codex reviews staged outputs.
3. Codex creates a promotion candidate.
4. A backup is made.
5. A dry-run summary is generated.
6. Codex promotes to the active DB only after review.

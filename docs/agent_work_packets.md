# Current Agent Work Packets

## Jules Work Packet: Automation And Repo Hardening

```text
Use D:\Music\MusicDB as the canonical workspace. Do not modify data\processed\Main_Song_Database.csv directly.

Your role is automation and repo hardening.

Read:
- AGENT_COORDINATION.md
- docs\agent_operating_model.md
- docs\proposed_improvement_plan.md

Tasks:
1. Reconcile the local canonical scripts/src layout with GitHub without committing full database CSVs or backups.
2. Upgrade `python scripts\musicdb.py quality-report` so it writes:
   - data\exports\jules\quality_report.json
   - data\exports\jules\quality_report.md
3. Include these sections:
   - row counts
   - missing Spotify and MusicBrainz identifiers
   - missing BPM and key
   - duplicate/version review groups
   - pending Antigravity suggestions
   - external-link verification status
4. Keep the CLI dry-run by default.
5. Add direct unit tests for command functions and config/path handling.
6. Expand the SQLite PoC only as a rebuildable output; CSV remains source of truth.

Write to:
- scripts
- src
- tests
- docs
- data\exports\jules
- data\staging\jules

Do not write to:
- data\processed\Main_Song_Database.csv
- data\backups
- .env or credential files

When ready, post a GitHub issue update using:

Status:
Owner:
Inputs:
Outputs:
Counts:
Safety:
Validation:
Blocked/Questions:
Next:
```

## Antigravity Work Packet: Mood, Event, And Performance Metadata

```text
Use D:\Music\MusicDB as the canonical workspace. Do not modify data\processed\Main_Song_Database.csv directly.

Your role is sourced metadata enrichment.

Read:
- AGENT_COORDINATION.md
- docs\agent_operating_model.md
- SongDB_v2\tag_options.csv
- SongDB_v2\recordings.csv
- SongDB_v2\playlist_membership.csv

Task:
Start with playlist rows, especially NRG. Create sourced suggestions for mood, event, situation, setlist role, crowd energy, and performance metadata.

Output:
data\staging\antigravity\mood_event_tag_suggestions.csv
data\staging\antigravity\performance_metadata_suggestions.csv
data\exports\antigravity\enrichment_summary.md

Required fields for tag suggestions:
- Recording ID
- Title
- Artist
- Suggested Field
- Suggested Value
- Confidence
- Rationale
- Source

Required fields for performance suggestions:
- Recording ID
- Title
- Artist
- Field
- Suggested Value
- Instrument
- Confidence
- Source URL
- Notes

Rules:
- Do not guess exact BPM/key/tuning without marking confidence.
- Prefer controlled vocabulary from SongDB_v2\tag_options.csv.
- Propose new vocabulary separately.
- Codex will review and promote accepted suggestions.
```

## Antigravity Work Packet: External Link Verification

```text
Use D:\Music\MusicDB as the canonical workspace. Do not modify data\processed\Main_Song_Database.csv directly.

Your role is exact external link verification.

Read:
- AGENT_COORDINATION.md
- docs\agent_operating_model.md
- SongDB_v2\recordings.csv
- SongDB_v2\external_links.csv

Task:
Verify exact SecondHandSongs, WhoSampled, and Ultimate Guitar links. Keep generated search links separate from verified exact links.

Output:
data\staging\antigravity\external_link_verification.csv
data\exports\antigravity\external_link_verification_summary.md

Required fields:
- Recording ID
- Title
- Artist
- Site
- Search URL
- Verified URL
- Link Status
- Match Type
- Confidence
- Last Checked
- Notes

Allowed statuses:
- verified_exact
- official_tab_verified
- best_tab_verified
- no_good_match
- needs_review

Rules:
- If no exact page exists, mark no_good_match or needs_review.
- Do not promote search URLs as verified URLs.
- Include enough notes for Codex to review quickly.
```

## Codex/Jules Work Packet: Cover Update Flow And Source Query Tracking

```text
Use D:\Music\MusicDB as the canonical workspace. Keep the active main CSV local and do not overwrite it wholesale.

Track this work in GitHub issue #58 in TexasMD/SongData.

Goal:
Add an `Update Covers` right-click action in the UI, query WhoSampled, SecondHandSongs, and cover.info, and persist when each source was last checked.

Outputs:
- staged cover relationship candidates
- source query tracking table/CSV
- backend endpoint and scraper modules
- UI menu action for selected recordings

Rules:
- Preserve source/query timestamps per recording and per source.
- Keep parsing layout-aware and source-specific.
- Prefer exact connected pages over generic search snippets where possible.
- Do not overwrite the active main database directly.
```


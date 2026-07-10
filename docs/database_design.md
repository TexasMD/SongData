# SongDB Design Notes

## Main Goal

The database should support two related workflows:

1. Quickly gather music for a mood, setting, crowd, or event.
2. Prepare to play songs on guitar, bass, drums, or vocals.

## Recommended Layers

### Songs

One row per generated song identity. This is useful for grouping obvious title/artist duplicates, but it is not enough to group covers. MusicBrainz Work IDs should eventually become the reliable grouping key for covers and compositions.

### Recordings

One row per specific recording or version. This is the best operational layer for playlists, setlists, tabs, key, BPM, instrumentation, and external links.

### External Links

Keep search links separate from verified exact links. A generated search URL is useful, but it is not the same as a confirmed SecondHandSongs, WhoSampled, or Ultimate Guitar match.

### Source Query Tracking

Track when a source was last queried, not just whether a link exists. The cover pipeline now stages `cover_relationship_candidates.csv` plus `source_query_checks.csv` so each song can retain a `last_checked_at` timestamp for sources such as WhoSampled, SecondHandSongs, and MusicBrainz.

### Playlist Membership

Playlist membership should be a table, not duplicated rows. A song can appear in many playlists, and a playlist can contain many songs.

## Mood and Event Tagging

Use controlled tag values whenever possible. Free text is useful for notes, but core filter fields should stay consistent.

Recommended tag categories:

- `Mood Tags`: dark, bright, melancholy, aggressive, romantic, dreamy, anthemic.
- `Event Tags`: road_trip, workout, dance_party, wedding, dinner, halloween, bar_band.
- `Setlist Role`: opener, closer, encore, breather, transition, peak_energy.
- `Crowd Energy`: low, medium, high, peak.

## Musician Metadata

Useful performance fields:

- `BPM`
- `Key`
- `Scale`
- `Time Signature`
- `Tuning`
- `Capo`
- `Guitar Difficulty`
- `Bass Difficulty`
- `Drum Difficulty`
- `Vocal Range`
- `Instrumentation`
- `Main Riff/Hook`
- `Solo`
- `Arrangement Notes`
- `Ultimate Guitar Official Tab URL`
- `Ultimate Guitar Best Tab URL`

## Release Preference Rule

If the same exact recording appears on both an original album and a greatest-hits-style release, keep the original album, single, or soundtrack as the primary release and store the greatest-hits-style reference as an alternate release.

Do not apply this rule to genuinely different versions.

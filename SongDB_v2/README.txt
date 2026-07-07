SongDB v2
Generated: 2026-07-04T19:00:46.020702+00:00

This folder is a new structured database built from:
D:\Music\MusicDB\data\processed\Main_Song_Database.csv

The original Main_Song_Database.csv was not modified.

Files
- songs.csv: one row per generated song identity.
- recordings.csv: one row per specific recording/version imported from the main database.
- external_links.csv: one row per external service link option per recording.
- playlist_membership.csv: normalized playlist membership.
- tag_options.csv: starter controlled vocabulary for mood, event, difficulty, and link-status fields.
- manifest.json: generation counts and policy notes.

Identifier rules
- Recording ID is the working row-level identifier for a specific version/recording.
- Song ID groups generated song identities by normalized title and artist.
- MusicBrainz Recording ID should become the preferred external identifier when verified.
- MusicBrainz Work ID should be added later to group covers and different recordings of the same written composition.

Release rules
- Prefer the first-published album/single/soundtrack as the primary Album/Preferred Primary Release.
- Put greatest-hits, deluxe, compilation, anniversary, and remaster references in Alternate Albums.
- Do not merge remixes, live versions, acoustic versions, radio edits, covers, or extended mixes unless they are intentionally interchangeable for your use.

External link rules
- SecondHandSongs Search URL is generated for every recording.
- WhoSampled Search URL is generated for every recording.
- Ultimate Guitar Search URL is generated for every recording.
- Verified URL fields are intentionally blank until an exact page has been checked.
- For Ultimate Guitar, prefer Official tabs. If no Official tab exists, use the most popular/highest-rated matching tab.

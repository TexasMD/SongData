# MusicDB Implementation Plan

## Completed Now

1. Compared the three project roots.
2. Identified `D:\Music\MusicDB` as the best canonical location.
3. Preserved the active MusicDB main CSV without overwriting it.
4. Hardened credential handling in active scripts.
5. Added source/connection documentation.
6. Added a source registry.
7. Updated the v2 builder to preserve legacy Spotify IDs.
8. Regenerated `SongDB_v2` from the active MusicDB main database.

## Phase 2

1. Decide whether the active 9,672-row main CSV or the conservative 9,648-row staged candidate should be the official source of truth.
2. Create a review report for rows present in the 9,672-row active DB but not in the conservative candidate.
3. Normalize `Spotify ID` into `Spotify Track ID` where safe.
4. Add stable internal IDs to the main processed database, or fully promote `SongDB_v2` as the operational database.

## Phase 3

1. Add exact verified SecondHandSongs URLs.
2. Add exact verified WhoSampled URLs.
3. Add exact Ultimate Guitar official/best tab URLs.
4. Fill musician-performance fields: key, BPM, tuning, capo, difficulty, instrumentation, and arrangement notes.
5. Build playlist/mood/event views from the normalized v2 tables.

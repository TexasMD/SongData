1. **Create `tests/test_utils.py`:** Create a new test file to house tests for `src/utils.py`.
2. **Implement Test Cases for `backup_file`:**
    *   `test_backup_file_success`: Create a temporary file (using pytest's `tmp_path`), mock `src.utils.datetime` to produce a deterministic timestamp, call `backup_file`, verify the returned path, verify the backup file is created, and check that the contents match the original.
    *   `test_backup_file_nonexistent`: Call `backup_file` on a file that does not exist and ensure it returns `""`.
3. **Verify tests:** Run `PYTHONPATH=. pytest tests/test_utils.py` to ensure the new tests pass and catch potential bugs.
4. **Pre-commit checks:** Complete pre commit steps to make sure proper testing, verifications, reviews and reflections are done.
5. **Submit PR:** Create a commit and submit the branch with a descriptive message.

## Product Goals

Longer-term user-facing goals for the MusicDB system:

- import user-approved playlists directly from Spotify, iTunes, Amazon Music, and YouTube Music
- incorporate those playlists into the database
- link songs, artists, and albums to the user’s preferred media source platform
- create mood-based, goal-based, event-based, and situation-based playlists
- suggest music that the user does not already have in their history
- find cover songs and related versions for music in the database
- support user-created versions or arrangements of songs
- provide links to lyrics and sheet music or tablature
- show simplified keyboard guidance for songs
- show visual pitch or note representations for vocals
- require double verification of song metadata using at least two reputable sources
- clean song metadata for font, symbol, and encoding problems
- retain reference IDs from every source for title, performance, artist, album, and other useful entities
- determine what metadata each primary source provides, including Spotify, iTunes, YouTube Music, cover.info, MusicBrainz, and Discogs
- maintain a cleaned, reliable reference-ID database that can be published as a web-reachable source of truth

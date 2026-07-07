import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus


PROJECT_DIR = Path(__file__).resolve().parents[1]
SOURCE_CSV = PROJECT_DIR / "data" / "processed" / "Main_Song_Database.csv"
OUT_DIR = PROJECT_DIR / "SongDB_v2"


VERSION_PATTERNS = [
    r"\blive\b",
    r"\bremaster(?:ed)?\b",
    r"\bremix\b",
    r"\bradio edit\b",
    r"\bsingle version\b",
    r"\balbum version\b",
    r"\bextended\b",
    r"\bacoustic\b",
    r"\binstrumental\b",
    r"\bdemo\b",
    r"\bcover\b",
    r"\bkaraoke\b",
    r"\b8d audio\b",
]


def clean(value):
    return (value or "").strip()


def normalize(value):
    value = clean(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def compact_id(prefix, *parts):
    raw = "\u241f".join(clean(part) for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}{digest}"


def first_nonblank(row, *columns):
    for col in columns:
        value = clean(row.get(col))
        if value:
            return value
    return ""


def semicolon_join(values):
    seen = set()
    result = []
    for value in values:
        value = clean(value)
        if not value:
            continue
        key = value.lower()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return "; ".join(result)


def infer_version(title, album):
    haystack = f"{title} {album}".lower()
    found = []
    for pattern in VERSION_PATTERNS:
        match = re.search(pattern, haystack)
        if match:
            found.append(match.group(0))
    return semicolon_join(found) or "studio/original unless noted"


def search_query(title, artist):
    return quote_plus(f"{title} {artist}".strip())


def google_site_search(domain, title, artist):
    return "https://www.google.com/search?q=" + quote_plus(
        f"site:{domain} {title} {artist}".strip()
    )


def secondhandsongs_search(title, artist):
    return google_site_search("secondhandsongs.com", title, artist)


def whosampled_search(title, artist):
    return google_site_search("whosampled.com", title, artist)


def ultimate_guitar_search(title, artist):
    return "https://www.ultimate-guitar.com/search.php?search_type=title&value=" + search_query(
        title, artist
    )


def split_playlists(value):
    value = clean(value)
    if not value:
        return []
    parts = re.split(r"\s*;\s*|\s*,\s*", value)
    return [part for part in (clean(part) for part in parts) if part]


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    with SOURCE_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        source_rows = list(csv.DictReader(f))

    songs_by_id = {}
    recordings = []
    external_links = []
    playlist_membership = []

    for index, row in enumerate(source_rows, start=2):
        title = first_nonblank(row, "Base Title", "Title")
        display_title = first_nonblank(row, "Title", "Base Title")
        artist = clean(row.get("Artist"))
        album = clean(row.get("Album"))
        spotify_track_id = first_nonblank(row, "Spotify Track ID", "Spotify ID", "Legacy D Music Spotify ID")
        song_id = compact_id("S", normalize(title), normalize(artist))
        recording_id = compact_id(
            "R",
            normalize(display_title),
            normalize(artist),
            normalize(album),
            clean(row.get("Duration")),
            spotify_track_id,
            str(index),
        )
        version = infer_version(display_title, album)
        bpm = first_nonblank(row, "BPM", "Spotify BPM")
        key = first_nonblank(row, "Spotify Key Full", "Spotify Key")
        mood_tags = semicolon_join(
            [
                clean(row.get("Vibe")),
                clean(row.get("Spotify Vibe")),
                clean(row.get("Spotify Energy Level")),
            ]
        )

        if song_id not in songs_by_id:
            songs_by_id[song_id] = {
                "Song ID": song_id,
                "Canonical Title": title,
                "Canonical Artist": artist,
                "MusicBrainz Work ID": "",
                "Primary Recording ID": recording_id,
                "Preferred Primary Release": album,
                "First Published Year": clean(row.get("Year")),
                "Genre Family": first_nonblank(row, "Genre", "Spotify Genre"),
                "Default Mood Tags": mood_tags,
                "Default Event Tags": "",
                "Default Situation Tags": "",
                "Notes": "Generated from Main_Song_Database.csv; verify Work ID before grouping covers or alternate artists.",
            }

        recording = {
            "Recording ID": recording_id,
            "Song ID": song_id,
            "Main DB CSV Line": index,
            "Title": display_title,
            "Canonical Title": title,
            "Version": version,
            "Artist": artist,
            "Original Artist": first_nonblank(row, "Original Artist", "Orig Artist"),
            "Covering Artist": clean(row.get("Covering Artist")),
            "Cover Song": clean(row.get("Cover Song")),
            "Album": album,
            "Alternate Albums": clean(row.get("Alternate Albums")),
            "Release Year": clean(row.get("Year")),
            "Duration": clean(row.get("Duration")),
            "Duration ms": clean(row.get("Spotify Duration (ms)")),
            "Genre": first_nonblank(row, "Genre", "Spotify Genre"),
            "Genre Detail": first_nonblank(row, "Spotify Genre Detail", "Spotify LastFM Tags"),
            "BPM": bpm,
            "BPM Source": "Spotify/manual" if bpm else "",
            "Key": key,
            "Key Source": "Spotify/manual" if key else "",
            "Scale": clean(row.get("Spotify Scale")),
            "Time Signature": "",
            "Tuning": "",
            "Capo": "",
            "Guitar Difficulty": "",
            "Bass Difficulty": "",
            "Drum Difficulty": "",
            "Vocal Range": "",
            "Instrumentation": "",
            "Main Riff/Hook": "",
            "Solo": "",
            "Arrangement Notes": "",
            "Mood Tags": mood_tags,
            "Event Tags": "",
            "Situation Tags": "",
            "Setlist Role": "",
            "Crowd Energy": clean(row.get("Energy")),
            "Danceability": clean(row.get("Spotify Danceability")),
            "Vocal Type": clean(row.get("Spotify Vocal Type")),
            "Explicit/Lyric Risk": "",
            "Playlists": clean(row.get("Playlists")),
            "Source Files": clean(row.get("Source Files")),
            "Spotify Track ID": spotify_track_id,
            "Legacy Spotify ID": first_nonblank(row, "Spotify ID", "Legacy D Music Spotify ID"),
            "Spotify ISRC": clean(row.get("Spotify ISRC")),
            "Spotify Popularity": clean(row.get("Spotify Popularity")),
            "Spotify Verified": clean(row.get("Spotify Verified")),
            "Spotify Match Method": clean(row.get("Spotify Match Method")),
            "Spotify Match Score": clean(row.get("Spotify Match Score")),
            "MusicBrainz Recording ID": clean(row.get("Spotify MusicBrainz ID")),
            "MusicBrainz Verified": clean(row.get("MusicBrainz Verified")),
            "Discogs Verified": clean(row.get("Discogs Verified")),
            "iTunes Verified": clean(row.get("iTunes Verified")),
            "SecondHandSongs Search URL": secondhandsongs_search(display_title, artist),
            "SecondHandSongs Verified URL": "",
            "SecondHandSongs Link Status": "search_link_generated",
            "WhoSampled Search URL": whosampled_search(display_title, artist),
            "WhoSampled Verified URL": "",
            "WhoSampled Link Status": "search_link_generated",
            "Ultimate Guitar Search URL": ultimate_guitar_search(display_title, artist),
            "Ultimate Guitar Official Tab URL": "",
            "Ultimate Guitar Best Tab URL": "",
            "Ultimate Guitar Tab Preference": "official_tab_then_most_popular",
            "Ultimate Guitar Tab Status": "search_link_generated",
            "Duplicate Merge Notes": clean(row.get("Duplicate Merge Notes")),
            "Data Quality Notes": "",
        }
        recordings.append(recording)

        for site, url, link_type in [
            ("SecondHandSongs", recording["SecondHandSongs Search URL"], "covers/originals/search"),
            ("WhoSampled", recording["WhoSampled Search URL"], "samples/covers/remixes/search"),
            ("Ultimate Guitar", recording["Ultimate Guitar Search URL"], "official_or_best_tab/search"),
        ]:
            external_links.append(
                {
                    "Recording ID": recording_id,
                    "Song ID": song_id,
                    "Site": site,
                    "Search URL": url,
                    "Verified URL": "",
                    "Link Type": link_type,
                    "Link Status": "search_link_generated",
                    "Preferred Match Rule": "Verify exact title, artist, and version before promoting Search URL to Verified URL.",
                    "Last Checked": "",
                    "Notes": "",
                }
            )

        for playlist in split_playlists(row.get("Playlists")):
            playlist_membership.append(
                {
                    "Recording ID": recording_id,
                    "Song ID": song_id,
                    "Playlist": playlist,
                    "Source": "Main_Song_Database.csv Playlists column",
                    "Notes": "",
                }
            )

    songs = list(songs_by_id.values())

    recording_fields = [
        "Recording ID",
        "Song ID",
        "Main DB CSV Line",
        "Title",
        "Canonical Title",
        "Version",
        "Artist",
        "Original Artist",
        "Covering Artist",
        "Cover Song",
        "Album",
        "Alternate Albums",
        "Release Year",
        "Duration",
        "Duration ms",
        "Genre",
        "Genre Detail",
        "BPM",
        "BPM Source",
        "Key",
        "Key Source",
        "Scale",
        "Time Signature",
        "Tuning",
        "Capo",
        "Guitar Difficulty",
        "Bass Difficulty",
        "Drum Difficulty",
        "Vocal Range",
        "Instrumentation",
        "Main Riff/Hook",
        "Solo",
        "Arrangement Notes",
        "Mood Tags",
        "Event Tags",
        "Situation Tags",
        "Setlist Role",
        "Crowd Energy",
        "Danceability",
        "Vocal Type",
        "Explicit/Lyric Risk",
        "Playlists",
        "Source Files",
        "Spotify Track ID",
        "Legacy Spotify ID",
        "Spotify ISRC",
        "Spotify Popularity",
        "Spotify Verified",
        "Spotify Match Method",
        "Spotify Match Score",
        "MusicBrainz Recording ID",
        "MusicBrainz Verified",
        "Discogs Verified",
        "iTunes Verified",
        "SecondHandSongs Search URL",
        "SecondHandSongs Verified URL",
        "SecondHandSongs Link Status",
        "WhoSampled Search URL",
        "WhoSampled Verified URL",
        "WhoSampled Link Status",
        "Ultimate Guitar Search URL",
        "Ultimate Guitar Official Tab URL",
        "Ultimate Guitar Best Tab URL",
        "Ultimate Guitar Tab Preference",
        "Ultimate Guitar Tab Status",
        "Duplicate Merge Notes",
        "Data Quality Notes",
    ]

    song_fields = [
        "Song ID",
        "Canonical Title",
        "Canonical Artist",
        "MusicBrainz Work ID",
        "Primary Recording ID",
        "Preferred Primary Release",
        "First Published Year",
        "Genre Family",
        "Default Mood Tags",
        "Default Event Tags",
        "Default Situation Tags",
        "Notes",
    ]

    link_fields = [
        "Recording ID",
        "Song ID",
        "Site",
        "Search URL",
        "Verified URL",
        "Link Type",
        "Link Status",
        "Preferred Match Rule",
        "Last Checked",
        "Notes",
    ]

    playlist_fields = ["Recording ID", "Song ID", "Playlist", "Source", "Notes"]

    tag_options = [
        {"Category": "Mood Tags", "Value": value}
        for value in [
            "aggressive",
            "anthemic",
            "bright",
            "brooding",
            "dark",
            "dreamy",
            "driving",
            "funny",
            "happy",
            "melancholy",
            "romantic",
            "sexy",
            "wistful",
        ]
    ] + [
        {"Category": "Event Tags", "Value": value}
        for value in [
            "bar_band",
            "cookout",
            "dance_party",
            "dinner",
            "halloween",
            "late_night",
            "road_trip",
            "wedding",
            "workout",
        ]
    ] + [
        {"Category": "Setlist Role", "Value": value}
        for value in ["opener", "closer", "encore", "breather", "transition", "peak_energy"]
    ] + [
        {"Category": "Difficulty", "Value": value}
        for value in ["beginner", "easy", "intermediate", "advanced", "expert"]
    ] + [
        {"Category": "Link Status", "Value": value}
        for value in ["search_link_generated", "verified_exact", "no_good_match", "needs_review"]
    ]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUT_DIR / "songs.csv", song_fields, songs)
    write_csv(OUT_DIR / "recordings.csv", recording_fields, recordings)
    write_csv(OUT_DIR / "external_links.csv", link_fields, external_links)
    write_csv(OUT_DIR / "playlist_membership.csv", playlist_fields, playlist_membership)
    write_csv(OUT_DIR / "tag_options.csv", ["Category", "Value"], tag_options)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_csv": str(SOURCE_CSV),
        "source_rows": len(source_rows),
        "songs_rows": len(songs),
        "recordings_rows": len(recordings),
        "external_links_rows": len(external_links),
        "playlist_membership_rows": len(playlist_membership),
        "main_database_modified": False,
        "link_policy": {
            "SecondHandSongs": "Search URL generated; promote to Verified URL only after exact title/artist/version review.",
            "WhoSampled": "Search URL generated; promote to Verified URL only after exact title/artist/version review.",
            "Ultimate Guitar": "Search URL generated; prefer Official tab, otherwise most popular/highest-rated matching tab.",
        },
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    readme = f"""SongDB v2
Generated: {manifest["generated_at"]}

This folder is a new structured database built from:
{SOURCE_CSV}

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
"""
    (OUT_DIR / "README.txt").write_text(readme, encoding="utf-8")

    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

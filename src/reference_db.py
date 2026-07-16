from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Iterable

from src.config import MusicDBPaths
from src.normalization import normalize_display_text, normalize_text


def _blank(value: object) -> bool:
    return str(value or "").strip() == ""


def _clean(value: object) -> str:
    return str(value or "").strip()


def _stable_entity_id(prefix: str, *parts: object) -> str:
    import hashlib

    raw = "|".join(normalize_text(_clean(part)) for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}{digest}"


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE source_registry (
            source TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            credential_required TEXT,
            credential_environment_variables TEXT,
            used_by TEXT,
            status TEXT,
            notes TEXT
        );

        CREATE TABLE source_metadata_matrix (
            source TEXT PRIMARY KEY,
            primary_metadata TEXT NOT NULL,
            identifier_fields TEXT NOT NULL,
            best_match_keys TEXT NOT NULL,
            default_confidence TEXT NOT NULL,
            notes TEXT
        );

        CREATE TABLE reference_entities (
            entity_kind TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            canonical_title TEXT,
            canonical_artist TEXT,
            album TEXT,
            release_year TEXT,
            primary_recording_id TEXT,
            musicbrainz_work_id TEXT,
            spotify_track_id TEXT,
            musicbrainz_recording_id TEXT,
            notes TEXT,
            PRIMARY KEY (entity_kind, entity_id)
        );

        CREATE TABLE reference_identifiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_kind TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            entity_label TEXT NOT NULL,
            source TEXT NOT NULL,
            field_name TEXT NOT NULL,
            field_value TEXT NOT NULL,
            value_kind TEXT NOT NULL,
            source_url TEXT,
            verified_status TEXT,
            notes TEXT
        );

        CREATE TABLE source_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            row_number TEXT NOT NULL,
            source_name TEXT NOT NULL,
            title TEXT,
            artist TEXT,
            album TEXT,
            field_name TEXT NOT NULL,
            field_value TEXT NOT NULL,
            value_kind TEXT NOT NULL,
            notes TEXT
        );

        CREATE INDEX idx_reference_identifiers_source
            ON reference_identifiers(source);

        CREATE INDEX idx_reference_identifiers_entity
            ON reference_identifiers(entity_kind, entity_id);

        CREATE INDEX idx_source_observations_source
            ON source_observations(source_name);

        CREATE INDEX idx_source_observations_row
            ON source_observations(row_number);
        """
    )


def _insert_many(
    conn: sqlite3.Connection,
    table: str,
    columns: list[str],
    rows: Iterable[Iterable[object]],
) -> None:
    placeholders = ", ".join(["?"] * len(columns))
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    conn.executemany(sql, list(rows))


def build_reference_db(paths: MusicDBPaths) -> dict[str, int]:
    """
    Build a read-only reference-ID SQLite database from the cleaned SongDB v2 exports.

    The output is meant to be served through the API as a reference layer rather than
    as another editable working database.
    """
    output_path = paths.reference_db_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    songs = _read_csv_rows(paths.songs_csv)
    recordings = _read_csv_rows(paths.recordings_csv)
    external_links = _read_csv_rows(paths.external_links_csv)
    main_rows = _read_csv_rows(paths.active_main_csv)
    youtube_verified_rows = _read_csv_rows(paths.exports_dir / "codex" / "youtube_music_takeout_verified.csv")
    youtube_unmatched_rows = _read_csv_rows(paths.exports_dir / "codex" / "youtube_music_takeout_unmatched.csv")
    cover_candidate_rows = _read_csv_rows(paths.staging_dir / "jules" / "antigravity_cover_candidates.csv")
    source_registry = _read_csv_rows(paths.data_dir / "source_registry.csv")
    source_matrix = _read_csv_rows(paths.data_dir / "source_metadata_matrix.csv")

    song_by_id = {row.get("Song ID", ""): row for row in songs if _clean(row.get("Song ID"))}
    recording_by_id = {
        row.get("Recording ID", ""): row for row in recordings if _clean(row.get("Recording ID"))
    }
    antigravity_db = paths.staging_dir / "jules" / "music_antigravity_review.sqlite"

    source_observation_rows: list[tuple[object, ...]] = []

    def add_observations(
        *,
        row_number: str,
        source_name: str,
        title: str,
        artist: str,
        album: str,
        rows: list[dict[str, str]],
        keep_fields: list[str] | None = None,
        notes: str = "",
    ) -> None:
        for row in rows:
            fields = keep_fields or list(row.keys())
            for field_name in fields:
                value = _clean(row.get(field_name))
                if _blank(value):
                    continue
                source_observation_rows.append(
                    (
                        row_number,
                        source_name,
                        title,
                        artist,
                        album,
                        field_name,
                        value,
                        "metadata",
                        notes,
                    )
                )

    def add_sqlite_observations(
        *,
        conn: sqlite3.Connection,
        table: str,
        source_name_field: str,
        row_number_field: str,
        title_field: str | None = None,
        artist_field: str | None = None,
        album_field: str | None = None,
        source_name_override: str | None = None,
        skip_fields: set[str] | None = None,
        notes: str = "",
    ) -> None:
        try:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            columns = [col[1] for col in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        except sqlite3.Error:
            return

        skip = {"id"}
        if skip_fields:
            skip |= set(skip_fields)
        for raw_row in rows:
            row = {columns[i]: raw_row[i] for i in range(len(columns))}
            row_number = _clean(row.get(row_number_field)) or _clean(row.get("recording_id")) or _clean(row.get("original_recording_id")) or "sqlite-row"
            source_name = source_name_override or _clean(row.get(source_name_field)) or "Antigravity"
            title = _clean(row.get(title_field)) if title_field else _clean(row.get("title"))
            artist = _clean(row.get(artist_field)) if artist_field else _clean(row.get("artist"))
            album = _clean(row.get(album_field)) if album_field else _clean(row.get("album"))
            for field_name, value in row.items():
                if field_name in skip:
                    continue
                cleaned = _clean(value)
                if _blank(cleaned):
                    continue
                source_observation_rows.append(
                    (
                        row_number,
                        source_name,
                        title,
                        artist,
                        album,
                        field_name,
                        cleaned,
                        "metadata",
                        notes,
                    )
                )

    with sqlite3.connect(output_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _create_tables(conn)

        _insert_many(
            conn,
            "source_registry",
            [
                "source",
                "kind",
                "credential_required",
                "credential_environment_variables",
                "used_by",
                "status",
                "notes",
            ],
            (
                (
                    _clean(row.get("Source")),
                    _clean(row.get("Kind")),
                    _clean(row.get("Credential Required")),
                    _clean(row.get("Credential Environment Variables")),
                    _clean(row.get("Used By")),
                    _clean(row.get("Status")),
                    _clean(row.get("Notes")),
                )
                for row in source_registry
                if _clean(row.get("Source"))
            ),
        )

        _insert_many(
            conn,
            "source_metadata_matrix",
            [
                "source",
                "primary_metadata",
                "identifier_fields",
                "best_match_keys",
                "default_confidence",
                "notes",
            ],
            (
                (
                    _clean(row.get("Source")),
                    _clean(row.get("Primary Metadata")),
                    _clean(row.get("Identifier Fields")),
                    _clean(row.get("Best Match Keys")),
                    _clean(row.get("Default Confidence")),
                    _clean(row.get("Notes")),
                )
                for row in source_matrix
                if _clean(row.get("Source"))
            ),
        )

        entity_rows: list[tuple[object, ...]] = []
        identifier_rows: list[tuple[object, ...]] = []
        seen_title_ids: set[str] = set()
        seen_artist_ids: set[str] = set()
        seen_album_ids: set[str] = set()

        for row in songs:
            song_id = _clean(row.get("Song ID"))
            if not song_id:
                continue

            display_name = " - ".join(
                value for value in [_clean(row.get("Canonical Title")), _clean(row.get("Canonical Artist"))] if value
            ) or song_id
            entity_rows.append(
                (
                    "song",
                    song_id,
                    display_name,
                    _clean(row.get("Canonical Title")),
                    _clean(row.get("Canonical Artist")),
                    _clean(row.get("Preferred Primary Release")),
                    _clean(row.get("First Published Year")),
                    _clean(row.get("Primary Recording ID")),
                    _clean(row.get("MusicBrainz Work ID")),
                    "",
                    "",
                    _clean(row.get("Notes")),
                )
            )

            identifier_rows.append(
                (
                    "song",
                    song_id,
                    display_name,
                    "MusicDB",
                    "Song ID",
                    song_id,
                    "internal_id",
                    "",
                    "",
                    "Canonical SongDB v2 identifier",
                )
            )
            if not _blank(row.get("MusicBrainz Work ID")):
                identifier_rows.append(
                    (
                        "song",
                        song_id,
                        display_name,
                        "MusicBrainz",
                        "MusicBrainz Work ID",
                        _clean(row.get("MusicBrainz Work ID")),
                        "external_id",
                        "https://musicbrainz.org/",
                        "verified" if _clean(row.get("MusicBrainz Work ID")) else "",
                        "",
                    )
                )

        for row in recordings:
            recording_id = _clean(row.get("Recording ID"))
            if not recording_id:
                continue

            song_id = _clean(row.get("Song ID"))
            song_row = song_by_id.get(song_id, {})
            title = _clean(row.get("Title")) or _clean(song_row.get("Canonical Title")) or recording_id
            artist = _clean(row.get("Artist")) or _clean(song_row.get("Canonical Artist"))
            album = _clean(row.get("Album"))
            display_name = " - ".join(value for value in [title, artist] if value) or recording_id
            title_entity_id = _stable_entity_id("T", title)
            artist_entity_id = _stable_entity_id("A", artist)
            album_entity_id = _stable_entity_id("L", album) if album else ""

            entity_rows.append(
                (
                    "recording",
                    recording_id,
                    display_name,
                    title,
                    artist,
                    _clean(row.get("Album")),
                    _clean(row.get("Release Year")),
                    "",
                    _clean(song_row.get("MusicBrainz Work ID")),
                    _clean(row.get("Spotify Track ID")),
                    _clean(row.get("MusicBrainz Recording ID")),
                    _clean(row.get("Notes")),
                )
            )

            if title_entity_id not in seen_title_ids:
                seen_title_ids.add(title_entity_id)
                entity_rows.append(
                    (
                        "title",
                        title_entity_id,
                        normalize_display_text(title) or title_entity_id,
                        title,
                        "",
                        "",
                        "",
                        recording_id,
                        "",
                        "",
                        "",
                        "",
                    )
                )
                identifier_rows.append(
                    (
                        "title",
                        title_entity_id,
                        title,
                        "MusicDB",
                        "Canonical Title",
                        title,
                        "display_name",
                        "",
                        "canonical",
                        "",
                    )
                )

            if artist_entity_id not in seen_artist_ids and artist:
                seen_artist_ids.add(artist_entity_id)
                entity_rows.append(
                    (
                        "artist",
                        artist_entity_id,
                        normalize_display_text(artist) or artist_entity_id,
                        "",
                        artist,
                        "",
                        "",
                        recording_id,
                        "",
                        "",
                        "",
                        "",
                    )
                )
                identifier_rows.append(
                    (
                        "artist",
                        artist_entity_id,
                        artist,
                        "MusicDB",
                        "Canonical Artist",
                        artist,
                        "display_name",
                        "",
                        "canonical",
                        "",
                    )
                )

            if album_entity_id and album_entity_id not in seen_album_ids:
                seen_album_ids.add(album_entity_id)
                entity_rows.append(
                    (
                        "album",
                        album_entity_id,
                        normalize_display_text(album) or album_entity_id,
                        "",
                        artist,
                        album,
                        _clean(row.get("Release Year")),
                        recording_id,
                        "",
                        "",
                        "",
                        _clean(row.get("Notes")),
                    )
                )
                identifier_rows.append(
                    (
                        "album",
                        album_entity_id,
                        album,
                        "MusicDB",
                        "Album",
                        album,
                        "display_name",
                        "",
                        "canonical",
                        "",
                    )
                )

            for field_name, value, source, value_kind, source_url, verified_status in [
                ("Recording ID", recording_id, "MusicDB", "internal_id", "", "canonical"),
                ("Song ID", song_id, "MusicDB", "internal_id", "", "canonical"),
                ("Spotify Track ID", _clean(row.get("Spotify Track ID")), "Spotify", "external_id", "", _clean(row.get("Spotify Verified"))),
                ("Legacy Spotify ID", _clean(row.get("Legacy Spotify ID")), "MusicDB", "legacy_id", "", ""),
                ("Spotify ISRC", _clean(row.get("Spotify ISRC")), "Spotify", "external_id", "", ""),
                ("MusicBrainz Recording ID", _clean(row.get("MusicBrainz Recording ID")), "MusicBrainz", "external_id", "https://musicbrainz.org/", _clean(row.get("MusicBrainz Verified"))),
            ]:
                if _blank(value):
                    continue
                identifier_rows.append(
                    (
                        "recording",
                        recording_id,
                        display_name,
                        source,
                        field_name,
                        value,
                        value_kind,
                        source_url,
                        verified_status,
                        "",
                    )
                )

        for row in external_links:
            recording_id = _clean(row.get("Recording ID"))
            if not recording_id:
                continue

            entity = recording_by_id.get(recording_id, {})
            title = _clean(entity.get("Title")) or recording_id
            artist = _clean(entity.get("Artist"))
            display_name = " - ".join(value for value in [title, artist] if value) or recording_id

            for field_name in [
                "Search URL",
                "Verified URL",
            ]:
                value = _clean(row.get(field_name))
                if _blank(value):
                    continue
                identifier_rows.append(
                    (
                        "recording",
                        recording_id,
                        display_name,
                        _clean(row.get("Site")),
                        f"{_clean(row.get('Site'))} {field_name}",
                        value,
                        "url",
                        value,
                        _clean(row.get("Link Status")),
                        _clean(row.get("Notes")),
                    )
                )

        for index, row in enumerate(main_rows, start=2):
            title = _clean(row.get("Title")) or _clean(row.get("Base Title"))
            artist = _clean(row.get("Artist"))
            album = _clean(row.get("Album"))
            row_number = str(index)

            for source_name, field_name, value_kind, field_names in [
                (
                    "MusicDB",
                    "Core Metadata",
                    "metadata",
                    [
                        "Title",
                        "Base Title",
                        "Artist",
                        "Album",
                        "Duration",
                        "Genre",
                        "Year",
                        "Original Artist",
                        "Cover Song",
                        "Orig Artist",
                        "Covering Artist",
                        "Source Files",
                        "Original Data",
                        "Energy",
                        "BPM",
                        "Vibe",
                        "Playlists",
                        "Alternate Albums",
                        "Duplicate Merge Notes",
                    ],
                ),
                (
                    "Spotify",
                    "Spotify Crosswalk",
                    "id",
                    [
                        "Spotify ID",
                        "Spotify Track ID",
                        "Spotify Album",
                        "Spotify Release Date",
                        "Spotify Duration (ms)",
                        "Spotify MusicBrainz ID",
                        "Spotify Match Method",
                        "Spotify Match Score",
                        "Spotify Search Strategy",
                        "Spotify ISRC",
                        "Spotify BPM",
                        "Spotify Key",
                        "Spotify Scale",
                        "Spotify Key Full",
                        "Spotify Energy Level",
                        "Spotify Danceability",
                        "Spotify Vocal Type",
                        "Spotify Genre",
                        "Spotify Genre Detail",
                        "Spotify LastFM Tags",
                        "Spotify Vibe",
                        "Spotify AB Source",
                    ],
                ),
                (
                    "Spotify",
                    "Spotify Mood Flags",
                    "flag",
                    [
                        "Spotify Mood Happy",
                        "Spotify Mood Sad",
                        "Spotify Mood Aggressive",
                        "Spotify Mood Relaxed",
                        "Spotify Mood Party",
                    ],
                ),
                (
                    "Spotify",
                    "Spotify Verification",
                    "flag",
                    [
                        "Spotify Verified",
                    ],
                ),
                (
                    "MusicBrainz",
                    "MusicBrainz Verification",
                    "flag",
                    [
                        "MusicBrainz Verified",
                    ],
                ),
                (
                    "Discogs",
                    "Discogs Verification",
                    "flag",
                    [
                        "Discogs Verified",
                    ],
                ),
                (
                    "iTunes",
                    "iTunes Verification",
                    "flag",
                    [
                        "iTunes Verified",
                    ],
                ),
            ]:
                for field_name_inner in field_names:
                    value = _clean(row.get(field_name_inner))
                    if _blank(value):
                        continue
                    source_observation_rows.append(
                        (
                            row_number,
                            source_name,
                            title,
                            artist,
                            album,
                            field_name_inner,
                            value,
                            value_kind,
                            field_name,
                        )
                    )

        for row in youtube_verified_rows:
            title = _clean(row.get("title"))
            artist = _clean(row.get("artist"))
            album = _clean(row.get("album"))
            row_number = _clean(row.get("videoID")) or title or "youtube-verified"
            add_observations(
                row_number=row_number,
                source_name="YouTube Music",
                title=title,
                artist=artist,
                album=album,
                rows=[row],
                keep_fields=[
                    "videoID",
                    "title",
                    "artist",
                    "year",
                    "album",
                    "genre",
                    "metadata_source",
                    "match_score",
                    "match_status",
                    "spotify_track_id",
                    "spotify_url",
                    "itunes_track_id",
                    "itunes_url",
                    "source_title",
                    "source_artist",
                    "source_year",
                    "source_album",
                    "source_genre",
                    "source_release_date",
                    "source_upload_date",
                    "duration_seconds",
                    "channel",
                    "uploader",
                    "categories",
                    "tags",
                    "description",
                    "webpage_url",
                    "metadata_lookup_url",
                    "metadata_lookup_status",
                    "source_playlist_count",
                    "source_playlists",
                    "source_files",
                    "first_seen_playlist_video_creation_timestamp",
                    "last_seen_playlist_video_creation_timestamp",
                    "occurrence_count",
                    "verified_candidate_note",
                ],
                notes="YouTube Music Takeout verified export",
            )

        for row in youtube_unmatched_rows:
            title = _clean(row.get("title"))
            artist = _clean(row.get("artist"))
            album = _clean(row.get("album"))
            row_number = _clean(row.get("videoID")) or title or "youtube-unmatched"
            add_observations(
                row_number=row_number,
                source_name="YouTube Music",
                title=title,
                artist=artist,
                album=album,
                rows=[row],
                keep_fields=["videoID", "title", "artist", "year", "album", "genre", "source_playlists", "metadata_lookup_status", "match_status"],
                notes="YouTube Music Takeout unmatched export",
            )

        for row in cover_candidate_rows:
            title = _clean(row.get("title"))
            artist = _clean(row.get("artist"))
            album = _clean(row.get("album"))
            source_name = _clean(row.get("source")) or "WhoSampled"
            row_number = _clean(row.get("id")) or _clean(row.get("original_recording_id")) or title or "cover-candidate"
            add_observations(
                row_number=row_number,
                source_name=source_name,
                title=title,
                artist=artist,
                album=album,
                rows=[row],
                keep_fields=list(row.keys()),
                notes="Cover candidate export",
            )

        if antigravity_db.exists():
            with sqlite3.connect(antigravity_db) as ant_conn:
                add_sqlite_observations(
                    conn=ant_conn,
                    table="antigravity_cover_candidates",
                    source_name_field="source",
                    row_number_field="original_recording_id",
                    title_field="title",
                    artist_field="artist",
                    album_field="album",
                    notes="Antigravity cover candidate table",
                    skip_fields={"source"},
                )
                add_sqlite_observations(
                    conn=ant_conn,
                    table="antigravity_external_link_suggestions",
                    source_name_field="site",
                    row_number_field="recording_id",
                    title_field=None,
                    artist_field=None,
                    album_field=None,
                    notes="Antigravity external link suggestion table",
                    skip_fields={"site"},
                )
                add_sqlite_observations(
                    conn=ant_conn,
                    table="antigravity_mood_event_suggestions",
                    source_name_field="source_url",
                    row_number_field="recording_id",
                    title_field=None,
                    artist_field=None,
                    album_field=None,
                    source_name_override="Antigravity",
                    notes="Antigravity mood/event suggestion table",
                    skip_fields={"source_url"},
                )
                add_sqlite_observations(
                    conn=ant_conn,
                    table="antigravity_performance_suggestions",
                    source_name_field="source_url",
                    row_number_field="recording_id",
                    title_field=None,
                    artist_field=None,
                    album_field=None,
                    source_name_override="Antigravity",
                    notes="Antigravity performance suggestion table",
                    skip_fields={"source_url"},
                )

                for table, source_field, row_number_field, value_fields, field_prefix, value_kind in [
                    (
                        "antigravity_cover_candidates",
                        "source",
                        "original_recording_id",
                        ["original_recording_id", "mbid"],
                        "Cover candidate",
                        "external_id",
                    ),
                    (
                        "antigravity_external_link_suggestions",
                        "site",
                        "recording_id",
                        ["verified_url", "search_url"],
                        "External link",
                        "url",
                    ),
                    (
                        "antigravity_mood_event_suggestions",
                        "",
                        "recording_id",
                        ["source_url"],
                        "Suggestion source",
                        "url",
                    ),
                    (
                        "antigravity_performance_suggestions",
                        "",
                        "recording_id",
                        ["source_url"],
                        "Suggestion source",
                        "url",
                    ),
                ]:
                    try:
                        rows = ant_conn.execute(f"SELECT * FROM {table}").fetchall()
                        columns = [col[1] for col in ant_conn.execute(f"PRAGMA table_info({table})").fetchall()]
                    except sqlite3.Error:
                        continue

                    for raw_row in rows:
                        row = {columns[i]: raw_row[i] for i in range(len(columns))}
                        row_number = _clean(row.get(row_number_field)) or "sqlite-row"
                        source_name = _clean(row.get(source_field)) or "Antigravity"
                        entity_kind = "recording"
                        entity_id = row_number
                        entity_label = row_number
                        for field_name in value_fields:
                            value = _clean(row.get(field_name))
                            if _blank(value):
                                continue
                            identifier_rows.append(
                                (
                                    entity_kind,
                                    entity_id,
                                    entity_label,
                                    source_name,
                                    f"{field_prefix} {field_name}",
                                    value,
                                    value_kind,
                                    value if value_kind == "url" else "",
                                    "",
                                    "Antigravity review table",
                                )
                            )

        _insert_many(
            conn,
            "reference_entities",
            [
                "entity_kind",
                "entity_id",
                "display_name",
                "canonical_title",
                "canonical_artist",
                "album",
                "release_year",
                "primary_recording_id",
                "musicbrainz_work_id",
                "spotify_track_id",
                "musicbrainz_recording_id",
                "notes",
            ],
            entity_rows,
        )
        _insert_many(
            conn,
            "reference_identifiers",
            [
                "entity_kind",
                "entity_id",
                "entity_label",
                "source",
                "field_name",
                "field_value",
                "value_kind",
                "source_url",
                "verified_status",
                "notes",
            ],
            identifier_rows,
        )
        _insert_many(
            conn,
            "source_observations",
            [
                "row_number",
                "source_name",
                "title",
                "artist",
                "album",
                "field_name",
                "field_value",
                "value_kind",
                "notes",
            ],
            source_observation_rows,
        )
        conn.commit()

    return {
        "source_registry_rows": len(source_registry),
        "source_metadata_matrix_rows": len(source_matrix),
        "reference_entities_rows": len(entity_rows),
        "reference_identifiers_rows": len(identifier_rows),
        "source_observation_rows": len(source_observation_rows),
    }

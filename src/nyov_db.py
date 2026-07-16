"""Build the not-yet-officially-verified song evidence database."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sqlite3
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree

from src.config import MusicDBPaths
from src.normalization import normalize_display_text, normalize_search_text


SUPPORTED_EXTENSIONS = {".csv", ".txt", ".xlsx", ".docx", ".zip"}
SEED_COLLECTION = "NYOV"
TEXT_PAIR_RE = re.compile(r"^\s*(?P<artist>.+?)\s+(?:\u2014|\u2013|--|-)\s+(?P<title>.+?)\s*$")
IDENTIFIER_PATTERNS = [
    ("spotify_track", re.compile(r"spotify track id|spotify_track_id|spotify id", re.I)),
    ("musicbrainz_recording", re.compile(r"musicbrainz|mbid", re.I)),
    ("youtube_video", re.compile(r"video id|videoid|youtube", re.I)),
    ("itunes_track", re.compile(r"itunes.*id|trackid", re.I)),
    ("secondhandsongs", re.compile(r"secondhandsongs|shs", re.I)),
]


@dataclass(frozen=True)
class SourceFile:
    source_file_id: str
    path: str
    container_path: str
    extension: str
    parser: str
    size_bytes: int
    sha256: str
    modified_at: str


@dataclass(frozen=True)
class ParsedObservation:
    source_file_id: str
    row_number: int
    source_path: str
    parser: str
    title: str
    artist: str
    album: str
    raw_data: dict[str, str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: object) -> str:
    return normalize_display_text(re.sub(r"\s+", " ", str(value or "").strip()))


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _bytes_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_file_id(path: str, sha256: str) -> str:
    return hashlib.sha1(f"{path}|{sha256}".encode("utf-8")).hexdigest()


def _seed_id(title: str, artist: str, album: str) -> str:
    key = "|".join([normalize_search_text(title), normalize_search_text(artist), normalize_search_text(album)])
    return "NYOV-" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16].upper()


def _observation_id(source_file_id: str, row_number: int, title: str, artist: str, album: str) -> str:
    payload = f"{source_file_id}|{row_number}|{title}|{artist}|{album}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _pick(row: dict[str, str], names: Iterable[str]) -> str:
    lookup = {key.lower().strip(): value for key, value in row.items()}
    for name in names:
        value = _clean(lookup.get(name.lower()))
        if value:
            return value
    return ""


def _parse_csv_text(text: str, source_file: SourceFile) -> list[ParsedObservation]:
    observations: list[ParsedObservation] = []
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return observations
    for row_number, row in enumerate(reader, start=2):
        raw = {str(key or ""): _clean(value) for key, value in row.items()}
        title = _pick(raw, ["Title", "Song Title", "Track", "Track Name", "performing_title", "title"])
        artist = _pick(raw, ["Artist", "Artist Name", "Artist Name 1", "Track Artist", "performing_artist", "artist"])
        album = _pick(raw, ["Album", "Album Title", "Collection", "collectionName", "album"])
        video_id = _pick(raw, ["Video ID", "videoID", "youtube video id"])
        if title or artist or album or video_id:
            observations.append(
                ParsedObservation(
                    source_file_id=source_file.source_file_id,
                    row_number=row_number,
                    source_path=source_file.path,
                    parser=source_file.parser,
                    title=title,
                    artist=artist,
                    album=album,
                    raw_data=raw,
                )
            )
    return observations


def _parse_txt_text(text: str, source_file: SourceFile) -> list[ParsedObservation]:
    observations: list[ParsedObservation] = []
    for row_number, line in enumerate(text.splitlines(), start=1):
        line = _clean(line)
        if not line or line.startswith("#") or line.startswith("*"):
            continue
        match = TEXT_PAIR_RE.match(line)
        if match:
            artist = _clean(match.group("artist").strip("* "))
            title = _clean(match.group("title").strip("* "))
        else:
            artist = ""
            title = line
        observations.append(
            ParsedObservation(
                source_file_id=source_file.source_file_id,
                row_number=row_number,
                source_path=source_file.path,
                parser=source_file.parser,
                title=title,
                artist=artist,
                album="",
                raw_data={"line": line},
            )
        )
    return observations


def _parse_xlsx(path: Path, source_file: SourceFile) -> list[ParsedObservation]:
    try:
        import openpyxl
    except ImportError:
        return []

    observations: list[ParsedObservation] = []
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        for worksheet in workbook.worksheets:
            rows = worksheet.iter_rows(values_only=True)
            header_values = next(rows, None)
            if not header_values:
                continue
            headers = [_clean(value) or f"column_{index}" for index, value in enumerate(header_values, start=1)]
            for row_number, values in enumerate(rows, start=2):
                raw = {headers[index]: _clean(value) for index, value in enumerate(values or []) if index < len(headers)}
                title = _pick(raw, ["Title", "Song Title", "Track", "Track Name", "performing_title"])
                artist = _pick(raw, ["Artist", "Artist Name", "Artist Name 1", "Track Artist", "performing_artist"])
                album = _pick(raw, ["Album", "Album Title", "Collection"])
                if title or artist or album:
                    observations.append(
                        ParsedObservation(
                            source_file_id=source_file.source_file_id,
                            row_number=row_number,
                            source_path=f"{source_file.path}::{worksheet.title}",
                            parser=source_file.parser,
                            title=title,
                            artist=artist,
                            album=album,
                            raw_data=raw,
                        )
                    )
    finally:
        workbook.close()
    return observations


def _parse_docx(path: Path, source_file: SourceFile) -> list[ParsedObservation]:
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
    except Exception:
        return []
    root = ElementTree.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    lines: list[str] = []
    for paragraph in root.findall(".//w:p", ns):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", ns))
        if _clean(text):
            lines.append(text)
    return _parse_txt_text("\n".join(lines), source_file)


def _read_text_bytes(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _source_file_for_path(path: Path, *, parser: str | None = None) -> SourceFile:
    sha = _file_sha256(path)
    return SourceFile(
        source_file_id=_source_file_id(str(path), sha),
        path=str(path),
        container_path="",
        extension=path.suffix.lower(),
        parser=parser or path.suffix.lower().lstrip("."),
        size_bytes=path.stat().st_size,
        sha256=sha,
        modified_at=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
    )


def _source_file_for_zip_entry(zip_path: Path, entry_name: str, data: bytes) -> SourceFile:
    source_path = f"{zip_path}::{entry_name}"
    sha = _bytes_sha256(data)
    extension = Path(entry_name).suffix.lower()
    return SourceFile(
        source_file_id=_source_file_id(source_path, sha),
        path=source_path,
        container_path=str(zip_path),
        extension=extension,
        parser=f"zip:{extension.lstrip('.')}",
        size_bytes=len(data),
        sha256=sha,
        modified_at=datetime.fromtimestamp(zip_path.stat().st_mtime, timezone.utc).isoformat(),
    )


def _parse_source_file(path: Path) -> tuple[list[SourceFile], list[ParsedObservation]]:
    extension = path.suffix.lower()
    source_files: list[SourceFile] = []
    observations: list[ParsedObservation] = []

    if extension == ".zip":
        with zipfile.ZipFile(path) as archive:
            for entry in archive.infolist():
                entry_extension = Path(entry.filename).suffix.lower()
                if entry.is_dir() or entry_extension not in {".csv", ".txt"}:
                    continue
                data = archive.read(entry)
                source_file = _source_file_for_zip_entry(path, entry.filename, data)
                source_files.append(source_file)
                text = _read_text_bytes(data)
                if entry_extension == ".csv":
                    observations.extend(_parse_csv_text(text, source_file))
                else:
                    observations.extend(_parse_txt_text(text, source_file))
        return source_files, observations

    source_file = _source_file_for_path(path)
    source_files.append(source_file)
    if extension == ".csv":
        observations.extend(_parse_csv_text(path.read_text(encoding="utf-8-sig", errors="replace"), source_file))
    elif extension == ".txt":
        observations.extend(_parse_txt_text(path.read_text(encoding="utf-8-sig", errors="replace"), source_file))
    elif extension == ".xlsx":
        observations.extend(_parse_xlsx(path, source_file))
    elif extension == ".docx":
        observations.extend(_parse_docx(path, source_file))
    return source_files, observations


def _iter_input_files(basket_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in basket_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS and "__pycache__" not in path.parts
    )


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS nyov_promotions;
        DROP TABLE IF EXISTS nyov_conflicts;
        DROP TABLE IF EXISTS nyov_verification_attempts;
        DROP TABLE IF EXISTS nyov_identifiers;
        DROP TABLE IF EXISTS nyov_source_observations;
        DROP TABLE IF EXISTS nyov_entities;
        DROP TABLE IF EXISTS nyov_source_files;

        CREATE TABLE nyov_source_files (
            source_file_id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            container_path TEXT NOT NULL,
            extension TEXT NOT NULL,
            parser TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            modified_at TEXT NOT NULL,
            imported_at TEXT NOT NULL
        );

        CREATE TABLE nyov_entities (
            nyov_id TEXT PRIMARY KEY,
            collection TEXT NOT NULL,
            seed_title TEXT NOT NULL,
            seed_artist TEXT NOT NULL,
            seed_album TEXT NOT NULL,
            title_search TEXT NOT NULL,
            artist_search TEXT NOT NULL,
            album_search TEXT NOT NULL,
            seed_source_file_id TEXT NOT NULL,
            seed_row_number INTEGER NOT NULL,
            verification_status TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE nyov_source_observations (
            observation_id TEXT PRIMARY KEY,
            source_file_id TEXT NOT NULL,
            nyov_id TEXT,
            row_number INTEGER NOT NULL,
            source_path TEXT NOT NULL,
            parser TEXT NOT NULL,
            observed_title TEXT NOT NULL,
            observed_artist TEXT NOT NULL,
            observed_album TEXT NOT NULL,
            title_search TEXT NOT NULL,
            artist_search TEXT NOT NULL,
            album_search TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            observed_at TEXT NOT NULL
        );

        CREATE TABLE nyov_identifiers (
            identifier_id TEXT PRIMARY KEY,
            nyov_id TEXT,
            observation_id TEXT,
            source_name TEXT NOT NULL,
            identifier_type TEXT NOT NULL,
            identifier_value TEXT NOT NULL,
            evidence_field TEXT NOT NULL,
            observed_at TEXT NOT NULL
        );

        CREATE TABLE nyov_verification_attempts (
            attempt_id TEXT PRIMARY KEY,
            nyov_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            query_title TEXT NOT NULL,
            query_artist TEXT NOT NULL,
            query_album TEXT NOT NULL,
            queried_at TEXT NOT NULL,
            result_json TEXT NOT NULL,
            match_status TEXT NOT NULL,
            match_score REAL NOT NULL
        );

        CREATE TABLE nyov_conflicts (
            conflict_id TEXT PRIMARY KEY,
            nyov_id TEXT NOT NULL,
            conflict_type TEXT NOT NULL,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            resolved_at TEXT NOT NULL
        );

        CREATE TABLE nyov_promotions (
            promotion_id TEXT PRIMARY KEY,
            nyov_id TEXT NOT NULL,
            target_table TEXT NOT NULL,
            target_key TEXT NOT NULL,
            promoted_at TEXT NOT NULL,
            promoted_by TEXT NOT NULL,
            notes TEXT NOT NULL
        );
        """
    )


def _insert_source_files(conn: sqlite3.Connection, source_files: list[SourceFile], imported_at: str) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO nyov_source_files
        (source_file_id, path, container_path, extension, parser, size_bytes, sha256, modified_at, imported_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                source.source_file_id,
                source.path,
                source.container_path,
                source.extension,
                source.parser,
                source.size_bytes,
                source.sha256,
                source.modified_at,
                imported_at,
            )
            for source in source_files
        ],
    )


def _build_seed_entities(seed_observations: list[ParsedObservation], imported_at: str) -> dict[tuple[str, str, str], str]:
    seed_index: dict[tuple[str, str, str], str] = {}
    for observation in seed_observations:
        title = _clean(observation.title)
        artist = _clean(observation.artist)
        album = _clean(observation.album)
        if not title or not artist:
            continue
        key = (normalize_search_text(title), normalize_search_text(artist), normalize_search_text(album))
        seed_index.setdefault(key, _seed_id(title, artist, album))
    return seed_index


def _insert_entities(
    conn: sqlite3.Connection,
    seed_observations: list[ParsedObservation],
    seed_index: dict[tuple[str, str, str], str],
    imported_at: str,
) -> None:
    inserted: set[str] = set()
    rows = []
    for observation in seed_observations:
        title = _clean(observation.title)
        artist = _clean(observation.artist)
        album = _clean(observation.album)
        key = (normalize_search_text(title), normalize_search_text(artist), normalize_search_text(album))
        nyov_id = seed_index.get(key)
        if not nyov_id or nyov_id in inserted:
            continue
        inserted.add(nyov_id)
        rows.append(
            (
                nyov_id,
                SEED_COLLECTION,
                title,
                artist,
                album,
                key[0],
                key[1],
                key[2],
                observation.source_file_id,
                observation.row_number,
                "nyov_seed_unverified",
                imported_at,
            )
        )
    conn.executemany(
        """
        INSERT INTO nyov_entities
        (nyov_id, collection, seed_title, seed_artist, seed_album, title_search, artist_search, album_search,
         seed_source_file_id, seed_row_number, verification_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _match_seed(observation: ParsedObservation, seed_index: dict[tuple[str, str, str], str]) -> str:
    title_key = normalize_search_text(observation.title)
    artist_key = normalize_search_text(observation.artist)
    album_key = normalize_search_text(observation.album)
    return seed_index.get((title_key, artist_key, album_key)) or seed_index.get((title_key, artist_key, "")) or ""


def _identifier_source(identifier_type: str) -> str:
    if identifier_type.startswith("spotify"):
        return "Spotify"
    if identifier_type.startswith("musicbrainz"):
        return "MusicBrainz"
    if identifier_type.startswith("youtube"):
        return "YouTube Music"
    if identifier_type.startswith("itunes"):
        return "iTunes"
    if identifier_type.startswith("secondhandsongs"):
        return "SecondHandSongs"
    return "Unknown"


def _extract_identifiers(observation_id: str, nyov_id: str, raw_data: dict[str, str], observed_at: str) -> list[tuple[str, str, str, str, str, str, str, str]]:
    rows = []
    for field, value in raw_data.items():
        value = _clean(value)
        if not value:
            continue
        identifier_type = ""
        for candidate_type, pattern in IDENTIFIER_PATTERNS:
            if pattern.search(field):
                identifier_type = candidate_type
                break
        if not identifier_type:
            continue
        identifier_id = hashlib.sha1(f"{observation_id}|{field}|{value}".encode("utf-8")).hexdigest()
        rows.append(
            (
                identifier_id,
                nyov_id,
                observation_id,
                _identifier_source(identifier_type),
                identifier_type,
                value,
                field,
                observed_at,
            )
        )
    return rows


def _insert_observations(
    conn: sqlite3.Connection,
    observations: list[ParsedObservation],
    seed_index: dict[tuple[str, str, str], str],
    imported_at: str,
) -> None:
    observation_rows = []
    identifier_rows = []
    seen_observations: set[str] = set()
    seen_identifiers: set[str] = set()
    for observation in observations:
        title = _clean(observation.title)
        artist = _clean(observation.artist)
        album = _clean(observation.album)
        if not (title or artist or album):
            continue
        observation_id = _observation_id(observation.source_file_id, observation.row_number, title, artist, album)
        if observation_id in seen_observations:
            continue
        seen_observations.add(observation_id)
        nyov_id = _match_seed(observation, seed_index)
        raw_json = json.dumps(observation.raw_data, ensure_ascii=False, sort_keys=True)
        observation_rows.append(
            (
                observation_id,
                observation.source_file_id,
                nyov_id,
                observation.row_number,
                observation.source_path,
                observation.parser,
                title,
                artist,
                album,
                normalize_search_text(title),
                normalize_search_text(artist),
                normalize_search_text(album),
                raw_json,
                imported_at,
            )
        )
        for identifier in _extract_identifiers(observation_id, nyov_id, observation.raw_data, imported_at):
            if identifier[0] not in seen_identifiers:
                seen_identifiers.add(identifier[0])
                identifier_rows.append(identifier)

    conn.executemany(
        """
        INSERT INTO nyov_source_observations
        (observation_id, source_file_id, nyov_id, row_number, source_path, parser,
         observed_title, observed_artist, observed_album, title_search, artist_search, album_search, raw_json, observed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        observation_rows,
    )
    conn.executemany(
        """
        INSERT INTO nyov_identifiers
        (identifier_id, nyov_id, observation_id, source_name, identifier_type, identifier_value, evidence_field, observed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        identifier_rows,
    )


def build_nyov_db(paths: MusicDBPaths, *, seed_csv: Path | None = None, basket_dir: Path | None = None, output_db: Path | None = None) -> dict[str, int | str]:
    seed_csv = (seed_csv or paths.basket_dir / "MyMusicBasefiltered_fixed.csv").resolve()
    basket_dir = (basket_dir or paths.basket_dir).resolve()
    output_db = (output_db or paths.nyov_db_path).resolve()
    imported_at = _utc_now()

    all_source_files: list[SourceFile] = []
    all_observations: list[ParsedObservation] = []
    for input_file in _iter_input_files(basket_dir):
        source_files, observations = _parse_source_file(input_file)
        all_source_files.extend(source_files)
        all_observations.extend(observations)

    seed_source = _source_file_for_path(seed_csv, parser="seed_csv")
    seed_observations = _parse_csv_text(seed_csv.read_text(encoding="utf-8-sig", errors="replace"), seed_source)
    if seed_source.source_file_id not in {source.source_file_id for source in all_source_files}:
        all_source_files.append(seed_source)
    all_observations.extend(seed_observations)
    seed_index = _build_seed_entities(seed_observations, imported_at)

    output_db.parent.mkdir(parents=True, exist_ok=True)
    if output_db.exists():
        output_db.unlink()
    with sqlite3.connect(output_db) as conn:
        _create_schema(conn)
        _insert_source_files(conn, all_source_files, imported_at)
        _insert_entities(conn, seed_observations, seed_index, imported_at)
        _insert_observations(conn, all_observations, seed_index, imported_at)
        summary = {
            "output_db": str(output_db),
            "seed_csv": str(seed_csv),
            "basket_dir": str(basket_dir),
            "source_files": conn.execute("SELECT COUNT(*) FROM nyov_source_files").fetchone()[0],
            "seed_entities": conn.execute("SELECT COUNT(*) FROM nyov_entities").fetchone()[0],
            "source_observations": conn.execute("SELECT COUNT(*) FROM nyov_source_observations").fetchone()[0],
            "matched_observations": conn.execute("SELECT COUNT(*) FROM nyov_source_observations WHERE nyov_id != ''").fetchone()[0],
            "identifiers": conn.execute("SELECT COUNT(*) FROM nyov_identifiers").fetchone()[0],
            "verification_attempts": 0,
            "conflicts": 0,
        }
    return summary

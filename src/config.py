"""Central path configuration for MusicDB automation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def project_root() -> Path:
    """Return the MusicDB root, overridable with MUSICDB_ROOT."""
    return Path(os.environ.get("MUSICDB_ROOT", _repo_root())).expanduser().resolve()


@dataclass(frozen=True)
class MusicDBPaths:
    root: Path
    scripts_dir: Path
    data_dir: Path
    basket_dir: Path
    active_main_csv: Path
    songdb_v2_dir: Path
    recordings_csv: Path
    songs_csv: Path
    external_links_csv: Path
    playlist_membership_csv: Path
    staging_dir: Path
    exports_dir: Path
    backups_dir: Path
    sqlite_poc_path: Path
    reference_db_path: Path
    nyov_db_path: Path


def paths(root: Path | None = None) -> MusicDBPaths:
    root = (root or project_root()).resolve()
    data_dir = root / "data"
    songdb_v2_dir = root / "SongDB_v2"
    return MusicDBPaths(
        root=root,
        scripts_dir=root / "scripts",
        data_dir=data_dir,
        basket_dir=root / "basket",
        active_main_csv=data_dir / "processed" / "Main_Song_Database.csv",
        songdb_v2_dir=songdb_v2_dir,
        recordings_csv=songdb_v2_dir / "recordings.csv",
        songs_csv=songdb_v2_dir / "songs.csv",
        external_links_csv=songdb_v2_dir / "external_links.csv",
        playlist_membership_csv=songdb_v2_dir / "playlist_membership.csv",
        staging_dir=data_dir / "staging",
        exports_dir=data_dir / "exports",
        backups_dir=data_dir / "backups",
        sqlite_poc_path=data_dir / "staging" / "jules" / "poc.sqlite",
        reference_db_path=data_dir / "staging" / "jules" / "reference_ids.sqlite",
        nyov_db_path=data_dir / "staging" / "codex" / "nyov.sqlite",
    )


def require_under_root(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    resolved.relative_to(root.resolve())
    return resolved

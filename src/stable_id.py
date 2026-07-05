import hashlib
from typing import Optional
from .normalization import normalize_text, normalize_artist

def generate_stable_id(title: str, artist: str, version: Optional[str] = None) -> str:
    """
    Generates a stable ID based on normalized title, artist, and version.
    """
    norm_title = normalize_text(title)
    norm_artist = normalize_artist(artist)

    components = f"{norm_title}|{norm_artist}"
    if version:
        norm_version = normalize_text(version)
        components += f"|{norm_version}"

    return hashlib.md5(components.encode('utf-8')).hexdigest()

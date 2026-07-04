import re
import unicodedata

def normalize_text(text: str) -> str:
    if not text:
        return ""
    # NFKD normalization to decompose characters
    text = unicodedata.normalize('NFKD', str(text))
    # Keep alphanumeric, spaces, and common punctuation
    text = re.sub(r'[^\w\s.,-]', '', text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()

def normalize_artist(artist: str) -> str:
    # Basic artist normalization, strip "The ", etc. (optional, depending on requirements)
    artist = normalize_text(artist)
    if artist.startswith("the "):
        artist = artist[4:]
    return artist

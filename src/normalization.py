import re
import unicodedata
from urllib.parse import unquote


_DISPLAY_TRANSLATION = str.maketrans(
    {
        "\u00a0": " ",  # non-breaking space
        "\u1680": " ",
        "\u2000": " ",
        "\u2001": " ",
        "\u2002": " ",
        "\u2003": " ",
        "\u2004": " ",
        "\u2005": " ",
        "\u2006": " ",
        "\u2007": " ",
        "\u2008": " ",
        "\u2009": " ",
        "\u200a": " ",
        "\u202f": " ",
        "\u205f": " ",
        "\u3000": " ",
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u2032": "'",
        "\u02bc": "'",
        "\u02b9": "'",
        "\u00b4": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u201f": '"',
        "\u2033": '"',
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
        "\u2212": "-",
        "\u2043": "-",
        "\u223c": "~",
        "\uff5e": "~",
        "\u00b7": "·",
    }
)


def _strip_invisible(text: str) -> str:
    return "".join(ch for ch in text if unicodedata.category(ch) not in {"Cf", "Cc"} or ch in "\t\n\r")


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


def normalize_search_text(text: str) -> str:
    """Return a comparison key suitable for resilient search matching."""

    return normalize_text(normalize_display_text(text))


def normalize_display_text(text: str) -> str:
    """Return a display-safe Unicode string with compatibility fonts cleaned up.

    This keeps legitimate diacritics intact, but normalizes compatibility
    characters, smart punctuation, and invisible formatting noise.
    """

    if text is None:
        return ""
    value = str(text)
    if re.search(r"%[0-9A-Fa-f]{2}", value) and not re.match(r"(?i)^[a-z][a-z0-9+.-]*://", value):
        value = unquote(value)
    value = value.translate(_DISPLAY_TRANSLATION)
    value = unicodedata.normalize("NFKC", value)
    value = _strip_invisible(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_display_row(row: dict[str, str], fields: tuple[str, ...] | None = None) -> dict[str, str]:
    """Normalize a dict row in place-like fashion for a CSV export."""

    normalized = dict(row)
    target_fields = fields or tuple(row.keys())
    for field in target_fields:
        if field in normalized:
            normalized[field] = normalize_display_text(normalized.get(field, ""))
    return normalized

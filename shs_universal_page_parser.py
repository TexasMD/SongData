#!/usr/bin/env python3
"""
shs_universal_page_parser.py

Unified, deterministic, high-throughput parser and relational dataset builder
for saved SecondHandSongs (SHS) HTML webpages.

Key Capabilities:
1. Cascading multi-signal page categorization (work, performance, artist,
   release, web_cover, admin_other) via canonical URL, OpenGraph tags, SPA
   root container data-controller/data-route, breadcrumbs, title, & filename.
2. Lossless extraction of core entity attributes, <dl> definition lists,
   Schema.org Microdata / JSON-LD, badges ([1st], Instrumental, Live, Medley),
   responsive tabular rows, and external provider IDs (ISWC, IPI, Spotify,
   YouTube, MusicBrainz).
3. Row-Level Relational Integrity: Every HTML table row is preserved as an
   atomic record with parent container context prepended to every row, plus
   full dictionary field columns.
4. Catalog Integrity & Business Rules:
   - Sanitize release/historical years, stripping .0 float suffixes.
   - Disambiguate colliding song titles via (performing_artist, song_title)
     and composer credits; protect short/numeric titles (<= 4 chars) and
     reject unanchored substring joins.
   - Classify subsequent collaborator / group-member renditions as 'aarw'
     (Artist Autocover / Re-recording With) rather than generic 'cover'.
   - Strictly separate adaptations from first releases ('1strel') and route
     adaptations to excluded_adaptations.csv.
   - Harmonize canonical earliest original performer and release year across
     all covers of the same underlying composition.
5. Dual Output Generation:
   - Row-Level Relational CSV (--output-csv / --output)
   - Normalized SQLite Database (--database / --output-sqlite) containing both
     3NF relational tables (entities, page_tables, table_rows, entity_credits,
     provider_identifiers) and observation catalog tables (parser_runs, pages,
     records, record_cells, field_catalog, field_observations).
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
import hashlib
import json
import logging
import multiprocessing
from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

VERSION = "3.0.0"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

YEAR_REGEX = re.compile(r"\b(16\d{2}|17\d{2}|18\d{2}|19\d{2}|20\d{2})\b")
ISWC_REGEX = re.compile(r"\b(T-?\d{3}\.?\d{3}\.?\d{3}-?\d)\b", re.I)
IPI_REGEX = re.compile(r"\b(\d{9,11})\b")
SPOTIFY_RE = re.compile(
    r"open\.spotify\.com/(track|artist|album)/([A-Za-z0-9]{22})", re.I
)
YOUTUBE_RE = re.compile(
    r"(?:youtube\.com/watch\?(?:[^#\s\"']*&)?v=|youtu\.be/|"
    r"youtube\.com/embed/)([A-Za-z0-9_-]{11})",
    re.I,
)
MB_UUID_RE = re.compile(
    r"musicbrainz\.org/(artist|recording|work|release)/([0-9a-f-]{36})", re.I
)
ROUTE_RE = re.compile(
    r"/(artist|work|performance|release|web-cover)/(\d+)(?:/|$)", re.I
)

STANDARD_85_FIELDS = [
    "page_type",
    "canonical_url",
    "shs_entity_type",
    "shs_entity_id",
    "page_title",
    "document_heading",
    "is_all_versions_view",
    "work_title",
    "work_id",
    "written_by",
    "music_written_by",
    "lyrics_written_by",
    "original_music_written_by",
    "original_lyrics_written_by",
    "work_language",
    "iswc",
    "published_by",
    "composition_date",
    "copyright_date",
    "adapted_from",
    "uses_parts_from",
    "licensing_status",
    "roud_number",
    "total_covers_count",
    "total_samples_count",
    "total_adaptations_count",
    "performance_id",
    "performance_title",
    "performing_artist",
    "performing_artist_id",
    "performance_type_classification",
    "is_first_release",
    "performance_release_date",
    "performance_release_year",
    "first_recorded_date",
    "performance_language",
    "is_instrumental",
    "is_live",
    "is_medley",
    "released_on_title",
    "released_on_release_id",
    "other_releases_list",
    "other_versions_list",
    "chart_placings",
    "user_rating",
    "youtube_video_id",
    "spotify_track_id",
    "artist_name",
    "artist_id",
    "artist_personal_name",
    "artist_aliases",
    "artist_birth_date",
    "artist_death_date",
    "artist_country",
    "artist_gender",
    "artist_ipi",
    "artist_affiliation",
    "artist_member_of",
    "artist_members",
    "artist_family",
    "artist_years_active",
    "artist_ranking",
    "spotify_artist_id",
    "musicbrainz_artist_id",
    "release_title",
    "release_id",
    "release_artist",
    "release_date",
    "release_format",
    "release_label",
    "release_catalog_number",
    "release_ean_upc",
    "release_tracklist",
    "tribute_to_artist",
    "spotify_album_id",
    "musicbrainz_release_id",
    "web_cover_id",
    "web_cover_original_work_url",
    "web_cover_channel_name",
    "web_cover_upload_date",
    "curator_comments",
    "not_to_be_confused_with",
    "entity_tags",
    "table_cells_count",
    "pagination_has_next",
]

RELATIONAL_ROW_COLUMNS = [
    "source_filename",
    "page_entity_type",
    "page_entity_id",
    "page_canonical_url",
    "parent_work_title",
    "parent_work_writers",
    "parent_work_iswc",
    "parent_work_language",
    "parent_artist_name",
    "parent_release_title",
    "canonical_original_performer",
    "canonical_original_year",
    "composition_disambiguation_key",
    "short_or_numeric_title_guard",
    "table_section_heading",
    "table_ordinal",
    "table_row_ordinal",
    "row_entity_type",
    "row_entity_id",
    "row_title",
    "row_performer",
    "row_performer_id",
    "row_release_date",
    "row_release_year",
    "row_originally_by",
    "row_originally_by_id",
    "row_label",
    "is_first_release",
    "is_adaptation",
    "is_instrumental",
    "is_live",
    "is_medley",
    "badges_raw",
    "classification",
]

DL_LABEL_MAP = {
    "written by": "written_by",
    "author": "written_by",
    "composer": "music_written_by",
    "music written by": "music_written_by",
    "lyricist": "lyrics_written_by",
    "lyrics written by": "lyrics_written_by",
    "original music written by": "original_music_written_by",
    "original lyrics written by": "original_lyrics_written_by",
    "language": "work_language",
    "iswc": "iswc",
    "published by": "published_by",
    "publisher": "published_by",
    "composition date": "composition_date",
    "copyright date": "copyright_date",
    "roud number": "roud_number",
    "adapted from": "adapted_from",
    "uses parts from": "uses_parts_from",
    "licensing": "licensing_status",
    "licensing status": "licensing_status",
    "born": "artist_birth_date",
    "birth date": "artist_birth_date",
    "died": "artist_death_date",
    "death date": "artist_death_date",
    "country": "artist_country",
    "nationality": "artist_country",
    "gender": "artist_gender",
    "birth name": "artist_personal_name",
    "legal name": "artist_personal_name",
    "personal name": "artist_personal_name",
    "aliases": "artist_aliases",
    "years active": "artist_years_active",
    "member of": "artist_member_of",
    "members": "artist_members",
    "affiliation": "artist_affiliation",
    "family": "artist_family",
    "not to be confused with": "not_to_be_confused_with",
    "tribute to": "tribute_to_artist",
    "ipi": "artist_ipi",
    "released on": "released_on_title",
    "release date": "release_date",
    "first recorded": "first_recorded_date",
    "chart placings": "chart_placings",
    "tags": "entity_tags",
    "comments": "curator_comments",
    "rating": "user_rating",
    "other version": "other_versions_list",
    "other versions": "other_versions_list",
    "other release": "other_releases_list",
    "other releases": "other_releases_list",
    "label": "release_label",
    "catalog number": "release_catalog_number",
    "barcode": "release_ean_upc",
    "ean": "release_ean_upc",
    "format": "release_format",
    "medium": "release_format",
    "tracklist": "release_tracklist",
    "tracks": "release_tracklist",
    "artist": "release_artist",
    "channel": "web_cover_channel_name",
    "upload date": "web_cover_upload_date",
}


def clean_text(val: Any) -> str:
    if not val:
        return ""
    return re.sub(r"\s+", " ", str(val).replace("\xa0", " ")).strip()


def norm_key(val: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (val or "").casefold()).strip()


def sanitize_year(date_str: Any) -> str:
    if not date_str:
        return ""
    cleaned = re.sub(r"\.0+$", "", str(date_str).strip())
    match = YEAR_REGEX.search(cleaned)
    if match:
        return str(int(match.group(1)))
    return ""


def is_short_or_numeric_title(title: str) -> bool:
    nk = norm_key(title).replace(" ", "")
    if not nk:
        return False
    return len(nk) <= 4 or nk.isdigit()


def build_disambiguation_key(
    title: str, performer: str, writers: str = ""
) -> str:
    t_norm = norm_key(title)
    p_norm = norm_key(performer)
    w_norm = norm_key(writers)
    if not t_norm:
        return ""
    return f"{p_norm}||{t_norm}||{w_norm}"


def decode_html_bytes(raw: bytes) -> Tuple[str, str]:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8-replace"


def make_soup(html_text: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html_text, "lxml")
    except Exception:
        return BeautifulSoup(html_text, "html.parser")


def extract_entity_from_url(url_str: str) -> Tuple[str, str]:
    if not url_str:
        return "", ""
    match = ROUTE_RE.search(url_str)
    if match:
        etype = match.group(1).lower().replace("web-cover", "web_cover")
        return etype, match.group(2)
    return "", ""


def detect_from_url_signals(soup: BeautifulSoup) -> Tuple[str, str, str]:
    canon = soup.find("link", rel="canonical")
    if canon and canon.get("href"):
        href = clean_text(canon.get("href"))
        et, eid = extract_entity_from_url(href)
        if et:
            return et, eid, href
    for sel in (
        'meta[property="og:url"]',
        'meta[name="cyt:source-webpage-url"]',
        'meta[name="source-webpage-url"]',
    ):
        node = soup.select_one(sel)
        if node and node.get("content"):
            href = clean_text(node.get("content"))
            et, eid = extract_entity_from_url(href)
            if et:
                return et, eid, href
    return "", "", ""


def detect_from_dom_or_filename(
    soup: BeautifulSoup, filename: str
) -> Tuple[str, str]:
    spa = soup.select_one("[data-controller],[data-route]")
    if spa:
        route_val = spa.get("data-route", "") or spa.get("data-controller", "")
        et, eid = extract_entity_from_url(str(route_val))
        if et:
            return et, eid

    fn = filename.lower()
    if "__perf" in fn or fn.startswith("cyt-performance-") or "cyt-atra-" in fn:
        m = re.search(r"(?:__perf|-)+(\d+)", fn)
        return "performance", (m.group(1) if m else "")
    if fn.startswith("cyt-work-") or "versions of " in fn:
        m = re.search(r"(\d+)", fn)
        return "work", (m.group(1) if m else "")
    if fn.startswith("cyt-artist-") or fn.startswith("artist_"):
        m = re.search(r"(\d+)", fn)
        return "artist", (m.group(1) if m else "")
    if fn.startswith("cyt-release-") or fn.startswith("tracks on "):
        m = re.search(r"(\d+)", fn)
        return "release", (m.group(1) if m else "")
    if "web cover" in fn or (soup.title and "web cover" in soup.title.text.lower()):
        m = re.search(r"(\d+)", fn)
        return "web_cover", (m.group(1) if m else "")
    return "admin_other", ""


def categorize_page(
    soup: BeautifulSoup, filepath: Path
) -> Tuple[str, str, str]:
    et, eid, canon_url = detect_from_url_signals(soup)
    if et:
        return et, eid, canon_url
    et, eid = detect_from_dom_or_filename(soup, filepath.name)
    return et, eid, canon_url


def extract_header_first_releases(
    soup: BeautifulSoup,
) -> Tuple[set, set, str, str]:
    perf_ids = set()
    artist_names = set()
    orig_performer = ""
    orig_year = ""

    for art in soup.find_all(["article", "section", "div"]):
        for p_tag in art.find_all("p", recursive=False):
            p_txt = clean_text(p_tag.get_text())
            p_low = p_txt.lower()
            if (
                "first release by" in p_low
                or "first recording and first release by" in p_low
                or "first recording by" in p_low
            ):
                for a in p_tag.find_all("a", href=re.compile(r"/performance/\d+")):
                    _, pid = extract_entity_from_url(a.get("href", ""))
                    if pid:
                        perf_ids.add(pid)
                art_span = p_tag.find(attrs={"itemprop": "byArtist"})
                if not art_span:
                    art_span = p_tag.find("a", href=re.compile(r"/artist/\d+"))
                if art_span:
                    aname = clean_text(art_span.get_text())
                    artist_names.add(aname.lower())
                    if not orig_performer:
                        orig_performer = aname
                yr = sanitize_year(p_txt)
                if yr and not orig_year:
                    orig_year = yr
    return perf_ids, artist_names, orig_performer, orig_year


def extract_dl_and_credits(
    soup: BeautifulSoup, meta: Dict[str, Any]
) -> None:
    for dl in soup.find_all("dl"):
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        for dt, dd in zip(dts, dds):
            label = clean_text(dt.get_text()).rstrip(":").lower()
            val = clean_text(dd.get_text())
            if not label or not val:
                continue
            mapped = DL_LABEL_MAP.get(label)
            if mapped:
                meta["dict_fields"][mapped] = val
            if label in ("written by", "author", "composer", "music written by", "lyrics written by"):
                writers = []
                for a in dd.find_all("a", href=re.compile(r"/artist/\d+")):
                    w_name = clean_text(a.get_text())
                    _, aid = extract_entity_from_url(a.get("href", ""))
                    writers.append(w_name)
                    meta["credits"].append((mapped or "written_by", w_name, aid))
                if writers and not meta["parent_work_writers"]:
                    meta["parent_work_writers"] = ", ".join(writers)
                elif not meta["parent_work_writers"]:
                    meta["parent_work_writers"] = val
            if "iswc" in label:
                m = ISWC_REGEX.search(val)
                meta["parent_work_iswc"] = m.group(1) if m else val
            elif label == "language":
                if meta["page_entity_type"] == "performance":
                    meta["dict_fields"]["performance_language"] = val
                else:
                    meta["parent_work_language"] = val
            elif label in ("released on", "release date"):
                meta["dict_fields"]["release_date"] = val
                meta["dict_fields"]["performance_release_year"] = sanitize_year(val)


def extract_providers_and_counts(
    soup: BeautifulSoup, html_str: str, meta: Dict[str, Any]
) -> None:
    df = meta["dict_fields"]
    for stype, sid in SPOTIFY_RE.findall(html_str):
        st = stype.lower()
        meta["provider_ids"].append(("spotify", f"{st}_id", sid))
        df.setdefault(f"spotify_{st}_id", sid)
    for yid in YOUTUBE_RE.findall(html_str):
        meta["provider_ids"].append(("youtube", "video_id", yid))
        df.setdefault("youtube_video_id", yid)
    for mtype, muuid in MB_UUID_RE.findall(html_str):
        mt = mtype.lower()
        meta["provider_ids"].append(("musicbrainz", f"{mt}_uuid", muuid))
        df.setdefault(f"musicbrainz_{mt}_id", muuid)
    if meta["parent_work_iswc"]:
        meta["provider_ids"].append(("iswc", "iswc_code", meta["parent_work_iswc"]))
        df["iswc"] = meta["parent_work_iswc"]

    for tab_key, field_key in (
        ("versions", "total_covers_count"),
        ("samples", "total_samples_count"),
        ("adaptations", "total_adaptations_count"),
    ):
        tab_a = soup.find("a", href=re.compile(rf"/{tab_key}$"))
        if tab_a:
            badge = tab_a.find("span", class_="badge")
            if badge and clean_text(badge.get_text()).isdigit():
                df[field_key] = clean_text(badge.get_text())


def parse_page_metadata(
    soup: BeautifulSoup, html_str: str, filepath: Path
) -> Dict[str, Any]:
    etype, eid, canon_url = categorize_page(soup, filepath)
    h1 = soup.find("h1")
    h1_text = clean_text(h1.get_text()) if h1 else ""
    name_span = h1.find(attrs={"itemprop": "name"}) if h1 else None
    pref_name = clean_text(name_span.get_text()) if name_span else h1_text
    if not pref_name and soup.title:
        pref_name = clean_text(soup.title.get_text().split("|")[0])
    if etype == "work" and pref_name:
        pref_name = re.sub(
            r"\s+\d+(?:st|nd|rd|th)\s+in\s+\d{4}$", "", pref_name, flags=re.I
        ).strip()

    f_pids, f_artists, orig_perf, orig_yr = extract_header_first_releases(soup)
    df: Dict[str, str] = {k: "" for k in STANDARD_85_FIELDS}
    df["page_type"] = etype
    df["shs_entity_type"] = etype if etype != "admin_other" else ""
    df["shs_entity_id"] = str(eid or "")
    df["canonical_url"] = canon_url
    df["page_title"] = clean_text(soup.title.get_text()) if soup.title else ""
    df["document_heading"] = h1_text
    df["is_all_versions_view"] = str(canon_url.endswith("/all"))
    df["table_cells_count"] = str(len(soup.find_all(["td", "th"])))
    df["pagination_has_next"] = str(
        bool(soup.select_one('a[rel="next"], ul.pagination li.next a'))
    )

    meta: Dict[str, Any] = {
        "source_filename": filepath.name,
        "page_entity_type": etype,
        "page_entity_id": str(eid or ""),
        "page_canonical_url": canon_url,
        "preferred_name": pref_name,
        "parent_work_title": pref_name if etype == "work" else "",
        "parent_work_writers": "",
        "parent_work_iswc": "",
        "parent_work_language": "",
        "parent_artist_name": pref_name if etype == "artist" else "",
        "parent_release_title": pref_name if etype == "release" else "",
        "canonical_original_performer": orig_perf,
        "canonical_original_year": orig_yr,
        "first_release_perf_ids": f_pids,
        "first_release_artist_names": f_artists,
        "credits": [],
        "provider_ids": [],
        "dict_fields": df,
    }

    if etype == "work":
        df["work_title"] = pref_name
        df["work_id"] = str(eid or "")
    elif etype == "performance":
        df["performance_title"] = pref_name
        df["performance_id"] = str(eid or "")
        if h1:
            art_a = h1.find("a", href=re.compile(r"/artist/\d+"))
            if art_a:
                meta["parent_artist_name"] = clean_text(art_a.get_text())
                df["performing_artist"] = meta["parent_artist_name"]
                _, aid = extract_entity_from_url(art_a.get("href", ""))
                df["performing_artist_id"] = aid
    elif etype == "artist":
        df["artist_name"] = pref_name
        df["artist_id"] = str(eid or "")
    elif etype == "release":
        df["release_title"] = pref_name
        df["release_id"] = str(eid or "")
    elif etype == "web_cover":
        df["web_cover_id"] = str(eid or "")

    extract_dl_and_credits(soup, meta)
    extract_providers_and_counts(soup, html_str, meta)
    return meta


def classify_row_entity(
    row_dict: Dict[str, Any], parent_meta: Dict[str, Any]
) -> str:
    if row_dict["is_adaptation"]:
        return "adaptation"
    if row_dict["is_first_release"]:
        return "1strel"

    p_artist = (parent_meta.get("parent_artist_name") or "").lower()
    orig_perf = (parent_meta.get("canonical_original_performer") or "").lower()
    row_orig = (row_dict.get("row_originally_by") or "").lower()
    row_perf = (row_dict.get("row_performer") or "").lower()
    writers = (parent_meta.get("parent_work_writers") or "").lower()

    collab_tokens = (" with ", " feat", " & ", " and ", " duet ", " featuring ", " vs")
    for ref_artist in (p_artist, orig_perf, row_orig):
        if ref_artist and len(ref_artist) >= 3 and ref_artist in row_perf:
            if row_perf != ref_artist or any(t in row_perf for t in collab_tokens):
                return "aarw"
    if writers and any(t in row_perf for t in collab_tokens):
        for w_part in [w.strip() for w in writers.split(",") if len(w.strip()) >= 4]:
            if w_part in row_perf:
                return "aarw"

    if row_dict["is_instrumental"]:
        return "instrumental"
    return "cover"


def detect_table_adaptation(
    table: Tag, heading_lower: str, parent_meta: Dict[str, Any]
) -> bool:
    if any(k in heading_lower for k in ("adaptation", "adapted song", "translation")):
        return True
    if parent_meta["page_entity_type"] == "work" and parent_meta["page_entity_id"]:
        for p_div in table.find_parents(id=True):
            pid = str(p_div.get("id", ""))
            m_work = re.search(r"workVersions\.(\d+)", pid)
            if m_work and m_work.group(1) != str(parent_meta["page_entity_id"]):
                return True
            if "workversions" in pid.lower() and any(
                lang in pid.lower()
                for lang in ("spanish", "french", "german", "dutch", "italian")
            ):
                return True
    return False


def map_table_headers(table: Tag) -> Tuple[List[str], Dict[str, int]]:
    ths = [clean_text(th.get_text()) for th in table.find_all("th")]
    col_map = {
        "title": -1,
        "performer": -1,
        "date": -1,
        "info": -1,
        "originally_by": -1,
        "label": -1,
    }
    for idx, h in enumerate(ths):
        hl = h.lower()
        if "title" in hl or hl in ("song", "work", "track"):
            col_map["title"] = idx
        elif "performer" in hl or hl == "artist":
            col_map["performer"] = idx
        elif "date" in hl:
            col_map["date"] = idx
        elif "info" in hl or "feature" in hl:
            col_map["info"] = idx
        elif "originally by" in hl:
            col_map["originally_by"] = idx
        elif "label" in hl:
            col_map["label"] = idx
    return ths, col_map


def extract_row_badges(tr: Tag, is_adaptation: bool) -> Dict[str, Any]:
    badges: List[str] = []
    flags = {
        "is_instrumental": False,
        "is_live": False,
        "is_medley": False,
        "is_adaptation": is_adaptation,
        "is_first_release": False,
    }
    for span in tr.find_all(class_=re.compile(r"badge|tag|label")):
        b_txt = clean_text(span.get_text())
        if b_txt:
            badges.append(b_txt)
            bl = b_txt.lower()
            flags["is_instrumental"] |= "instrumental" in bl
            flags["is_live"] |= "live" in bl
            flags["is_medley"] |= "medley" in bl
            flags["is_adaptation"] |= "adaptation" in bl

    info_td = tr.find("td", class_=re.compile(r"field-info|field-badges"))
    if info_td:
        info_txt = clean_text(info_td.get_text(" "))
        if info_txt:
            badges.append(info_txt)
            il = info_txt.lower()
            flags["is_instrumental"] |= "instrumental" in il
            flags["is_live"] |= "live" in il
            flags["is_medley"] |= "medley" in il
            flags["is_adaptation"] |= "adaptation" in il
            if not flags["is_adaptation"] and ("first release" in il or "[1st]" in il):
                flags["is_first_release"] = True

    inst_td = tr.find("td", class_=re.compile(r"field-instrumental"))
    if inst_td and clean_text(inst_td.get_text()):
        flags["is_instrumental"] = True

    if not flags["is_adaptation"]:
        if tr.find(class_=re.compile(r"badge-original|first-release")) or "[1st]" in tr.get_text():
            flags["is_first_release"] = True

    flags["badges_raw"] = "; ".join(list(dict.fromkeys(badges)))
    return flags


def populate_row_cells(
    tds: List[Tag], col_map: Dict[str, int], r: Dict[str, Any]
) -> None:
    num_tds = len(tds)
    t_idx = (
        col_map["title"]
        if 0 <= col_map["title"] < num_tds
        else (2 if num_tds >= 4 else (1 if num_tds >= 2 else 0))
    )
    if t_idx < num_tds:
        title_td = tds[t_idx]
        r["row_title"] = clean_text(title_td.get_text())
        title_a = title_td.find("a", href=re.compile(r"/(performance|work|release)/\d+"))
        if not title_a and t_idx > 0:
            title_a = tds[0].find("a", href=re.compile(r"/(performance|work|release)/\d+"))
        if title_a:
            et, eid = extract_entity_from_url(title_a.get("href", ""))
            if et:
                r["row_entity_type"] = et
                r["row_entity_id"] = eid

    p_idx = (
        col_map["performer"]
        if 0 <= col_map["performer"] < num_tds
        else (3 if num_tds >= 4 else (2 if num_tds >= 3 else -1))
    )
    if 0 <= p_idx < num_tds:
        perf_td = tds[p_idx]
        r["row_performer"] = clean_text(perf_td.get_text())
        perf_a = perf_td.find("a", href=re.compile(r"/artist/\d+"))
        if perf_a:
            _, aid = extract_entity_from_url(perf_a.get("href", ""))
            r["row_performer_id"] = aid

    d_idx = (
        col_map["date"]
        if 0 <= col_map["date"] < num_tds
        else (4 if num_tds >= 5 else (3 if num_tds >= 4 else -1))
    )
    if 0 <= d_idx < num_tds:
        r["row_release_date"] = clean_text(tds[d_idx].get_text())
        r["row_release_year"] = sanitize_year(r["row_release_date"])

    orig_idx = col_map["originally_by"]
    if 0 <= orig_idx < num_tds:
        orig_td = tds[orig_idx]
        r["row_originally_by"] = clean_text(orig_td.get_text())
        orig_a = orig_td.find("a", href=re.compile(r"/artist/\d+"))
        if orig_a:
            _, oid = extract_entity_from_url(orig_a.get("href", ""))
            r["row_originally_by_id"] = oid

    lbl_idx = col_map["label"]
    if 0 <= lbl_idx < num_tds:
        r["row_label"] = clean_text(tds[lbl_idx].get_text())


def parse_html_table(
    table: Tag, table_idx: int, parent_meta: Dict[str, Any]
) -> List[Dict[str, Any]]:
    prev_h = table.find_previous(["h2", "h3", "h4"])
    caption = table.find("caption")
    heading = (
        clean_text(caption.get_text())
        if caption
        else (clean_text(prev_h.get_text()) if prev_h else f"Table {table_idx}")
    )
    heading_lower = heading.lower()
    table_is_adaptation = detect_table_adaptation(table, heading_lower, parent_meta)
    is_originals_section = (
        "originals" in heading_lower
        and "covers" not in heading_lower
        and "using parts" not in heading_lower
        and not table_is_adaptation
    )
    headers, col_map = map_table_headers(table)
    rows: List[Dict[str, Any]] = []
    row_ordinal = 0

    for tr in table.find_all("tr"):
        if tr.find_parent("table") is not table:
            continue
        tds = tr.find_all(["td", "th"], recursive=False)
        if not tds or (tr.find("th") and not tr.find("td")):
            continue
        row_ordinal += 1
        r: Dict[str, Any] = {k: "" for k in RELATIONAL_ROW_COLUMNS}
        r.update(parent_meta["dict_fields"])
        for pkey in (
            "source_filename",
            "page_entity_type",
            "page_entity_id",
            "page_canonical_url",
            "parent_work_title",
            "parent_work_writers",
            "parent_work_iswc",
            "parent_work_language",
            "parent_artist_name",
            "parent_release_title",
            "canonical_original_performer",
            "canonical_original_year",
        ):
            r[pkey] = parent_meta.get(pkey, "")

        r["table_section_heading"] = heading
        r["table_ordinal"] = table_idx
        r["table_row_ordinal"] = row_ordinal
        r["row_entity_type"] = "performance"

        populate_row_cells(tds, col_map, r)
        badge_info = extract_row_badges(tr, table_is_adaptation)
        r.update(badge_info)

        if not r["is_adaptation"]:
            if r["row_entity_id"] and r["row_entity_id"] in parent_meta["first_release_perf_ids"]:
                r["is_first_release"] = True
            if is_originals_section:
                r["is_first_release"] = True

        r["classification"] = classify_row_entity(r, parent_meta)
        r["performance_type_classification"] = r["classification"]
        r["composition_disambiguation_key"] = build_disambiguation_key(
            r["row_title"] or r["parent_work_title"],
            r["row_performer"] or r["parent_artist_name"],
            r["parent_work_writers"],
        )
        r["short_or_numeric_title_guard"] = is_short_or_numeric_title(
            r["row_title"] or r["parent_work_title"]
        )

        raw_cells = []
        for c_idx, cell in enumerate(tds, 1):
            c_head = headers[c_idx - 1] if c_idx - 1 < len(headers) else f"col_{c_idx}"
            c_links = [
                {"text": clean_text(a.get_text()), "href": a.get("href", "")}
                for a in cell.find_all("a", href=True)
            ]
            raw_cells.append(
                {
                    "column_ordinal": c_idx,
                    "column_heading": c_head,
                    "value": clean_text(cell.get_text()),
                    "tag": cell.name,
                    "links": c_links,
                }
            )
        r["_raw_cells"] = raw_cells

        if r["row_title"] or r["row_performer"]:
            rows.append(r)
    return rows


def harmonize_work_originals(
    meta: Dict[str, Any], table_rows: List[Dict[str, Any]]
) -> None:
    orig_perf = meta.get("canonical_original_performer", "")
    orig_yr = meta.get("canonical_original_year", "")
    for r in table_rows:
        if r["is_first_release"] and not r["is_adaptation"]:
            if not orig_perf and r["row_performer"]:
                orig_perf = r["row_performer"]
            if not orig_yr and r["row_release_year"]:
                orig_yr = r["row_release_year"]
            break

    meta["canonical_original_performer"] = orig_perf
    meta["canonical_original_year"] = orig_yr
    for r in table_rows:
        if not r["canonical_original_performer"]:
            r["canonical_original_performer"] = orig_perf or r.get("row_originally_by", "")
        if not r["canonical_original_year"]:
            r["canonical_original_year"] = orig_yr
        r["classification"] = classify_row_entity(r, meta)
        r["performance_type_classification"] = r["classification"]


def parse_single_file(filepath: Path) -> Dict[str, Any]:
    raw_bytes = filepath.read_bytes()
    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    html_str, encoding = decode_html_bytes(raw_bytes)
    soup = make_soup(html_str)
    meta = parse_page_metadata(soup, html_str, filepath)
    meta["source_sha256"] = sha256
    meta["source_byte_size"] = len(raw_bytes)
    meta["detected_encoding"] = encoding

    all_rows: List[Dict[str, Any]] = []
    tables_info: List[Dict[str, Any]] = []
    for t_idx, table in enumerate(soup.find_all("table"), 1):
        t_rows = parse_html_table(table, t_idx, meta)
        if not t_rows:
            continue
        tables_info.append(
            {
                "table_ordinal": t_idx,
                "section_heading": t_rows[0]["table_section_heading"],
                "row_count": len(t_rows),
                "rows": t_rows,
            }
        )
        all_rows.extend(t_rows)

    harmonize_work_originals(meta, all_rows)

    if not all_rows:
        page_row: Dict[str, Any] = {k: "" for k in RELATIONAL_ROW_COLUMNS}
        page_row.update(meta["dict_fields"])
        for pkey in (
            "source_filename",
            "page_entity_type",
            "page_entity_id",
            "page_canonical_url",
            "parent_work_title",
            "parent_work_writers",
            "parent_work_iswc",
            "parent_work_language",
            "parent_artist_name",
            "parent_release_title",
            "canonical_original_performer",
            "canonical_original_year",
        ):
            page_row[pkey] = meta.get(pkey, "")
        page_row["table_section_heading"] = "Page Summary"
        page_row["table_ordinal"] = 0
        page_row["table_row_ordinal"] = 0
        page_row["row_entity_type"] = meta["page_entity_type"]
        page_row["row_entity_id"] = meta["page_entity_id"]
        page_row["row_title"] = meta["preferred_name"]
        page_row["row_performer"] = meta["parent_artist_name"]
        page_row["row_release_date"] = meta["dict_fields"].get("release_date", "")
        page_row["row_release_year"] = sanitize_year(page_row["row_release_date"])
        page_row["is_first_release"] = False
        page_row["is_adaptation"] = False
        page_row["is_instrumental"] = False
        page_row["is_live"] = False
        page_row["is_medley"] = False
        page_row["classification"] = meta["page_entity_type"]
        page_row["composition_disambiguation_key"] = build_disambiguation_key(
            page_row["row_title"], page_row["row_performer"], meta["parent_work_writers"]
        )
        page_row["short_or_numeric_title_guard"] = is_short_or_numeric_title(
            page_row["row_title"]
        )
        page_row["_raw_cells"] = []
        all_rows.append(page_row)

    meta["tables_info"] = tables_info
    meta["rows"] = all_rows
    return meta


def init_sqlite_database(db_path: Path) -> sqlite3.Connection:
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE entities (
            entity_key TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            shs_id INTEGER,
            canonical_name TEXT NOT NULL,
            canonical_url TEXT,
            source_filename TEXT NOT NULL,
            iswc TEXT,
            ipi TEXT,
            country TEXT,
            birth_date TEXT,
            death_date TEXT,
            release_date TEXT,
            release_year INTEGER,
            licensing_status TEXT,
            total_covers_count INTEGER,
            canonical_original_performer TEXT,
            canonical_original_year INTEGER
        );
        CREATE TABLE page_tables (
            table_id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_key TEXT NOT NULL REFERENCES entities(entity_key),
            table_ordinal INTEGER NOT NULL,
            section_heading TEXT,
            row_count INTEGER NOT NULL
        );
        CREATE TABLE table_rows (
            row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER NOT NULL REFERENCES page_tables(table_id),
            row_ordinal INTEGER NOT NULL,
            row_entity_type TEXT NOT NULL,
            row_entity_id INTEGER,
            title TEXT NOT NULL,
            performer TEXT,
            performer_id INTEGER,
            release_date TEXT,
            release_year INTEGER,
            originally_by TEXT,
            originally_by_id INTEGER,
            label TEXT,
            is_first_release BOOLEAN NOT NULL DEFAULT 0,
            is_adaptation BOOLEAN NOT NULL DEFAULT 0,
            is_instrumental BOOLEAN NOT NULL DEFAULT 0,
            is_live BOOLEAN NOT NULL DEFAULT 0,
            is_medley BOOLEAN NOT NULL DEFAULT 0,
            badges_raw TEXT,
            classification TEXT,
            composition_disambiguation_key TEXT,
            short_or_numeric_title_guard BOOLEAN NOT NULL DEFAULT 0
        );
        CREATE TABLE entity_credits (
            credit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_key TEXT NOT NULL REFERENCES entities(entity_key),
            credit_role TEXT NOT NULL,
            credited_name TEXT NOT NULL,
            credited_artist_id INTEGER
        );
        CREATE TABLE provider_identifiers (
            identifier_id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_key TEXT NOT NULL REFERENCES entities(entity_key),
            provider_name TEXT NOT NULL,
            identifier_type TEXT NOT NULL,
            identifier_value TEXT NOT NULL,
            UNIQUE (entity_key, provider_name, identifier_value)
        );
        CREATE TABLE record_cells (
            record_cell_id INTEGER PRIMARY KEY AUTOINCREMENT,
            row_id INTEGER NOT NULL REFERENCES table_rows(row_id),
            column_ordinal INTEGER NOT NULL,
            column_heading TEXT NOT NULL,
            value_text TEXT,
            cell_tag TEXT,
            links_json TEXT
        );
        """
    )
    conn.commit()
    return conn


def to_int_or_none(val: Any) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        return int(str(val).strip())
    except ValueError:
        return None


def store_page_in_sqlite(conn: sqlite3.Connection, page_data: Dict[str, Any]) -> None:
    cur = conn.cursor()
    etype = page_data["page_entity_type"]
    eid = page_data["page_entity_id"]
    stem = Path(page_data["source_filename"]).stem
    entity_key = f"{etype}/{eid or stem}"
    df = page_data["dict_fields"]

    cur.execute(
        """
        INSERT OR REPLACE INTO entities (
            entity_key, entity_type, shs_id, canonical_name, canonical_url,
            source_filename, iswc, ipi, country, birth_date, death_date,
            release_date, release_year, licensing_status, total_covers_count,
            canonical_original_performer, canonical_original_year
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entity_key,
            etype,
            to_int_or_none(eid),
            page_data["preferred_name"] or stem,
            page_data["page_canonical_url"],
            page_data["source_filename"],
            page_data["parent_work_iswc"],
            df.get("artist_ipi", ""),
            df.get("artist_country", ""),
            df.get("artist_birth_date", ""),
            df.get("artist_death_date", ""),
            df.get("release_date", ""),
            to_int_or_none(sanitize_year(df.get("release_date", ""))),
            df.get("licensing_status", ""),
            to_int_or_none(df.get("total_covers_count", "")),
            page_data.get("canonical_original_performer", ""),
            to_int_or_none(page_data.get("canonical_original_year", "")),
        ),
    )

    for role, cname, caid in page_data.get("credits", []):
        cur.execute(
            """
            INSERT INTO entity_credits (
                entity_key, credit_role, credited_name, credited_artist_id
            ) VALUES (?, ?, ?, ?)
            """,
            (entity_key, role, cname, to_int_or_none(caid)),
        )

    for pname, ptype, pval in set(page_data.get("provider_ids", [])):
        cur.execute(
            """
            INSERT OR IGNORE INTO provider_identifiers (
                entity_key, provider_name, identifier_type, identifier_value
            ) VALUES (?, ?, ?, ?)
            """,
            (entity_key, pname, ptype, pval),
        )

    for tinfo in page_data.get("tables_info", []):
        cur.execute(
            """
            INSERT INTO page_tables (
                entity_key, table_ordinal, section_heading, row_count
            ) VALUES (?, ?, ?, ?)
            """,
            (
                entity_key,
                tinfo["table_ordinal"],
                tinfo["section_heading"],
                tinfo["row_count"],
            ),
        )
        table_id = cur.lastrowid
        for r in tinfo["rows"]:
            cur.execute(
                """
                INSERT INTO table_rows (
                    table_id, row_ordinal, row_entity_type, row_entity_id, title,
                    performer, performer_id, release_date, release_year,
                    originally_by, originally_by_id, label, is_first_release,
                    is_adaptation, is_instrumental, is_live, is_medley,
                    badges_raw, classification, composition_disambiguation_key,
                    short_or_numeric_title_guard
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    table_id,
                    r["table_row_ordinal"],
                    r["row_entity_type"],
                    to_int_or_none(r["row_entity_id"]),
                    r["row_title"],
                    r["row_performer"] or None,
                    to_int_or_none(r["row_performer_id"]),
                    r["row_release_date"] or None,
                    to_int_or_none(r["row_release_year"]),
                    r["row_originally_by"] or None,
                    to_int_or_none(r["row_originally_by_id"]),
                    r["row_label"] or None,
                    1 if r["is_first_release"] else 0,
                    1 if r["is_adaptation"] else 0,
                    1 if r["is_instrumental"] else 0,
                    1 if r["is_live"] else 0,
                    1 if r["is_medley"] else 0,
                    r["badges_raw"] or None,
                    r["classification"],
                    r["composition_disambiguation_key"],
                    1 if r["short_or_numeric_title_guard"] else 0,
                ),
            )
            row_id = cur.lastrowid
            for cell in r.get("_raw_cells", []):
                cur.execute(
                    """
                    INSERT INTO record_cells (
                        row_id, column_ordinal, column_heading, value_text,
                        cell_tag, links_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row_id,
                        cell["column_ordinal"],
                        cell["column_heading"],
                        cell["value"],
                        cell["tag"],
                        json.dumps(cell["links"], ensure_ascii=False),
                    ),
                )


def resolve_input_files(args: argparse.Namespace) -> List[Path]:
    target = args.input_file or args.input_dir or args.input
    if not target:
        default_dir = Path("SHSmetadataScrapingGuide")
        target = str(default_dir if default_dir.exists() else Path.cwd())
    src = Path(target).resolve()
    if not src.exists():
        raise FileNotFoundError(f"Input path does not exist: {src}")
    if src.is_file():
        return [src]
    return sorted(
        (
            p
            for p in src.rglob("*")
            if p.is_file()
            and p.suffix.lower() in {".html", ".htm"}
            and "output" not in p.relative_to(src).parts
        ),
        key=lambda p: p.as_posix().casefold(),
    )


def build_csv_fieldnames() -> List[str]:
    cols = list(RELATIONAL_ROW_COLUMNS)
    for f in STANDARD_85_FIELDS:
        if f not in cols:
            cols.append(f)
    return cols


def execute_pipeline(args: argparse.Namespace) -> Tuple[int, int, int]:
    html_files = resolve_input_files(args)
    out_csv_str = args.output_csv or args.output or "shs_parsed_archetypes_output.csv"
    out_csv = Path(out_csv_str).resolve()
    out_db_str = args.database or args.output_sqlite
    out_db = (
        Path(out_db_str).resolve()
        if out_db_str
        else out_csv.with_suffix(".sqlite")
    )
    excl_str = args.excluded_csv
    excl_csv = (
        Path(excl_str).resolve()
        if excl_str
        else out_csv.with_name("excluded_adaptations.csv")
    )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = build_csv_fieldnames()

    workers = max(1, int(args.workers or 1))
    if workers > 1 and len(html_files) > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            parsed_pages = list(pool.map(parse_single_file, html_files))
    else:
        parsed_pages = [parse_single_file(fp) for fp in html_files]

    conn = init_sqlite_database(out_db)
    main_rows: List[Dict[str, Any]] = []
    adaptation_rows: List[Dict[str, Any]] = []

    for page_data in parsed_pages:
        store_page_in_sqlite(conn, page_data)
        for r in page_data["rows"]:
            clean_r = {k: r.get(k, "") for k in fieldnames}
            main_rows.append(clean_r)
            if r.get("is_adaptation"):
                adaptation_rows.append(clean_r)

    conn.commit()
    conn.close()

    with out_csv.open("w", encoding="utf-8-sig", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(main_rows)

    with excl_csv.open("w", encoding="utf-8-sig", newline="") as f_excl:
        writer = csv.DictWriter(f_excl, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(adaptation_rows)

    logging.info(
        "Parsed %d HTML files -> %d relational rows (%d adaptations routed to %s). "
        "CSV: %s | SQLite: %s",
        len(parsed_pages),
        len(main_rows),
        len(adaptation_rows),
        excl_csv.name,
        out_csv.name,
        out_db.name,
    )
    return len(parsed_pages), len(main_rows), len(adaptation_rows)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Universal SecondHandSongs HTML Parser & Relational Dataset Builder"
    )
    parser.add_argument(
        "--input-dir", type=str, default=None, help="Directory containing HTML files"
    )
    parser.add_argument(
        "--input-file", type=str, default=None, help="Single HTML file to parse"
    )
    parser.add_argument(
        "--input", type=str, default=None, help="HTML file or directory path"
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default=None,
        help="Output Row-Level Relational CSV path",
    )
    parser.add_argument(
        "--output", type=str, default=None, help="Alias for --output-csv"
    )
    parser.add_argument(
        "--database",
        type=str,
        default=None,
        help="Output SQLite database file path",
    )
    parser.add_argument(
        "--output-sqlite",
        type=str,
        default=None,
        help="Alias for --database",
    )
    parser.add_argument(
        "--excluded-csv",
        type=str,
        default=None,
        help="Output CSV path for foreign adaptations (default: excluded_adaptations.csv)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=multiprocessing.cpu_count(),
        help="Number of worker processes",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    execute_pipeline(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

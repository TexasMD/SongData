import csv
import sys
import os
import time
import traceback
import unicodedata
from concurrent.futures import ThreadPoolExecutor

from ftfy import fix_text
import Levenshtein
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import musicbrainzngs

# ============================================================
# CONFIG / ENVIRONMENT
# ============================================================

DEBUG = True   # Set to False to silence console diagnostics

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

MUSICBRAINZ_USER = os.getenv("MUSICBRAINZ_USER")
MUSICBRAINZ_APP = os.getenv("MUSICBRAINZ_APP")
MUSICBRAINZ_VERSION = os.getenv("MUSICBRAINZ_VERSION")

if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    raise RuntimeError("Missing Spotify credentials in environment variables.")

if not MUSICBRAINZ_USER or not MUSICBRAINZ_APP or not MUSICBRAINZ_VERSION:
    raise RuntimeError("Missing MusicBrainz credentials in environment variables.")

# ============================================================
# DIAGNOSTICS / RETRY / PARALLEL
# ============================================================

def debug(msg):
    if DEBUG:
        print(msg)

def timed(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
        finally:
            elapsed = time.time() - start
            debug(f"[TIMING] {func.__name__} took {elapsed:.2f}s")
        return result
    return wrapper

def retry(func, retries=3, delay=1.0, backoff=2.0):
    def wrapper(*args, **kwargs):
        current_delay = delay
        for attempt in range(1, retries + 1):
            try:
                debug(f"[RETRY] Attempt {attempt}/{retries} for {func.__name__}")
                return func(*args, **kwargs)
            except Exception as e:
                debug(f"[ERROR] {func.__name__} failed: {e}")
                debug(traceback.format_exc())
                if attempt < retries:
                    debug(f"[BACKOFF] Waiting {current_delay:.1f}s before retry...")
                    time.sleep(current_delay)
                    current_delay *= backoff
                else:
                    debug(f"[FAIL] {func.__name__} exhausted retries.")
                    return None
    return wrapper

executor = ThreadPoolExecutor(max_workers=2)

def parallel_lookup(spotify_func, mb_func, title, artist, album):
    future_spotify = executor.submit(spotify_func, title, artist, album)
    future_mb = executor.submit(mb_func, title, artist, album)

    try:
        spotify_result = future_spotify.result(timeout=60)
    except Exception:
        spotify_result = None
    try:
        mb_result = future_mb.result(timeout=60)
    except Exception:
        mb_result = None

    return spotify_result, mb_result

# ============================================================
# INIT CLIENTS
# ============================================================

sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET
    )
)

musicbrainzngs.set_useragent(MUSICBRAINZ_APP, MUSICBRAINZ_VERSION, contact=MUSICBRAINZ_USER)

# ============================================================
# MOJIBAKE DETECTION / REPAIR
# ============================================================

MOJIBAKE_PATTERNS = ["Ã", "Â", "ðŸ", "ï¿½"]  # removed " "

def looks_mojibake(text: str) -> bool:
    if not text:
        return False
    return any(pat in text for pat in MOJIBAKE_PATTERNS)

def latin1_to_utf8(text: str) -> str:
    try:
        return text.encode("latin-1", errors="replace").decode("utf-8", errors="replace")
    except Exception:
        return text

# ============================================================
# SCORING
# ============================================================

def similarity(a: str, b: str) -> float:
    a = a or ""
    b = b or ""
    if not a and not b:
        return 1.0
    return Levenshtein.ratio(a, b)

def overall_score(title_score, artist_score, album_score) -> float:
    return 0.5 * artist_score + 0.3 * title_score + 0.2 * album_score

# ============================================================
# YOUTUBE-STYLE DETECTOR (Option A)
# ============================================================

def is_youtube_style(title):
    bad_tokens = ["|", "cover", "acoustic", "feat.", "/", "-"]
    return any(tok.lower() in title.lower() for tok in bad_tokens)

# ============================================================
# MUSICBRAINZ ARTIST PARSER (robust)
# ============================================================

def extract_mb_artist(rec):
    ac_list = rec.get("artist-credit", [])
    artists = []

    for ac in ac_list:
        if isinstance(ac, dict):
            if "artist" in ac and isinstance(ac["artist"], dict):
                name = ac["artist"].get("name")
                if name:
                    artists.append(name)
                    continue
            if "name" in ac:
                artists.append(ac["name"])
                continue

        if isinstance(ac, str):
            artists.append(ac)
            continue

        artists.append(str(ac))

    return ", ".join(artists)

# ============================================================
# SPOTIFY LOOKUP
# ============================================================

@timed
@retry
def spotify_lookup(title, artist, album):
    if not title and not artist:
        debug("[SPOTIFY SKIP] Empty query")
        return None

    query = f"{title} {artist}".strip()
    debug(f"[SPOTIFY] Query: {query}")

    try:
        results = sp.search(q=query, type="track", limit=3)
    except Exception as e:
        debug(f"[SPOTIFY ERROR] {e}")
        return None

    if not results["tracks"]["items"]:
        debug("[SPOTIFY] No results")
        return None

    best = None
    for item in results["tracks"]["items"]:
        cand_title = item["name"]
        cand_artist = ", ".join(a["name"] for a in item["artists"])
        cand_album = item["album"]["name"]

        t_score = similarity(title, cand_title)
        a_score = similarity(artist, cand_artist)
        al_score = similarity(album, cand_album)
        score = overall_score(t_score, a_score, al_score)

        debug(f"[SPOTIFY CANDIDATE] {cand_title} / {cand_artist} / {cand_album} (score={score:.3f})")

        if best is None or score > best["overall_score"]:
            best = {
                "title": cand_title,
                "artist": cand_artist,
                "album": cand_album,
                "title_score": t_score,
                "artist_score": a_score,
                "album_score": al_score,
                "overall_score": score,
            }

    return best

# ============================================================
# MUSICBRAINZ LOOKUP
# ============================================================

@timed
@retry
def musicbrainz_lookup(title, artist, album):
    if not title and not artist:
        debug("[MB SKIP] Empty query")
        return None

    debug(f"[MB] Query: title={title}, artist={artist}, album={album}")

    try:
        result = musicbrainzngs.search_recordings(
            recording=title,
            artist=artist,
            release=album,
            limit=3
        )
    except Exception as e:
        debug(f"[MB ERROR] {e}")
        return None

    recordings = result.get("recording-list", [])
    if not recordings:
        debug("[MB] No results")
        return None

    best = None
    for rec in recordings:
        cand_title = rec.get("title", "")
        cand_artist = extract_mb_artist(rec)

        cand_album = ""
        if "release-list" in rec and rec["release-list"]:
            cand_album = rec["release-list"][0].get("title", "")

        t_score = similarity(title, cand_title)
        a_score = similarity(artist, cand_artist)
        al_score = similarity(album, cand_album)
        score = overall_score(t_score, a_score, al_score)

        debug(f"[MB CANDIDATE] {cand_title} / {cand_artist} / {cand_album} (score={score:.3f})")

        if best is None or score > best["overall_score"]:
            best = {
                "title": cand_title,
                "artist": cand_artist,
                "album": cand_album,
                "title_score": t_score,
                "artist_score": a_score,
                "album_score": al_score,
                "overall_score": score,
            }

    return best

# ============================================================
# HEADER NORMALIZATION + BOM REMOVAL
# ============================================================

def normalize_header(header):
    normalized = []
    for col in header:
        col = col.replace("\ufeff", "")  # remove BOM
        col = col.strip()
        col = unicodedata.normalize("NFKD", col)
        col = "".join(c for c in col if not unicodedata.combining(c))
        col = col.lower()
        normalized.append(col)
    return normalized

def find_column_indices(header):
    title_synonyms = {"title", "track", "song", "name", "track name", "video title"}
    artist_synonyms = {"artist", "artists", "performer", "channel", "creator", "channel name", "artist name"}
    album_synonyms = {"album", "release", "record", "collection", "playlist name", "album name"}

    title_idx = None
    artist_idx = None
    album_idx = None

    for idx, col in enumerate(header):
        if title_idx is None and col in title_synonyms:
            title_idx = idx
        if artist_idx is None and col in artist_synonyms:
            artist_idx = idx
        if album_idx is None and col in album_synonyms:
            album_idx = idx

    if title_idx is None or artist_idx is None:
        raise RuntimeError(f"CSV must contain Title and Artist columns. Found: {header}")

    return title_idx, artist_idx, album_idx

# ============================================================
# MAIN PIPELINE
# ============================================================

def process_file(input_file, output_file=None, ambiguity_report_file=None):
    if output_file is None:
        base, ext = input_file.rsplit(".", 1)
        output_file = f"{base}_fixed.{ext}"
    if ambiguity_report_file is None:
        base, ext = input_file.rsplit(".", 1)
        ambiguity_report_file = f"{base}_ambiguity.csv"

    rows = []
    with open(input_file, "r", encoding="utf-8", errors="replace") as infile:
        reader = csv.reader(infile)
        for row in reader:
            rows.append(row)

    fixed_rows = []
    ambiguity_rows = []

    title_idx = artist_idx = album_idx = None
    ftfy_only_count = 0
    externally_repaired_count = 0
    skipped_youtube_count = 0
    ambiguous_count = 0
    total_rows = 0

    for idx, row in enumerate(rows):
        if idx == 0:
            header = normalize_header(row)

            debug(f"[HEADER RAW] {row}")
            debug(f"[HEADER NORMALIZED] {header}")

            title_idx, artist_idx, album_idx = find_column_indices(header)

            fixed_rows.append(["Title", "Artist", "Album", "Confidence", "Source Used"])
            continue

        orig_title = row[title_idx] if len(row) > title_idx else ""
        orig_artist = row[artist_idx] if len(row) > artist_idx else ""
        orig_album = row[album_idx] if album_idx is not None and len(row) > album_idx else ""

        debug(f"[ROW {idx}] Original: {orig_title} / {orig_artist} / {orig_album}")

        ftfy_title = fix_text(orig_title)
        ftfy_artist = fix_text(orig_artist)
        ftfy_album = fix_text(orig_album)

        orig_had_mojibake = (
            looks_mojibake(orig_title) or
            looks_mojibake(orig_artist) or
            looks_mojibake(orig_album)
        )

        needs_repair = (
            looks_mojibake(ftfy_title) or
            looks_mojibake(ftfy_artist) or
            looks_mojibake(ftfy_album)
        )

        latin_title = ftfy_title
        latin_artist = ftfy_artist
        latin_album = ftfy_album

        if needs_repair:
            debug(f"[ROW {idx}] Mojibake detected after ftfy; applying Latin-1→UTF-8 repair.")
            latin_title = latin1_to_utf8(ftfy_title) if looks_mojibake(ftfy_title) else ftfy_title
            latin_artist = latin1_to_utf8(ftfy_artist) if looks_mojibake(ftfy_artist) else ftfy_artist
            latin_album = latin1_to_utf8(ftfy_album) if looks_mojibake(ftfy_album) else ftfy_album

        def is_interesting(title, artist, album):
            text = f"{title} {artist} {album}"
            if not text.isascii():
                return True
            if any(sep in artist for sep in [',', '&', ' and ']):
                return True
            lower_text = text.lower()
            if any(kw in lower_text for kw in ['cover', 'remix', 'feat', 'ft.', 'live']):
                return True
            return False

        still_broken = (
            looks_mojibake(latin_title) or
            looks_mojibake(latin_artist) or
            looks_mojibake(latin_album) or
            orig_had_mojibake or
            is_interesting(latin_title, latin_artist, latin_album)
        )

        final_title = latin_title
        final_artist = latin_artist
        final_album = latin_album
        decision = "ftfy_only"

        spotify_result = None
        mb_result = None

        if still_broken:
            if is_youtube_style(latin_title):
                debug(f"[ROW {idx}] Skipping external lookup (YouTube-style title).")
                decision = "skipped_youtube_style"
            else:
                debug(f"[ROW {idx}] Still broken after Latin-1 repair; starting parallel external lookup.")
                spotify_result, mb_result = parallel_lookup(
                    spotify_lookup,
                    musicbrainz_lookup,
                    latin_title,
                    latin_artist,
                    latin_album
                )
                debug(f"[ROW {idx}] External lookup complete.")

                decision = "unresolved_no_external_match"

                if spotify_result and mb_result:
                    s = spotify_result["overall_score"]
                    m = mb_result["overall_score"]
                    artist_sim = similarity(spotify_result["artist"], mb_result["artist"])

                    debug(f"[ROW {idx}] Spotify score={s:.3f}, MB score={m:.3f}, artist_sim={artist_sim:.3f}")

                    if s >= 0.8 and m >= 0.8 and artist_sim >= 0.9:
                        final_title = spotify_result["title"]
                        final_artist = spotify_result["artist"]
                        final_album = spotify_result["album"]
                        decision = "accepted_spotify_agreed_with_mb"
                    elif s >= 0.8 or m >= 0.8:
                        decision = "ambiguous_artist_disagreement"
                    else:
                        decision = "ambiguous_low_confidence_both"

                elif spotify_result and not mb_result:
                    s = spotify_result["overall_score"]
                    debug(f"[ROW {idx}] Spotify only, score={s:.3f}")
                    if s >= 0.85:
                        final_title = spotify_result["title"]
                        final_artist = spotify_result["artist"]
                        final_album = spotify_result["album"]
                        decision = "accepted_spotify_only_high_confidence"
                    else:
                        decision = "ambiguous_spotify_low_confidence"

                elif mb_result and not spotify_result:
                    m = mb_result["overall_score"]
                    debug(f"[ROW {idx}] MB only, score={m:.3f}")
                    if m >= 0.85:
                        final_title = mb_result["title"]
                        final_artist = mb_result["artist"]
                        final_album = mb_result["album"]
                        decision = "accepted_mb_only_high_confidence"
                    else:
                        decision = "ambiguous_mb_low_confidence"

                else:
                    debug(f"[ROW {idx}] No external match found.")
                    decision = "unresolved_no_match"

                ambiguity_rows.append({
                    "row_index": idx,
                    "original_title": orig_title,
                    "original_artist": orig_artist,
                    "original_album": orig_album,
                    "ftfy_title": ftfy_title,
                    "ftfy_artist": ftfy_artist,
                    "latin1_title": latin_title,
                    "latin1_artist": latin_artist,
                    "spotify_title": spotify_result["title"] if spotify_result else "",
                    "spotify_artist": spotify_result["artist"] if spotify_result else "",
                    "spotify_album": spotify_result["album"] if spotify_result else "",
                    "spotify_title_score": spotify_result["title_score"] if spotify_result else "",
                    "spotify_artist_score": spotify_result["artist_score"] if spotify_result else "",
                    "spotify_album_score": spotify_result["album_score"] if spotify_result else "",
                    "spotify_overall_score": spotify_result["overall_score"] if spotify_result else "",
                    "mb_title": mb_result["title"] if mb_result else "",
                    "mb_artist": mb_result["artist"] if mb_result else "",
                    "mb_album": mb_result["album"] if mb_result else "",
                    "mb_title_score": mb_result["title_score"] if mb_result else "",
                    "mb_artist_score": mb_result["artist_score"] if mb_result else "",
                    "mb_album_score": mb_result["album_score"] if mb_result else "",
                    "mb_overall_score": mb_result["overall_score"] if mb_result else "",
                    "decision": decision,
                })

                confidence = "high" # Placeholder for actual logic
        if decision.startswith("accepted"): confidence = "high"
        elif decision.startswith("ambiguous"): confidence = "low"
        elif decision.startswith("skipped"): confidence = "medium"
        elif decision == "ftfy_only": confidence = "high"
        elif decision == "unresolved_no_external_match": confidence = "medium"
        elif decision == "unresolved_no_match": confidence = "low"

        source = "ftfy"
        if decision.startswith("accepted_spotify"): source = "spotify"
        elif decision.startswith("accepted_mb"): source = "musicbrainz"
        elif decision == "accepted_spotify_agreed_with_mb": source = "spotify+mb"
        elif latin_title != ftfy_title or latin_artist != ftfy_artist or latin_album != ftfy_album: source = "latin1"

        fixed_rows.append([final_title, final_artist, final_album, confidence, source])

        total_rows += 1
        if decision == "ftfy_only":
            ftfy_only_count += 1
        elif decision.startswith("accepted"):
            externally_repaired_count += 1
        elif decision == "skipped_youtube_style":
            skipped_youtube_count += 1
        elif decision.startswith("ambiguous") or decision.startswith("unresolved"):
            ambiguous_count += 1

    with open(output_file, "w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile)
        for row in fixed_rows:
            writer.writerow(row)

    with open(ambiguity_report_file, "w", encoding="utf-8", newline="") as ambfile:
        fieldnames = [
            "row_index",
            "original_title",
            "original_artist",
            "original_album",
            "ftfy_title",
            "ftfy_artist",
            "latin1_title",
            "latin1_artist",
            "spotify_title",
            "spotify_artist",
            "spotify_album",
            "spotify_title_score",
            "spotify_artist_score",
            "spotify_album_score",
            "spotify_overall_score",
            "mb_title",
            "mb_artist",
            "mb_album",
            "mb_title_score",
            "mb_artist_score",
            "mb_album_score",
            "mb_overall_score",
            "decision",
        ]
        writer = csv.DictWriter(ambfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in ambiguity_rows:
            writer.writerow(row)

    print(f"✓ Fixed file saved as: {output_file}")
    print(f"✓ Ambiguity report saved as: {ambiguity_report_file}")

    print("\n=== SUMMARY ===")
    print(f"Total rows: {total_rows}")
    print(f"Unicode-only repairs: {ftfy_only_count}")
    print(f"External metadata repairs: {externally_repaired_count}")
    print(f"Skipped YouTube-style rows: {skipped_youtube_count}")
    print(f"Ambiguous/unresolved rows: {ambiguous_count}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python safe_mojibake_pipeline.py <input.csv> [output.csv] [ambiguity.csv]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    ambiguity_file = sys.argv[3] if len(sys.argv) > 3 else None

    process_file(input_file, output_file, ambiguity_file)

import csv
import json
import time
import requests
from pathlib import Path
from urllib.parse import quote_plus

# Configuration
PROJECT_ROOT = Path(r"D:\Music\MusicDB")
ACTIVE_CSV = PROJECT_ROOT / "SongDB_v2" / "recordings.csv"
STAGING_DIR = PROJECT_ROOT / "data" / "staging" / "antigravity"

MOOD_CSV = STAGING_DIR / "mood_event_tag_suggestions.csv"
PERF_CSV = STAGING_DIR / "performance_metadata_suggestions.csv"
EXT_CSV = STAGING_DIR / "external_link_verification.csv"
STATUS_FILE = STAGING_DIR / "enrichment_status.json"

USER_AGENT = "MusicDB-Enrichment-Daemon/1.0 ( seth@example.com )"

def ensure_file_headers():
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    
    if not MOOD_CSV.exists():
        with open(MOOD_CSV, 'w', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow(["Recording ID", "Suggested Mood Tags", "Suggested Event Tags", "Suggested Situation Tags", "Source URL", "Confidence", "Notes"])
            
    if not PERF_CSV.exists():
        with open(PERF_CSV, 'w', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow(["Recording ID", "BPM", "Key", "Tuning", "Capo", "Guitar Difficulty", "Bass Difficulty", "Drum Difficulty", "Vocal Range", "Instrumentation", "Arrangement Notes", "Source URL", "Confidence", "Notes"])
            
    if not EXT_CSV.exists():
        with open(EXT_CSV, 'w', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow(["Recording ID", "Site", "Verified URL", "Search URL", "Match Type", "Confidence", "Notes"])

def get_processed_ids():
    processed = set()
    if MOOD_CSV.exists():
        with open(MOOD_CSV, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Recording ID"):
                    processed.add(row["Recording ID"])
    return processed

def write_status(current, total, last_artist, last_title):
    status = {
        "timestamp": time.time(),
        "processed": current,
        "total": total,
        "percent": round((current / total) * 100, 2) if total > 0 else 0,
        "last_processed": f"{last_artist} - {last_title}"
    }
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f, indent=2)

def fetch_musicbrainz_tags(artist, title):
    """Hits the MusicBrainz API to get tags/genres."""
    query = f"recording:\"{title}\" AND artist:\"{artist}\""
    url = f"https://musicbrainz.org/ws/2/recording?query={quote_plus(query)}&fmt=json"
    try:
        res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get("recordings"):
                rec = data["recordings"][0]
                tags = [t.get("name") for t in rec.get("tags", [])]
                return tags, f"https://musicbrainz.org/recording/{rec['id']}"
    except Exception:
        pass
    return [], "Generative Suggestion"

def run_daemon():
    print("Starting MusicDB Enrichment Daemon...")
    ensure_file_headers()
    
    # Load all targets
    targets = []
    with open(ACTIVE_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            targets.append(row)
            
    total_targets = len(targets)
    processed_ids = get_processed_ids()
    current_count = len(processed_ids)
    
    print(f"Total rows: {total_targets}. Already processed: {current_count}. Remaining: {total_targets - current_count}")
    write_status(current_count, total_targets, "None", "None")
    
    # Open files in append mode
    with open(MOOD_CSV, 'a', newline='', encoding='utf-8-sig') as f_mood, \
         open(PERF_CSV, 'a', newline='', encoding='utf-8-sig') as f_perf, \
         open(EXT_CSV, 'a', newline='', encoding='utf-8-sig') as f_ext:
         
        writer_mood = csv.writer(f_mood)
        writer_perf = csv.writer(f_perf)
        writer_ext = csv.writer(f_ext)
        
        for row in targets:
            rec_id = row.get("Recording ID")
            if rec_id in processed_ids:
                continue
                
            artist = row.get("Artist", "")
            title = row.get("Title", "")
            
            # Fetch tags
            tags, url = fetch_musicbrainz_tags(artist, title)
            # Dummy categorization for the prototype
            moods = [t for t in tags if t in ['sad', 'happy', 'chill', 'angry']]
            
            writer_mood.writerow([rec_id, ", ".join(moods), "", "", url, "Medium" if tags else "Low", "Queried from MusicBrainz"])
            
            # Performance metadata (mock generative baseline)
            writer_perf.writerow([rec_id, row.get('BPM', ''), row.get('Key', ''), "Standard", "None", "Intermediate", "Novice", "Novice", "", "Vocals, Guitar, Bass, Drums", "Standard arrangement", "Generative Suggestion", "Low", "Requires manual tuning"])
            
            # External URLs
            q = quote_plus(f"{artist} {title}")
            writer_ext.writerow([rec_id, "Ultimate Guitar", "", f"https://www.ultimate-guitar.com/search.php?search_type=title&value={q}", "Search Query", "Low", "Generated search URL"])
            writer_ext.writerow([rec_id, "SecondHandSongs", "", f"https://secondhandsongs.com/search?search_text={q}", "Search Query", "Low", "Generated search URL"])
            writer_ext.writerow([rec_id, "WhoSampled", "", f"https://www.whosampled.com/search/?q={q}", "Search Query", "Low", "Generated search URL"])
            
            # Flush immediately so progress isn't lost if killed
            f_mood.flush()
            f_perf.flush()
            f_ext.flush()
            
            current_count += 1
            if current_count % 10 == 0:
                write_status(current_count, total_targets, artist, title)
                
            # Sleep to respect rate limits (1 request per second for MusicBrainz)
            time.sleep(1.1)
            
    print("Enrichment Daemon completed its run!")
    write_status(current_count, total_targets, "DONE", "DONE")

if __name__ == "__main__":
    run_daemon()

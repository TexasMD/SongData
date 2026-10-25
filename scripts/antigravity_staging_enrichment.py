import pandas as pd
import os
import requests
import time
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

INPUT_CSV = r"D:\Music\MusicDB\SongDB_v2\recordings.csv"
STAGING_DIR = r"D:\Music\MusicDB\data\staging\antigravity"

MOOD_CSV = os.path.join(STAGING_DIR, "mood_event_tag_suggestions.csv")
PERF_CSV = os.path.join(STAGING_DIR, "performance_metadata_suggestions.csv")
EXT_CSV = os.path.join(STAGING_DIR, "external_link_verification.csv")

def scrape_lastfm_tags(artist, title):
    url = f"https://www.last.fm/music/{quote_plus(artist)}/_/{quote_plus(title)}"
    headers = {"User-Agent": "Antigravity/1.0"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            tags = [tag.text.strip() for tag in soup.select('.tags-list .tag a')]
            return tags, url
    except Exception:
        pass
    return [], url

def categorize_tags(tags):
    mood_keywords = {'sad', 'happy', 'chill', 'aggressive', 'melancholic', 'upbeat', 'dark'}
    event_keywords = {'party', 'workout', 'wedding', 'sleep', 'driving', 'study'}

    moods, events, situations = [], [], []
    for tag in tags:
        t = tag.lower()
        if t in mood_keywords: moods.append(t)
        elif t in event_keywords: events.append(t)
        else: situations.append(t)
    return moods[:3], events[:2], situations[:3]

def enrich_sample():
    print("Loading recordings.csv...")
    df = pd.read_csv(INPUT_CSV, encoding='utf-8-sig', dtype=str)

    # Take a small sample of 20 tracks (skip the first few if they are weird, let's just take head(20))
    sample_df = df.head(20)

    mood_rows = []
    perf_rows = []
    ext_rows = []

    print(f"Processing {len(sample_df)} tracks for staging enrichment...")
    for idx, row in sample_df.iterrows():
        rec_id = row.get('Recording ID', '')
        title = row.get('Title', '')
        artist = row.get('Artist', '')

        print(f"  -> Enriching: {artist} - {title}")

        # 1. Mood/Event/Situation Tags
        tags, lfm_url = scrape_lastfm_tags(artist, title)
        moods, events, situations = categorize_tags(tags)

        mood_conf = "Medium" if tags else "Low"
        mood_notes = "Extracted from Last.fm tags" if tags else "No tags found on Last.fm"

        mood_rows.append({
            "Recording ID": rec_id,
            "Suggested Mood Tags": ", ".join(moods),
            "Suggested Event Tags": ", ".join(events),
            "Suggested Situation Tags": ", ".join(situations),
            "Source URL": lfm_url,
            "Confidence": mood_conf,
            "Notes": mood_notes
        })

        # 2. Performance Metadata
        # We will mock Chosic/AcousticBrainz for this sample since we don't have API keys/full access here
        # We will set confidence to Low to indicate it's a generated search/suggestion
        perf_rows.append({
            "Recording ID": rec_id,
            "BPM": row.get('BPM', ''),
            "Key": row.get('Key', ''),
            "Tuning": "Standard",
            "Capo": "None",
            "Guitar Difficulty": "Intermediate",
            "Bass Difficulty": "Novice",
            "Drum Difficulty": "Novice",
            "Vocal Range": "",
            "Instrumentation": "Vocals, Guitar, Bass, Drums",
            "Arrangement Notes": "Standard rock/pop arrangement",
            "Source URL": "Generative Suggestion",
            "Confidence": "Low",
            "Notes": "Auto-filled standard defaults; requires manual tuning verification."
        })

        # 3. External Links
        q = quote_plus(f"{artist} {title}")

        # UG
        ug_search = f"https://www.ultimate-guitar.com/search.php?search_type=title&value={q}"
        ext_rows.append({
            "Recording ID": rec_id,
            "Site": "Ultimate Guitar",
            "Verified URL": "",  # Empty until manually verified or deeply scraped
            "Search URL": ug_search,
            "Match Type": "Search Query",
            "Confidence": "Low",
            "Notes": "Prefer Official Tab, fallback to highest rated."
        })

        # SecondHandSongs
        shs_search = f"https://secondhandsongs.com/search?search_text={q}"
        ext_rows.append({
            "Recording ID": rec_id,
            "Site": "SecondHandSongs",
            "Verified URL": "",
            "Search URL": shs_search,
            "Match Type": "Search Query",
            "Confidence": "Low",
            "Notes": "Requires exact title/artist match."
        })

        # WhoSampled
        ws_search = f"https://www.whosampled.com/search/?q={q}"
        ext_rows.append({
            "Recording ID": rec_id,
            "Site": "WhoSampled",
            "Verified URL": "",
            "Search URL": ws_search,
            "Match Type": "Search Query",
            "Confidence": "Low",
            "Notes": "Requires exact title/artist match."
        })

        time.sleep(1) # Be nice to Last.fm

    # Save to staging
    pd.DataFrame(mood_rows).to_csv(MOOD_CSV, index=False, encoding='utf-8-sig')
    pd.DataFrame(perf_rows).to_csv(PERF_CSV, index=False, encoding='utf-8-sig')
    pd.DataFrame(ext_rows).to_csv(EXT_CSV, index=False, encoding='utf-8-sig')

    print("Staging CSVs generated successfully!")

if __name__ == "__main__":
    enrich_sample()

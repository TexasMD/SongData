import time
import random
import requests
import logging
import re
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

USER_AGENT = "MusicDB_Bot/1.0 ( antigravity@example.com )"

BROWSER_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0"
]

def get_random_headers():
    return {
        "User-Agent": random.choice(BROWSER_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
    }

def fetch_work_id_for_recording(title: str, artist: str) -> str:
    """Finds the MusicBrainz Work ID for a given title and artist."""
    url = "https://musicbrainz.org/ws/2/recording/"
    params = {
        "query": f'recording:"{title}" AND artist:"{artist}"',
        "fmt": "json",
    }
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
            
        data = resp.json()
        recordings = data.get("recordings", [])
        if not recordings:
            return None
            
        # Get the first recording's work relations
        rec_id = recordings[0]["id"]
        time.sleep(1.1)  # Respect rate limit
        
        lookup_url = f"https://musicbrainz.org/ws/2/recording/{rec_id}"
        lookup_params = {"inc": "work-rels", "fmt": "json"}
        lookup_resp = requests.get(lookup_url, params=lookup_params, headers=headers, timeout=10)
        
        if lookup_resp.status_code == 200:
            rec_data = lookup_resp.json()
            relations = rec_data.get("relations", [])
            for rel in relations:
                if rel.get("target-type") == "work" and rel.get("work"):
                    return rel["work"]["id"]
    except Exception as e:
        logger.error(f"Error fetching work ID: {e}")
        
    return None

def fetch_covers_for_work(work_id: str, original_artist: str) -> list:
    """Fetches covers (recordings) for a given Work ID."""
    url = "https://musicbrainz.org/ws/2/recording"
    params = {
        "work": work_id,
        "inc": "artists",
        "fmt": "json",
        "limit": 100
    }
    headers = {"User-Agent": USER_AGENT}
    covers = []
    try:
        time.sleep(1.1)
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            recordings = data.get("recordings", [])
            for rec in recordings:
                title = rec.get("title")
                mbid = rec.get("id")
                artist_credit = rec.get("artist-credit", [])
                artist_name = artist_credit[0].get("name", "Unknown") if artist_credit else "Unknown"
                
                if artist_name.lower() != original_artist.lower():
                    covers.append({
                        "title": title,
                        "artist": artist_name,
                        "musicbrainz_recording_id": mbid,
                        "cover_song": "Yes",
                        "source": "MusicBrainz"
                    })
    except Exception as e:
        logger.error(f"Error fetching covers for work {work_id}: {e}")
        
    return covers

def scrape_secondhandsongs(title: str, artist: str) -> list:
    """Scrapes SecondHandSongs using search."""
    covers = []
    try:
        # Politeness delay
        time.sleep(random.uniform(1.0, 2.5))
        url = f"https://secondhandsongs.com/search/performance?op_title=contains&title={quote_plus(title)}"
        headers = get_random_headers()
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            # Broad regex to match typical table row structure for performances
            matches = re.finditer(r'<a[^>]+href="/performance/[^>]+>([^<]+)</a>.*?<a[^>]+href="/artist/[^>]+>([^<]+)</a>', resp.text, re.IGNORECASE | re.DOTALL)
            for m in matches:
                c_title = m.group(1).strip()
                c_artist = m.group(2).strip()
                if c_artist.lower() != artist.lower():
                    covers.append({
                        "title": c_title,
                        "artist": c_artist,
                        "musicbrainz_recording_id": None,
                        "cover_song": "Yes",
                        "source": "SecondHandSongs"
                    })
    except Exception as e:
        logger.error(f"SHS scrape error: {e}")
    return covers

def scrape_whosampled(title: str, artist: str) -> list:
    """Scrapes WhoSampled using a delayed, browser-mimicking approach."""
    covers = []
    try:
        # Crucial Initial delay as requested by user
        time.sleep(random.uniform(2.5, 6.5))
        
        search_url = f"https://www.whosampled.com/search/tracks/?q={quote_plus(title + ' ' + artist)}"
        headers = get_random_headers()
        session = requests.Session()
        session.headers.update(headers)
        
        search_resp = session.get(search_url, timeout=15)
        if search_resp.status_code != 200:
            return covers
            
        # Extract track URL from search results
        match = re.search(r'<a[^>]+href="([^"]+)"[^>]*class="trackName[^"]*"', search_resp.text)
        if not match:
            return covers
            
        track_path = match.group(1) 
        
        # Add random delay before navigating to covers page
        time.sleep(random.uniform(3.5, 7.5))
        
        covers_url = f"https://www.whosampled.com{track_path}Covered/"
        covers_resp = session.get(covers_url, timeout=15)
        
        if covers_resp.status_code == 200:
            # Extract covers
            track_matches = re.finditer(r'class="trackName[^"]*">([^<]+)</a>.*?class="trackArtist[^"]*">\s*(?:<a[^>]*>)?([^<]+)(?:</a>)?', covers_resp.text, re.IGNORECASE | re.DOTALL)
            
            for m in track_matches:
                c_title = m.group(1).strip()
                c_artist = m.group(2).strip()
                if c_artist.lower() != artist.lower():
                    covers.append({
                        "title": c_title,
                        "artist": c_artist,
                        "musicbrainz_recording_id": None,
                        "cover_song": "Yes",
                        "source": "WhoSampled"
                    })
    except Exception as e:
        logger.error(f"WhoSampled scrape error: {e}")
        
    return covers

def scrape_covers(title: str, artist: str) -> list:
    """End-to-end function to scrape cover songs from all sources and deduplicate."""
    covers = []
    
    # 1. MusicBrainz
    work_id = fetch_work_id_for_recording(title, artist)
    if work_id:
        covers.extend(fetch_covers_for_work(work_id, artist))
        
    # 2. SecondHandSongs
    covers.extend(scrape_secondhandsongs(title, artist))
    
    # 3. WhoSampled
    covers.extend(scrape_whosampled(title, artist))
    
    # Deduplicate based on title and artist
    unique_covers = {}
    for cover in covers:
        key = f"{cover['title'].lower()}|{cover['artist'].lower()}"
        if key not in unique_covers:
            unique_covers[key] = cover
        else:
            # Merge sources if not already included
            existing_source = unique_covers[key].get("source", "")
            new_source = cover.get("source", "")
            if new_source and new_source not in existing_source:
                unique_covers[key]["source"] = f"{existing_source}, {new_source}"
                
            # Retain MBID if one has it and the other doesn't
            if cover.get("musicbrainz_recording_id") and not unique_covers[key].get("musicbrainz_recording_id"):
                unique_covers[key]["musicbrainz_recording_id"] = cover["musicbrainz_recording_id"]
                
    return list(unique_covers.values())

if __name__ == "__main__":
    # Test script
    print("Testing scrape_covers with Hallelujah by Leonard Cohen...")
    res = scrape_covers("Hallelujah", "Leonard Cohen")
    print(f"Found {len(res)} unique covers:")
    for c in res[:5]:
        print(f"- {c['title']} by {c['artist']} ({c.get('source')})")

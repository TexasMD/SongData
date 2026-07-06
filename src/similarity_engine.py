import sqlite3
from typing import Dict, List, Any

# Map of major keys to their relative minor keys
RELATIVE_KEYS = {
    "C": "Am", "Am": "C",
    "C#": "A#m", "A#m": "C#",
    "Db": "Bbm", "Bbm": "Db",
    "D": "Bm", "Bm": "D",
    "D#": "Cm", "Cm": "D#",
    "Eb": "Cm",
    "E": "C#m", "C#m": "E",
    "F": "Dm", "Dm": "F",
    "F#": "D#m", "D#m": "F#",
    "Gb": "Ebm", "Ebm": "Gb",
    "G": "Em", "Em": "G",
    "G#": "Fm", "Fm": "G#",
    "Ab": "Fm",
    "A": "F#m", "F#m": "A",
    "A#": "Gm", "Gm": "A#",
    "Bb": "Gm",
    "B": "G#m", "G#m": "B"
}

def parse_tags(tag_string: str) -> set[str]:
    """Parse a comma-separated tag string into a set of lowercased tags."""
    if not tag_string:
        return set()
    return {t.strip().lower() for t in tag_string.split(",") if t.strip()}

def compute_bpm_score(target_bpm: float, candidate_bpm: float) -> float:
    """Compute score based on BPM difference. Max 10 points for exact match, 0 if diff > 15."""
    if not target_bpm or not candidate_bpm:
        return 0.0
    diff = abs(target_bpm - candidate_bpm)
    if diff > 15:
        return 0.0
    return max(0.0, 10.0 * (1.0 - (diff / 15.0)))

def compute_key_score(target_key: str, candidate_key: str) -> float:
    """Compute score based on musical key match."""
    if not target_key or not candidate_key:
        return 0.0
    
    t_key = target_key.strip()
    c_key = candidate_key.strip()
    
    if t_key == c_key:
        return 5.0
    
    # Check relative keys
    if RELATIVE_KEYS.get(t_key) == c_key:
        return 3.0
        
    return 0.0

def compute_tag_overlap_score(target_tags: set[str], candidate_tags: set[str]) -> float:
    """Compute Jaccard similarity of tags, mapped to a 10 point scale."""
    if not target_tags or not candidate_tags:
        return 0.0
    
    intersection = len(target_tags.intersection(candidate_tags))
    union = len(target_tags.union(candidate_tags))
    
    if union == 0:
        return 0.0
        
    return 10.0 * (intersection / union)

def find_similar_recordings(
    target_id: str, 
    db_path: str, 
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Find songs mathematically similar to the target recording.
    Matches based on BPM proximity, Key relationship, Genre match, and Tag overlap.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Fetch target
    cursor.execute("""
        SELECT r.recording_id, r.title, r.artist, r.bpm, r.key, r.genre, 
               s.suggested_mood_tags, s.suggested_event_tags, s.suggested_situation_tags
        FROM recordings r
        LEFT JOIN antigravity_mood_event_suggestions s ON r.recording_id = s.recording_id
        WHERE r.recording_id = ?
    """, (target_id,))
    
    target_row = cursor.fetchone()
    if not target_row:
        conn.close()
        raise ValueError(f"Recording ID {target_id} not found in database.")
        
    target_bpm = target_row['bpm']
    target_key = target_row['key']
    target_genre = target_row['genre']
    
    target_tags = set()
    for tag_col in ['suggested_mood_tags', 'suggested_event_tags', 'suggested_situation_tags']:
        if target_row[tag_col]:
            target_tags.update(parse_tags(target_row[tag_col]))
            
    # Fetch all other candidates
    cursor.execute("""
        SELECT r.recording_id, r.title, r.artist, r.bpm, r.key, r.genre, 
               s.suggested_mood_tags, s.suggested_event_tags, s.suggested_situation_tags
        FROM recordings r
        LEFT JOIN antigravity_mood_event_suggestions s ON r.recording_id = s.recording_id
        WHERE r.recording_id != ?
    """, (target_id,))
    
    candidates = cursor.fetchall()
    conn.close()
    
    results = []
    
    for row in candidates:
        candidate_bpm = row['bpm']
        candidate_key = row['key']
        candidate_genre = row['genre']
        
        candidate_tags = set()
        for tag_col in ['suggested_mood_tags', 'suggested_event_tags', 'suggested_situation_tags']:
            if row[tag_col]:
                candidate_tags.update(parse_tags(row[tag_col]))
                
        # Calculate scores
        bpm_score = compute_bpm_score(target_bpm, candidate_bpm) if target_bpm else 0.0
        key_score = compute_key_score(target_key, candidate_key)
        genre_score = 5.0 if (target_genre and candidate_genre and target_genre.lower() == candidate_genre.lower()) else 0.0
        tag_score = compute_tag_overlap_score(target_tags, candidate_tags)
        
        total_score = bpm_score + key_score + genre_score + tag_score
        
        # Only include if there's some meaningful similarity
        if total_score > 3.0:
            results.append({
                "recording_id": row['recording_id'],
                "title": row['title'],
                "artist": row['artist'],
                "bpm": candidate_bpm,
                "key": candidate_key,
                "genre": candidate_genre,
                "similarity_score": round(total_score, 2),
                "score_breakdown": {
                    "bpm": round(bpm_score, 2),
                    "key": round(key_score, 2),
                    "genre": genre_score,
                    "tags": round(tag_score, 2)
                }
            })
            
    # Sort by total score descending
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    return results[:limit]

if __name__ == "__main__":
    # Simple self-test
    import sys
    from pathlib import Path
    
    db_path = Path(__file__).resolve().parents[2] / "data" / "staging" / "jules" / "music_antigravity_review.sqlite"
    if db_path.exists() and len(sys.argv) > 1:
        test_id = sys.argv[1]
        print(f"Finding similar tracks for {test_id}...")
        results = find_similar_recordings(test_id, str(db_path))
        for i, r in enumerate(results):
            print(f"{i+1}. {r['artist']} - {r['title']} (Score: {r['similarity_score']})")

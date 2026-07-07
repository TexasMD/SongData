from typing import List, Dict, Any

def calculate_similarity(target_song: Dict[str, Any], candidate_songs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculates similarity scores between a target song and a list of candidates.
    Returns candidates sorted by score descending, with reason columns.
    """
    scored_candidates = []

    target_bpm = target_song.get("bpm")
    target_key = target_song.get("key")
    target_artist = target_song.get("artist")
    target_playlists = set(str(target_song.get("playlists", "")).split(";")) if target_song.get("playlists") else set()

    for cand in candidate_songs:
        if cand.get("recording_id") == target_song.get("recording_id"):
            continue

        score = 0.0
        reasons = []

        # 1. BPM Similarity (Weight: 30)
        cand_bpm = cand.get("bpm")
        if target_bpm and cand_bpm:
            bpm_diff = abs(float(target_bpm) - float(cand_bpm))
            if bpm_diff <= 5:
                score += 30
                reasons.append("Close BPM")
            elif bpm_diff <= 10:
                score += 15
                reasons.append("Similar BPM")

        # 2. Key Similarity (Weight: 20) - Simple exact match for now
        cand_key = cand.get("key")
        if target_key and cand_key and target_key == cand_key:
            score += 20
            reasons.append("Same Key")

        # 3. Artist Similarity (Weight: 25)
        cand_artist = cand.get("artist")
        if target_artist and cand_artist and target_artist == cand_artist:
            score += 25
            reasons.append("Same Artist")

        # 4. Playlist/Tag Similarity (Weight: 25)
        cand_playlists = set(str(cand.get("playlists", "")).split(";")) if cand.get("playlists") else set()
        common_playlists = target_playlists.intersection(cand_playlists)
        if common_playlists:
            # Jaccard-ish
            p_score = (len(common_playlists) / len(target_playlists.union(cand_playlists))) * 25
            score += p_score
            reasons.append(f"Shared Playlists: {', '.join(common_playlists)}")

        if score > 0:
            cand_result = cand.copy()
            cand_result["similarity_score"] = round(score, 2)
            cand_result["reasons"] = "; ".join(reasons)
            scored_candidates.append(cand_result)

    return sorted(scored_candidates, key=lambda x: x["similarity_score"], reverse=True)

import os
from datetime import datetime

def generate_handoff():
    handoff_path = "docs/song_analysis_handoff.md"

    content = f"""# Song Analysis Handoff

Status: ready_for_review
Owner: Antigravity
Inputs: songlist.txt
Outputs: data/staging/antigravity/song_analysis.json (planned)
Counts: 135 rows
Safety: No active DB modifications.
Validation: N/A - Analysis handoff.
Blocked/Questions: None
Next: Antigravity to review and structure into JSON format.

## Overview
This document hands off the analysis of the provided `songlist.txt` to Antigravity for further structured enrichment. The goal is to categorize these songs based on common musical characteristics.

## Reasoning for Grouping Categories
To effectively analyze and group the songs, we employ a multidimensional approach based on standard music information retrieval (MIR) practices and musicology.

*   **Genre:** Grouping by genre (e.g., Alternative Rock, Post-Punk, Trip-Hop, New Wave) provides the most immediate macro-level categorization. It defines the foundational stylistic elements and historical context. Source: Standard musicological classification systems (e.g., AllMusic taxonomy).
*   **Mood:** Capturing the emotional resonance (e.g., Melancholic, Euphoric, Dark, Introspective) is crucial as it dictates the psychological impact of the music. This aligns with psychological models of music perception (e.g., Russell's circumplex model of affect).
*   **Aggressiveness (Energy/Valence):** This metric differentiates between high-energy, distorted tracks (e.g., TOOL, Nine Inch Nails) and softer, acoustic pieces. It maps to the 'energy' metric commonly used in music recommendation systems (like Spotify's API).
*   **Tempo:** The BPM (beats per minute) significantly influences the track's feel, categorizing them into downtempo/ballads versus upbeat/danceable tracks.
*   **Lyrics:** The thematic content of the lyrics (e.g., existential angst, love, social commentary) connects songs thematically, regardless of genre.
*   **Instruments:** Identifying key instrumentation (e.g., heavy distorted guitars, synthesizers, acoustic guitar, string arrangements) provides a sonic fingerprint for grouping similar-sounding tracks.

## Preliminary Analysis / Commonalities

Based on the provided list, several strong clusters emerge:

1.  **90s Alternative & Grunge:** (Pearl Jam, Soundgarden, Smashing Pumpkins, Alice In Chains). Characterized by high aggressiveness, distorted guitars, mid-tempo, and often introspective or angsty lyrics. (Sources: *AllMusic Genre Profiles: Grunge*, *Spotify Audio Features API documentation for Energy & Tempo characteristics of Alternative Rock*)
2.  **Post-Punk & New Wave:** (The Cure, Joy Division/New Order, Siouxsie And The Banshees, Depeche Mode). Characterized by prominent synthesizers, driving basslines, often darker or more melancholic moods, and danceable tempos. (Sources: *Reynolds, Simon. "Rip It Up and Start Again: Postpunk 1978-1984"*, *Discogs Genre/Style database definitions*)
3.  **Trip-Hop & Downtempo:** (Massive Attack, Portishead, Tricky, Sneaker Pimps). Characterized by slow tempos, heavy bass, breakbeats, atmospheric/moody synths, and often female vocals. Very specific sonic palette. (Sources: *MusicBrainz Tag taxonomy*, *RateYourMusic Genre descriptions for Trip Hop*)
4.  **Classic/Arena Rock:** (U2, The Police, Peter Gabriel). Characterized by anthemic qualities, prominent vocals, varied tempos, and sophisticated pop-rock instrumentation. (Sources: *AllMusic Genre Profiles: Arena Rock*, *Billboard chart histories establishing pop-rock crossover appeal*)
5.  **Industrial/Alternative Metal:** (Nine Inch Nails, TOOL, Deftones). Characterized by extreme aggressiveness, complex time signatures (especially TOOL), heavy electronic elements mixed with distorted guitars, and dark moods. (Sources: *Spotify Audio Features API (Energy/Valence distributions)*, *Metal Archives (Encyclopaedia Metallum) subgenre definitions*)

## Next Steps for Antigravity

1.  Review this preliminary analysis.
2.  Process the `songlist.txt` and generate a structured dataset (e.g., JSON or CSV) in `data/staging/antigravity/` mapping each song to specific tags across these categories.
3.  Provide a summary report of the structured data.
"""
    with open(handoff_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Handoff document generated at {handoff_path}")

if __name__ == "__main__":
    generate_handoff()

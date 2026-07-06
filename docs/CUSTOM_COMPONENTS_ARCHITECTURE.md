# MusicDB Custom Components Architecture

This document proposes the technical architecture for the "Find Similar" and "Conversational Search" features of the MusicDB interface.

## 1. "Find Similar" Component

The similarity engine uses a multi-factor weighting system to rank songs relative to a reference track.

### Vector Representation
Each song is represented as a feature vector:
`V = [Normalized_BPM, Key_Ordinal, Energy, Mood_Vector, Event_Vector]`

### Distance Metric
We use a weighted Euclidean distance:
`Distance = sqrt( w1*(ΔBPM)^2 + w2*(ΔKey)^2 + w3*(ΔEnergy)^2 + w4*(TagDifference) )`

- **ΔBPM**: Percentage difference (to handle high vs. low BPM fairly).
- **ΔKey**: Distance on the Circle of Fifths (0 to 6).
- **TagDifference**: Hamming distance (count of mismatched tags) between mood/event lists.

### SQL Implementation (SQLite)
While complex math is better done in Python, a first-pass "Similar BPM" can be done in raw SQL:
```sql
SELECT *, abs(BPM - :target_bpm) as bpm_diff
FROM songs
ORDER BY bpm_diff ASC
LIMIT 20;
```

---

## 2. Conversational Search (NLP) Component

This component translates natural language into structured database filters.

### Option A: Heuristic Mapping (Fast & Private)
A keyword-based mapper for common terms:
- "chill", "relaxing", "mellow" -> `Energy <= 3` AND `Mood IN ('Melancholic', 'Calm')`
- "hype", "banger", "party" -> `Energy >= 8` AND `Situation = 'Club'`

### Option B: LLM Text-to-SQL (Powerful & Flexible)
Using a Small Language Model (SLM) or OpenAI API:
1. **Prompt**: "Convert this music request to a SQL WHERE clause: 'I want some upbeat 80s synth pop for a workout'"
2. **Context**: Provide the database schema and a list of valid Tag values.
3. **Execution**: Validate the generated SQL for safety (SELECT only) and run it against the SQLite database.

---

## 3. Data Flow in Streamlit Interface

1. **User Interaction**: User selects a row or types a query.
2. **Logic Engine**:
   - If **Similarity**: Python calculates distances and adds a "Similarity Score" column.
   - If **NLP**: LLM generates a SQL snippet; Python joins it with the base query.
3. **View Update**: The AG-Grid re-renders with the filtered/sorted results.
4. **Refinement**: User can further use Excel-style filters on top of the algorithm's results.

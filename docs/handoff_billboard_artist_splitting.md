# Billboard Artist Splitting Handoff

This document is designed for human maintainers and AI orchestrators (e.g., Jules) regarding the processing of Billboard artist arrays, specifically splitting combined collaboration strings into separate distinct musical entities.

---

## 1. The Core Problem

Billboard charting credits often mash multiple distinct artists together using delimiters like `&`, `and`, `,`, `X`, `/`.
For example: `"21 Savage & Metro Boomin"`

However, many *single* distinct bands/groups naturally contain these exact same delimiters in their official name.
For example: `"Earth, Wind & Fire"` or `"AC/DC"`

A naive split on `&` or `and` causes severe data corruption, shattering "Earth, Wind & Fire" into three distinct entities ("Earth", "Wind", "Fire").

## 2. The Solution: `scripts/split_billboard_artists.py`

This script uses targeted substitution heuristics to safely process and expand the array.

### Heuristic Logic

1.  **Tag Stripping:** Strips out errant HTML tags frequently found in raw Billboard exports (e.g., `<a href="...">`).
2.  **Explicit Protection Map:** Contains a hardcoded list of `protected_bands` (e.g., "Simon & Garfunkel", "Kool & The Gang").
3.  **Substitution Phasing:**
    *   Before performing any string splitting, the script searches the target string for any of the protected bands.
    *   If found, it temporarily replaces the entire protected band name with a placeholder like `__PROTECTED_0__`. This is vital for complex strings like `"Earth, Wind & Fire & Santana"`.
4.  **Delimiter Splitting:** The string is then split via Regex on standard delimiters (` \& | and | \/ | x | X |\, | Or `).
5.  **Restoration:** The placeholders (`__PROTECTED_0__`) are restored to their original protected band names.
6.  **Backing Band Logic:** Checks if the final trailing element of a split ends with a known backing band identifier ("His Orchestra", "The Blackhearts", etc.). If it does, and there are only two elements, it assumes it's one act and recombines them.

### Data Expansion

The script leverages pandas to read an input CSV.
1.  For each row containing an `artist_name`, it runs the heuristic list generator.
2.  It creates a *new row* for every distinct artist returned, duplicating the original row's attributes (like IDs or confidence scores) so no data is lost.
3.  It performs a `.drop_duplicates()` across all columns ensuring the final output is entirely unique.

## 3. Usage for AI

When executing this script in automated pipelines, use the `argparse` flags:

```bash
python3 scripts/split_billboard_artists.py -i /path/to/input.csv -o /path/to/output.csv
```

**Required Input Structure:**
The input CSV *must* contain a column named `artist_name`.

**Output Structure:**
The script guarantees outputting `artist_dictionary_id`, `original_artist_name` (the pre-split string), `artist_name` (the clean extracted entity), `artist_split_status`, and `suggested_action`.

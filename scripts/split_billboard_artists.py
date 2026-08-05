import pandas as pd
import argparse
import re
from pathlib import Path
from typing import List

def split_artist_name(name: str) -> List[str]:
    # Handle NaN/float from pandas if the field was empty
    if not isinstance(name, str):
        if pd.isna(name) or name is None:
            return [""]
        name = str(name)

    # Remove HTML tags if present (like the weird billboard link)
    name = re.sub(r'<[^>]+>', '', name).strip()

    # Check for some common specific known bad formats and fix them
    if name == 'Lil Nas X & Cardi B Or Nas':
        return ['Lil Nas X', 'Cardi B', 'Nas']

    # Common band names with ampersands/ands to protect
    protected_bands = [
        "10,000 Maniacs", "2 Hyped Brothers & A Dog", "5 Stairsteps and Cubie",
        "A Great Big World", "AC/DC", "Alive & Kicking", "Alton McClain & Destiny",
        "Alvin And The Chipmunks", "Alvin Cash & The Crawlers", "Alvin Cash & The Registers",
        "Aly & AJ", "Andre Williams & His Orch.", "Angels & Airwaves",
        "Anita & Th' So-And-So's", "Anthony & The Imperials", "Archie Bell & The Drells",
        "Art Mooney And His Orchestra", "Earth, Wind & Fire", "Simon & Garfunkel",
        "Kool & The Gang", "Sly & The Family Stone", "Mumford & Sons",
        "Captain & Tennille", "Florence + The Machine", "Hootie & The Blowfish",
        "Peter, Paul & Mary", "Peter, Paul And Mary", "Crosby, Stills, Nash & Young",
        "Crosby, Stills & Nash", "Emerson, Lake & Palmer", "Blood, Sweat & Tears",
        "Boyz II Men", "KC & The Sunshine Band", "Katrina & The Waves",
        "Peaches & Herb", "Tears For Fears", "Hall & Oates",
        "Ashford & Simpson", "Seals & Crofts",
        "Sonny & Cher", "Ike & Tina Turner", "Loggins & Messina",
        "Womack & Womack", "Marilyn McCoo & Billy Davis Jr.",
        "Sam & Dave", "Chad & Jeremy", "Peter & Gordon",
        "England Dan & John Ford Coley", "McFadden & Whitehead",
        "James & Bobby Purify", "Mickey & Sylvia", "Mac & Katie Kissoon",
        "Donnie & Joe Emerson", "Jan & Dean", "Zager & Evans",
        "Bell Biv DeVoe", "Tony! Toni! Tone!",
        "Tony Orlando & Dawn", "Mitch Ryder & The Detroit Wheels",
        "Tommy James & The Shondells", "Gary Puckett & The Union Gap",
        "Paul Revere & The Raiders", "Joan Jett & The Blackhearts",
        "Bob Marley & The Wailers", "Tom Petty & The Heartbreakers",
        "Bruce Springsteen & The E Street Band", "Prince & The Revolution",
        "Prince & The New Power Generation"
    ]

    # Pre-process name to replace protected bands with a placeholder
    protected_map = {}
    for i, band in enumerate(protected_bands):
        # Case insensitive exact word match boundary replacement
        pattern = re.compile(re.escape(band), re.IGNORECASE)
        # Only replace if the match is the full string or surrounded by delimiters

        matches = list(pattern.finditer(name))
        for match in reversed(matches): # Reverse so indices don't shift
            placeholder = f"__PROTECTED_{i}__"
            protected_map[placeholder] = match.group(0) # Keep original capitalization
            name = name[:match.start()] + placeholder + name[match.end():]

    # Split on " & ", " and ", " / ", " x ", " X ", ", ", " Or "
    delimiters = r'(?: \& | and | \/ | x | X |\, | Or )'
    parts = re.split(delimiters, name)

    # Trim parts and remove empty strings or quotes
    parts = [p.strip().strip('"').strip("'") for p in parts if p.strip()]

    # Restore protected bands
    restored_parts = []
    for part in parts:
        for placeholder, original in protected_map.items():
            if placeholder in part:
                part = part.replace(placeholder, original)
        restored_parts.append(part)

    parts = restored_parts

    if len(parts) > 1:
        # Check if the parts look like distinct artists (e.g., not "His Orchestra" or "The Imperials")
        # If the last part is "His Orchestra", "The X", "The Y", etc., it might be one act
        last_part = parts[-1].lower()
        if re.match(r'^(his |her |the ).*', last_part) or last_part in ['band', 'orchestra', 'chorus', 'choir', 'group']:
            # Recombine just the last part to the second-to-last part
            if len(parts) >= 2:
                parts[-2] = f"{parts[-2]} and {parts[-1]}"
                parts.pop()

    return parts

def process_file(input_path: Path, output_path: Path):
    print(f"Reading {input_path}...")
    df = pd.read_csv(input_path)

    all_parsed_artists = []

    if 'artist_name' not in df.columns:
        raise ValueError("Input CSV must contain an 'artist_name' column")

    for index, row in df.iterrows():
        name = row['artist_name']
        # Remove surrounding quotes from CSV string itself if any
        if isinstance(name, str):
             name = name.strip()
             if name.startswith('"""') and name.endswith('"""'):
                 name = name[3:-3]
             elif name.startswith('"') and name.endswith('"'):
                 name = name[1:-1]

        parsed = split_artist_name(name)
        all_parsed_artists.append(parsed)

    df['parsed_artists'] = all_parsed_artists

    # Expand the list of artists into multiple rows
    print("Expanding lists into individual rows...")
    expanded_rows = []
    for index, row in df.iterrows():
        parsed = row['parsed_artists']
        for artist in parsed:
            new_row = row.drop('parsed_artists').to_dict()
            new_row['artist_name'] = artist
            new_row['original_artist_name'] = row['artist_name']
            expanded_rows.append(new_row)

    expanded_df = pd.DataFrame(expanded_rows)

    # If the user just wants unique artists deduplicated, we could drop other columns,
    # but the prompt says "Deduplicate duplicate rows", so drop duplicates across all columns

    # Deduplicate rows
    initial_len = len(expanded_df)
    expanded_df = expanded_df.drop_duplicates()
    final_len = len(expanded_df)
    print(f"Deduplicated {initial_len - final_len} rows. Final count: {final_len} rows.")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Saving to {output_path}...")
    expanded_df.to_csv(output_path, index=False)
    print("Done!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split multiple artists from Billboard Dictionary into distinct rows.")
    parser.add_argument("-i", "--input", type=Path, required=True, help="Input CSV file containing artist_name field")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output path for the processed CSV")

    args = parser.parse_args()

    process_file(args.input, args.output)

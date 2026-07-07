import pandas as pd
import json
import collections

db_path = r"D:\Music\Main_Song_Database.csv"
out_path = r"C:\Users\sethm\.gemini\antigravity\brain\ac74e32c-404f-4741-af88-b5e5a58c2d8c\scratch\library_analysis.json"

df = pd.read_csv(db_path, encoding='utf-8-sig', dtype=str)

results = {}
results['total_songs'] = len(df)
results['unique_artists'] = df['Artist'].nunique()

# ── 1. Top Artists ──
top_artists = df['Artist'].value_counts().head(20).to_dict()
results['top_artists'] = top_artists

# ── 2. Decades / Eras ──
# Convert 'Year' to numeric, dropping NaNs
df['Year_Num'] = pd.to_numeric(df['Year'], errors='coerce')
valid_years = df.dropna(subset=['Year_Num']).copy()
valid_years['Decade'] = (valid_years['Year_Num'] // 10) * 10

decade_counts = valid_years['Decade'].value_counts().sort_index().to_dict()
# Format decade labels (e.g. 1980.0 -> "1980s")
results['decades'] = {f"{int(k)}s": v for k, v in decade_counts.items() if 1900 <= k <= 2030}

# ── 3. Top Genres ──
# Genres might be comma-separated or dirty
all_genres = []
for g in df['Genre'].dropna():
    # Split by comma or slash
    parts = [x.strip().title() for x in str(g).replace('/', ',').split(',')]
    all_genres.extend([p for p in parts if p])

genre_counts = collections.Counter(all_genres)
# Filter out generic/useless genres
ignore_genres = ['Music', 'Pop', 'Rock', 'Alternative', 'Indie', 'Vocal']
filtered_genres = {k: v for k, v in genre_counts.items() if k not in ignore_genres and len(k) > 2}

results['top_genres_broad'] = dict(genre_counts.most_common(15))
results['top_genres_niche'] = dict(collections.Counter(filtered_genres).most_common(15))

# ── 4. Decade-Genre Cross-Analysis ──
decade_genres = {}
for decade in results['decades'].keys():
    d_num = int(decade[:4])
    d_df = valid_years[valid_years['Decade'] == d_num]
    d_genres = []
    for g in d_df['Genre'].dropna():
        parts = [x.strip().title() for x in str(g).replace('/', ',').split(',')]
        d_genres.extend([p for p in parts if p])
    top_d = collections.Counter(d_genres).most_common(5)
    decade_genres[decade] = dict(top_d)
results['decade_genres'] = decade_genres

with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)

print(f"Analysis saved to {out_path}")

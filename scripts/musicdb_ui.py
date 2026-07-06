import streamlit as st
import sqlite3
import pandas as pd
import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.similarity import calculate_similarity
from src.sqlite_poc import DB_PATH

st.set_page_config(page_title="MusicDB Pro Console", layout="wide")

# Stitch Design System Integration
STITCH_THEME = {
    "primary": "#4d90fe",
    "background": "#191a1f",
    "sidebar": "#202124"
}

st.markdown(f"""
    <style>
    .stApp {{
        background-color: {STITCH_THEME['background']};
        color: white;
    }}
    [data-testid="stSidebar"] {{
        background-color: {STITCH_THEME['sidebar']};
    }}
    </style>
""", unsafe_allow_html=True)

def get_connection():
    return sqlite3.connect(DB_PATH)

def load_data():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM view_search", conn)
    conn.close()
    return df

st.title("🎚️ MusicDB Pro Console")

if not os.path.exists(DB_PATH):
    st.error(f"Database not found. Please run `python scripts/musicdb.py --write build-v2` first.")
    st.stop()

df = load_data()

# --- SIDEBAR: Filter Presets ---
st.sidebar.header("Filter Presets")
preset_name = st.sidebar.text_input("Preset Name", "My Filter")
if st.sidebar.button("Save Current Filters"):
    # Mock save logic
    st.sidebar.success(f"Saved '{preset_name}'")

# --- SIDEBAR: Filters ---
st.sidebar.header("Filters")
high_density = st.sidebar.toggle("High Density Grid", value=True)

search_query = st.sidebar.text_input("Global Search (Title/Artist)", "")
artist_filter = st.sidebar.multiselect("Artist", options=sorted(df['artist'].unique()))
key_filter = st.sidebar.multiselect("Key", options=sorted(df['key'].dropna().unique()))

bpm_min, bpm_max = int(df['bpm'].min()) if not df['bpm'].dropna().empty else 0, int(df['bpm'].max()) if not df['bpm'].dropna().empty else 200
if bpm_min == bpm_max: bpm_max = bpm_min + 1
bpm_range = st.sidebar.slider("BPM Range", bpm_min, bpm_max, (bpm_min, bpm_max))

mood_query = st.sidebar.text_input("Mood/Vibe Search", "")

# Apply filters
filtered_df = df.copy()
if search_query:
    filtered_df = filtered_df[
        filtered_df['title'].str.contains(search_query, case=False, na=False) |
        filtered_df['artist'].str.contains(search_query, case=False, na=False)
    ]
if artist_filter:
    filtered_df = filtered_df[filtered_df['artist'].isin(artist_filter)]
if key_filter:
    filtered_df = filtered_df[filtered_df['key'].isin(key_filter)]
filtered_df = filtered_df[(filtered_df['bpm'] >= bpm_range[0]) & (filtered_df['bpm'] <= bpm_range[1])]

if mood_query:
    filtered_df = filtered_df[
        (filtered_df['mood'].str.contains(mood_query, case=False, na=False)) |
        (filtered_df['playlists'].str.contains(mood_query, case=False, na=False))
    ]

# --- MAIN: Grid ---
st.subheader(f"Main Grid ({len(filtered_df)})")

all_columns = filtered_df.columns.tolist()
default_cols = ['title', 'artist', 'bpm', 'key', 'playlists']
selected_cols = st.sidebar.multiselect("Visible Columns", options=all_columns, default=[c for c in default_cols if c in all_columns])

# Data Editor for Batch Edit
edited_df = st.data_editor(
    filtered_df[selected_cols],
    use_container_width=True,
    num_rows="dynamic",
    key="main_grid"
)

# --- BATCH EDIT TOOLS ---
with st.expander("🛠️ Batch Edit & Tools"):
    st.write("Batch update selected rows in the grid above.")
    new_tag = st.text_input("Add Playlist/Tag to selected")
    if st.button("Apply to All Visible"):
        st.info(f"Would apply '{new_tag}' to {len(filtered_df)} records.")

# --- SIMILARITY ---
st.divider()
st.subheader("🔍 Smart Discovery")
selection = st.selectbox("Select a song for similarity analysis", options=filtered_df.index, format_func=lambda x: f"{filtered_df.loc[x, 'title']} - {filtered_df.loc[x, 'artist']}")

if selection is not None:
    target_song = filtered_df.loc[selection].to_dict()
    all_songs = df.to_dict('records')
    similar_songs = calculate_similarity(target_song, all_songs)

    if similar_songs:
        sim_df = pd.DataFrame(similar_songs[:5])
        st.table(sim_df[['title', 'artist', 'similarity_score', 'reasons']])
    else:
        st.write("No similar songs found.")

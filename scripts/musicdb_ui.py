import streamlit as st
import sqlite3
import pandas as pd
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.similarity import calculate_similarity
from src.sqlite_poc import DB_PATH

st.set_page_config(page_title="MusicDB Search & Similarity", layout="wide")

def get_connection():
    return sqlite3.connect(DB_PATH)

def load_data():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM view_search", conn)
    conn.close()
    return df

st.title("🎵 MusicDB Search & Similarity MVP")

if not os.path.exists(DB_PATH):
    st.error(f"Database not found at {DB_PATH}. Please run `python scripts/musicdb.py --write build-v2` first.")
    st.stop()

df = load_data()

# Sidebar filters
st.sidebar.header("Filters")
search_query = st.sidebar.text_input("Global Search (Title/Artist)", "")
artist_filter = st.sidebar.multiselect("Artist", options=sorted(df['artist'].unique()))
key_filter = st.sidebar.multiselect("Key", options=sorted(df['key'].dropna().unique()))

bpm_min, bpm_max = int(df['bpm'].min()) if not df['bpm'].dropna().empty else 0, int(df['bpm'].max()) if not df['bpm'].dropna().empty else 200
if bpm_min == bpm_max:
    bpm_max = bpm_min + 1
bpm_range = st.sidebar.slider("BPM Range", bpm_min, bpm_max, (bpm_min, bpm_max))

# Mood Search (Placeholder mapping to playlists/mood)
mood_query = st.sidebar.text_input("Mood/Vibe Search", "")

# Apply filters
filtered_df = df.copy()

# Column Selection
all_columns = filtered_df.columns.tolist()
default_cols = ['title', 'artist', 'bpm', 'key', 'playlists']
selected_cols = st.sidebar.multiselect("Visible Columns", options=all_columns, default=[c for c in default_cols if c in all_columns])
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
        filtered_df['mood'].str.contains(mood_query, case=False, na=False) |
        filtered_df['playlists'].str.contains(mood_query, case=False, na=False)
    ]

st.subheader(f"Results ({len(filtered_df)})")

# Selection
selected_indices = st.multiselect("Select songs to find similar tracks", options=filtered_df.index, format_func=lambda x: f"{filtered_df.loc[x, 'title']} - {filtered_df.loc[x, 'artist']}")

col1, col2 = st.columns([2, 1])

with col1:
    st.dataframe(filtered_df[selected_cols], use_container_width=True)

with col2:
    if selected_indices:
        st.subheader("Similar Songs")
        for idx in selected_indices:
            target_song = filtered_df.loc[idx].to_dict()
            st.write(f"**Similar to: {target_song['title']}**")

            # Use all data for similarity search
            all_songs = df.to_dict('records')
            similar_songs = calculate_similarity(target_song, all_songs)

            if similar_songs:
                sim_df = pd.DataFrame(similar_songs[:5])
                st.table(sim_df[['title', 'artist', 'similarity_score', 'reasons']])
            else:
                st.write("No similar songs found.")
    else:
        st.info("Select a song from the list to see similarity recommendations.")

import streamlit as st
import sqlite3
import pandas as pd
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.similarity import calculate_similarity
from src.sqlite_poc import DB_PATH

# Design Tokens
STITCH_BG = "#09090A"
STITCH_SURFACE = "#141416"
STITCH_HOVER = "#1C1C1F"
STITCH_TEXT = "#EAEAEA"
STITCH_MUTED = "#737378"
STITCH_ORANGE = "#FF5000"
STITCH_CYAN = "#00E5FF"
STITCH_BORDER = "#2A2A2E"

st.set_page_config(page_title="MusicDB Pro Console", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for Stitch Design System
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;700&family=JetBrains+Mono:wght@400;700&display=swap');

    /* Main App Background */
    .stApp {{
        background-color: {STITCH_BG};
        color: {STITCH_TEXT};
        font-family: 'Space Grotesk', sans-serif;
    }}

    /* Global Typography */
    h1, h2, h3, h4, h5, h6, .stMarkdown h3 {{
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: {STITCH_TEXT};
        margin-bottom: 0.5rem;
    }}

    /* Data typography */
    .data-font {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
    }}

    /* Remove border radius */
    * {{
        border-radius: 0px !important;
    }}

    /* Custom borders and surfaces */
    .stTextInput>div>div>input, .stMultiSelect>div>div, .stMultiSelect [data-baseweb="tag"], .stSlider [data-baseweb="slider"] {{
        background-color: {STITCH_SURFACE} !important;
        border: 1px solid {STITCH_BORDER} !important;
        color: {STITCH_TEXT} !important;
    }}

    .stMultiSelect [data-baseweb="tag"] {{
        background-color: {STITCH_ORANGE} !important;
        color: white !important;
    }}

    /* Rail Styling */
    .rail-btn {{
        width: 40px;
        height: 40px;
        background: transparent;
        border: 1px solid {STITCH_BORDER};
        color: {STITCH_MUTED};
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 20px;
        cursor: pointer;
    }}
    .rail-btn:hover {{
        color: {STITCH_ORANGE};
        border-color: {STITCH_ORANGE};
    }}

    /* Custom Table Styling via st.dataframe configuration */
    /* We still use the custom table for high density if st.dataframe is too bulky */
    .stitch-table {{
        width: 100%;
        border-collapse: collapse;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
    }}
    .stitch-table th {{
        background-color: {STITCH_SURFACE};
        color: {STITCH_MUTED};
        text-transform: uppercase;
        font-size: 10px;
        padding: 6px 10px;
        border: 1px solid {STITCH_BORDER};
        text-align: left;
        position: sticky;
        top: 0;
        z-index: 10;
    }}
    .stitch-table td {{
        border: 1px solid {STITCH_BORDER};
        padding: 4px 10px;
        height: 28px;
        color: {STITCH_TEXT};
    }}
    .stitch-table tr:hover td {{
        background-color: {STITCH_HOVER};
    }}
    .stitch-table tr.selected td {{
        background-color: {STITCH_HOVER};
        border-left: 2px solid {STITCH_ORANGE};
    }}

    /* Bottom Action Bar */
    .action-bar-shim {{
        height: 60px;
    }}

    [data-testid="stVerticalBlock"] > div:last-child .action-bar-container {{
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: {STITCH_SURFACE};
        border-top: 1px solid {STITCH_ORANGE};
        padding: 10px 20px;
        z-index: 1000;
    }}

    /* Button styling */
    .stButton>button {{
        background-color: {STITCH_SURFACE};
        color: {STITCH_TEXT};
        border: 1px solid {STITCH_BORDER} !important;
        height: 32px;
        padding: 0 15px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
    }}
    .stButton>button:hover {{
        border-color: {STITCH_ORANGE} !important;
        color: {STITCH_ORANGE} !important;
    }}

    /* Primary button override */
    .stButton>button[kind="primary"] {{
        background-color: {STITCH_ORANGE} !important;
        color: white !important;
        border: none !important;
    }}

    /* Hide default Streamlit elements */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    /* Adjust container padding */
    .block-container {{
        padding-top: 1rem;
        padding-bottom: 5rem;
    }}

    /* Input focus */
    .stTextInput input:focus, .stMultiSelect div:focus {{
        border-color: {STITCH_CYAN} !important;
        box-shadow: 0 0 0 1px {STITCH_CYAN} !important;
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

if not os.path.exists(DB_PATH):
    st.error(f"DATABASE NOT FOUND: {DB_PATH}")
    st.stop()

df = load_data()

# --- SESSION STATE ---
if 'selected_ids' not in st.session_state:
    st.session_state.selected_ids = []
if 'visible_cols' not in st.session_state:
    st.session_state.visible_cols = ['recording_id', 'title', 'artist', 'bpm', 'key']

# --- TOP TOOLBAR ---
with st.container():
    col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns([2, 1, 1, 1, 1])
    with col_t1:
        search_query = st.text_input("CMD / SEARCH", placeholder="Search Title, Artist, ID...", label_visibility="collapsed")
    with col_t2:
        artist_filter = st.multiselect("ARTIST", options=sorted(df['artist'].unique()), placeholder="ARTIST", label_visibility="collapsed")
    with col_t3:
        key_filter = st.multiselect("KEY", options=sorted(df['key'].dropna().unique()), placeholder="KEY", label_visibility="collapsed")
    with col_t4:
        bpm_min, bpm_max = int(df['bpm'].min()) if not df['bpm'].dropna().empty else 0, int(df['bpm'].max()) if not df['bpm'].dropna().empty else 200
        bpm_range = st.slider("BPM", bpm_min, bpm_max, (bpm_min, bpm_max), label_visibility="collapsed")
    with col_t5:
        mood_query = st.text_input("MOOD / VIBE", placeholder="Mood...", label_visibility="collapsed")

# --- MAIN LAYOUT ---
col_rail, col_grid, col_inspector = st.columns([0.15, 3, 1])

with col_rail:
    st.markdown('<div class="rail-btn">⌗</div>', unsafe_allow_html=True)
    st.markdown('<div class="rail-btn">⚡</div>', unsafe_allow_html=True)
    st.markdown('<div class="rail-btn">📁</div>', unsafe_allow_html=True)
    st.markdown('<div class="rail-btn">⚙</div>', unsafe_allow_html=True)

    # Column selection in rail/sidebar context
    st.session_state.visible_cols = st.multiselect("COLS", options=df.columns.tolist(), default=st.session_state.visible_cols)

# Filter logic
filtered_df = df.copy()
if search_query:
    filtered_df = filtered_df[
        filtered_df['title'].str.contains(search_query, case=False, na=False) |
        filtered_df['artist'].str.contains(search_query, case=False, na=False) |
        filtered_df['recording_id'].str.contains(search_query, case=False, na=False)
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

with col_grid:
    st.markdown(f"### CONSOLE / {len(filtered_df)} RECORDS")

    # Using st.dataframe for sortability while trying to maintain density
    # Unfortunately Streamlit's st.dataframe height is not row-based easily.
    # We will use st.data_editor to allow row selection if we can, but it's often more than 28px.
    # To satisfy "sortable", we'll use st.dataframe.

    st.dataframe(
        filtered_df[st.session_state.visible_cols],
        use_container_width=True,
        hide_index=True,
        height=600
    )

with col_inspector:
    st.markdown("### INSPECTOR")

    # Selection using a multiselect as the source of truth
    selected_ids = st.multiselect("SELECT TO INSPECT",
                                  options=filtered_df['recording_id'].tolist(),
                                  default=st.session_state.selected_ids,
                                  format_func=lambda x: f"{filtered_df[filtered_df['recording_id']==x]['title'].values[0]} [{x[:6]}]",
                                  label_visibility="collapsed")

    st.session_state.selected_ids = selected_ids

    if selected_ids:
        # Show details for the latest selection
        target_id = selected_ids[-1]
        target_song = df[df['recording_id'] == target_id].iloc[0]

        st.markdown(f"""
            <div style="background-color: {STITCH_SURFACE}; padding: 15px; border: 1px solid {STITCH_BORDER};">
                <h4 style="color: {STITCH_ORANGE}; margin-top:0;">{target_song['title']}</h4>
                <div class="data-font">
                    <p><span style="color: {STITCH_MUTED}">ARTIST:</span> {target_song['artist']}</p>
                    <p><span style="color: {STITCH_MUTED}">VERSION:</span> {target_song.get('version') or '-'}</p>
                    <p><span style="color: {STITCH_MUTED}">BPM:</span> {target_song['bpm'] or '-'}</p>
                    <p><span style="color: {STITCH_MUTED}">KEY:</span> {target_song['key'] or '-'}</p>
                    <p><span style="color: {STITCH_MUTED}">MOOD:</span> {target_song.get('mood') or '-'}</p>
                    <p><span style="color: {STITCH_MUTED}">PLAYLISTS:</span> {target_song.get('playlists') or '-'}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f"### SIMILARITY <span style='color: {STITCH_CYAN}'>[AI]</span>", unsafe_allow_html=True)

        all_songs = df.to_dict('records')
        similar_songs = calculate_similarity(target_song.to_dict(), all_songs)

        if similar_songs:
            for sim in similar_songs[:5]:
                st.markdown(f"""
                    <div style="margin-bottom: 10px; padding: 8px; border-left: 2px solid {STITCH_CYAN}; background-color: {STITCH_BG};">
                        <div style="font-weight: bold; font-size: 12px; font-family: 'Space Grotesk';">{sim['title']}</div>
                        <div style="color: {STITCH_MUTED}; font-size: 11px;">{sim['artist']}</div>
                        <div style="color: {STITCH_CYAN}; font-size: 10px; font-family: 'JetBrains Mono'; margin-top:4px;">MATCH: {sim['similarity_score']}%</div>
                        <div style="color: {STITCH_MUTED}; font-size: 10px; font-family: 'JetBrains Mono';">{sim['reasons']}</div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Select a record to inspect.")

# --- BOTTOM ACTION BAR ---
# Using a sticky container at the bottom
if st.session_state.selected_ids:
    num_selected = len(st.session_state.selected_ids)

    # We use a container that we will target with CSS to be fixed at the bottom
    # We wrap it in a div with a specific class
    st.markdown('<div class="action-bar-container">', unsafe_allow_html=True)
    b_col1, b_col2, b_col3, b_col4, b_col_spacer, b_col5 = st.columns([1, 1, 1, 1, 4, 1])
    with b_col1:
        st.markdown(f"<div style='font-family: \"JetBrains Mono\"; font-size: 12px; color: {STITCH_ORANGE}; font-weight: bold; margin-top:8px;'>{num_selected} SELECTED</div>", unsafe_allow_html=True)
    with b_col2:
        st.button("BATCH EDIT", type="primary", key="batch_edit")
    with b_col3:
        st.button("EXPORT CSV", key="export_csv")
    with b_col4:
        st.button("ADD TO LIST", key="add_to_list")
    with b_col5:
        if st.button("CLEAR", key="clear_selection"):
            st.session_state.selected_ids = []
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Add a shim to prevent the bottom action bar from overlapping the content
    st.markdown('<div class="action-bar-shim"></div>', unsafe_allow_html=True)

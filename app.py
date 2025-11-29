import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import csv  # For quoting

# Page config
st.set_page_config(page_title="Spotify Analyzer", page_icon="🎵", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    .fun-fact { background-color: #ffeb3b; padding: 10px; border-radius: 10px; font-weight: bold; }
    .metric-container { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data(csv_path="full_clean_spotify_data.csv"):
    """Load the simplified Spotify CSV with derived columns."""
    if not os.path.exists(csv_path):
        st.error("CSV not found! Place full_clean_spotify_data.csv in the repo root.")
        return pd.DataFrame()
    
    try:
        # Step 1: Read raw CSV
        df = pd.read_csv(
            csv_path,
            quotechar='"',
            escapechar='\\',  # Handle escaped quotes/commas
            on_bad_lines='skip',  # Skip malformed rows
            low_memory=False
        )
        
        # Step 2: Verify key columns
        required_cols = ['played_at', 'artist_name', 'track_name', 'ms_played']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            st.error(f"Missing columns in CSV: {missing}. Ensure headers match.")
            return pd.DataFrame()
        
        # Step 3: Derive columns for compatibility
        df['end_time'] = pd.to_datetime(df['played_at'], errors='coerce')
        df['start_time'] = df['end_time'] - pd.to_timedelta(df['ms_played'], unit='ms')
        df['date'] = df['end_time'].dt.date
        df['month_year'] = df['end_time'].dt.to_period('M').astype(str)
        df['hours_played'] = df['ms_played'] / 3600000
        df['track'] = df['track_name'].fillna('Unknown Track')
        df['artist'] = df['artist_name'].fillna('Unknown Artist')
        df['album'] = 'Unknown Album'  # Not in CSV
        df['skipped'] = False  # Assume not skipped (not in CSV)
        df['platform_clean'] = 'Unknown'  # Not in CSV
        df['type'] = 'audio'  # Assume audio
        
        # Filter valid rows
        df = df.dropna(subset=['end_time'])
        df = df[df['ms_played'] > 0]
        
        st.success(f"Loaded {len(df)} streams successfully!")
        return df
        
    except Exception as e:
        st.error(f"CSV load failed: {str(e)}. Try regenerating the CSV.")
        return pd.DataFrame()

def calculate_stats(df):
    """Compute stats."""
    if df.empty:
        return {}
    total_hours = df['hours_played'].sum()
    total_tracks = len(df)
    skip_rate = (df['skipped'].sum() / total_tracks * 100) if total_tracks > 0 else 0
    
    top_tracks = df.groupby(['track', 'artist'])['hours_played'].sum().reset_index().sort_values('hours_played', ascending=False).head(10)
    top_artists = df.groupby('artist')['hours_played'].sum().reset_index().sort_values('hours_played', ascending=False).head(10)
    monthly = df.groupby('month_year')['hours_played'].sum().reset_index().sort_values('hours_played', ascending=False).head(5)
    
    daily_sessions = df.groupby('date')['ms_played'].sum().reset_index()
    longest_session = daily_sessions.loc[daily_sessions['ms_played'].idxmax()] if not daily_sessions.empty else pd.Series()
    
    stats = {
        'total_hours': total_hours,
        'total_tracks': total_tracks,
        'skip_rate': skip_rate,
        'top_tracks': top_tracks,
        'top_artists': top_artists,
        'top_months': monthly,
        'longest_session': longest_session,
        'platform_usage': df['platform_clean'].value_counts()
    }
    return stats

def find_song_by_datetime(df, target_datetime):
    """Find closest song to a given datetime."""
    if df.empty:
        return None
    df_copy = df.copy()
    df_copy['time_diff'] = abs((df_copy['end_time'] - target_datetime).dt.total_seconds())
    closest_idx = df_copy['time_diff'].idxmin()
    return df_copy.loc[closest_idx] if pd.notna(closest_idx) else None

def find_times_by_song(df, track_name, artist_name):
    """Find all play times for a song."""
    if df.empty:
        return pd.DataFrame()
    matches = df[(df['track'].str.contains(track_name, case=False, na=False)) & 
                 (df['artist'].str.contains(artist_name, case=False

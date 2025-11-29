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
                 (df['artist'].str.contains(artist_name, case=False, na=False))]
    return matches[['end_time', 'ms_played', 'skipped']].sort_values('end_time') if not matches.empty else pd.DataFrame()

def main():
    st.title("🎵 Spotify Streaming Time Machine 🎵")
    st.markdown("Dive into your streams. Total vibe time: Loaded dynamically!")
    
    df = load_data()
    if df.empty:
        st.stop()
    
    stats = calculate_stats(df)
    
    # Sidebar filters
    st.sidebar.header("Filters")
    if not df.empty:
        date_range = st.sidebar.date_input("Date Range", value=(df['date'].min(), df['date'].max()))
        filtered_df = df[(df['date'] >= date_range[0]) & (df['date'] <= date_range[1])].copy()
    else:
        filtered_df = pd.DataFrame()
    filtered_stats = calculate_stats(filtered_df)
    
    # Metrics
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("Total Hours", f"{filtered_stats.get('total_hours', 0):.1f}")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("Skip Rate", f"{filtered_stats.get('skip_rate', 0):.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Interactive Feature
    st.subheader("🕰️ Time Travel: Song Lookup")
    tab1, tab2 = st.tabs(["Date/Time → Song", "Song → Play Times"])
    
    with tab1:
        if filtered_df.empty:
            st.warning("Load data first!")
        else:
            st.markdown("Enter a UTC date/time to find what was playing.")
            col_dt1, col_dt2 = st.columns(2)
            with col_dt1:
                selected_date = st.date_input("Date", value=datetime.now().date())
            with col_dt2:
                selected_time = st.time_input("Time (UTC)", value=datetime.now().time())
            target_dt = datetime.combine(selected_date, selected_time)
            
            if st.button("Find Song"):
                closest = find_song_by_datetime(filtered_df, target_dt)
                if closest is not None:
                    st.success(f"**{closest['track']}** by **{closest['artist']}** (Album: {closest.get('album', 'N/A')})")
                    st.info(f"Played: {closest['start_time']} to {closest['end_time']} ({closest['ms_played']/1000:.0f}s)")
                    if closest.get('skipped', False):
                        st.warning("💨 Skipped!")
                    # Spotify URI not in CSV, skip
                else:
                    st.warning("No streams found nearby. Try a different time!")
    
    with tab2:
        if filtered_df.empty:
            st.warning("Load data first!")
        else:
            st.markdown("Search for a song to see when you played it.")
            track_input = st.text_input("Track Name", placeholder="e.g., Beggin'")
            artist_input = st.text_input("Artist", placeholder="e.g., Madcon")
            
            if st.button("Find Play Times") and track_input and artist_input:
                matches = find_times_by_song(filtered_df, track_input, artist_input)
                if not matches.empty:
                    st.success(f"Found {len(matches)} plays for '{track_input}' by '{artist_input}'.")
                    fig = px.timeline(matches, x_start="end_time", x_end="end_time", y=matches.index, 
                                      title="Play Timeline", hover_data=['ms_played', 'skipped'])
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(matches)
                else:
                    st.warning("No matches found. Check spelling!")
    
    # Fun Facts
    if filtered_stats:
        st.subheader("🎉 Fun Facts")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="fun-fact">Vibed {filtered_stats["total_hours"]:.0f} hrs – enough for {filtered_stats["total_hours"]/24:.1f} days!</div>', unsafe_allow_html=True)
        with col2:
            if not filtered_stats['longest_session'].empty:
                longest_date = filtered_stats['longest_session']['date']
                longest_min = filtered_stats['longest_session']['ms_played'] / 60000
                st.markdown(f'<div class="fun-fact">Epic day: {longest_date} ({longest_min:.0f} mins!)</div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="fun-fact">Skipped {filtered_stats["skip_rate"]:.0f}% – DJ mode activated? 🎧</div>', unsafe_allow_html=True)
    
    # Visualizations
    if filtered_stats:
        st.subheader("📊 Groove Charts")
        tab_v1, tab_v2, tab_v3, tab_v4 = st.tabs(["Top Tracks", "Top Artists", "Monthly Vibes", "Platforms"])
        
        with tab_v1:
            if not filtered_stats['top_tracks'].empty:
                fig = px.bar(filtered_stats['top_tracks'], x='hours_played', y='track', orientation='h', 
                             title="Top 10 Bangers", color='hours_played', color_continuous_scale='viridis')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data for charts yet.")
        
        with tab_v2:
            if not filtered_stats['top_artists'].empty:
                fig = px.pie(filtered_stats['top_artists'], values='hours_played', names='artist', title="Artist Pie")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data for charts yet.")
        
        with tab_v3:
            if not filtered_stats['top_months'].empty:
                fig = px.line(filtered_stats['top_months'], x='month_year', y='hours_played', title="Peak Months")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data for charts yet.")
        
        with tab_v4:
            if not filtered_stats['platform_usage'].empty:
                fig = px.bar(filtered_stats['platform_usage'], title="Stream Spots")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data for charts yet.")
    
    # Export
    if not filtered_df.empty:
        csv_export = filtered_df.to_csv(index=False, quoting=csv.QUOTE_ALL).encode('utf-8')
        st.download_button("📥 Download Filtered CSV", csv_export, "filtered_spotify_history.csv", "text/csv")
    
    with st.expander("Data Preview"):
        if not filtered_df.empty:
            st.dataframe(filtered_df.head(50))
        else:
            st.info("No data loaded.")

if __name__ == "__main__":
    main()

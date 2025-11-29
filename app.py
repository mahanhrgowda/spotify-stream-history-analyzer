import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import csv  # Added for quoting fix

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
def load_data(csv_path="full_cleaned_spotify_history.csv"):
    """Load the cleaned CSV with robust parsing."""
    if os.path.exists(csv_path):
        # Fixed: Use QUOTE_ALL to handle unquoted commas in fields like platform
        df = pd.read_csv(
            csv_path, 
            parse_dates=['end_time', 'start_time'], 
            quoting=csv.QUOTE_ALL,  # Force all fields as quoted
            low_memory=False  # For large CSVs
        )
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    else:
        st.error("CSV not found! Place full_cleaned_spotify_history.csv in data/.")
        return pd.DataFrame()

def calculate_stats(df):
    """Compute stats."""
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
    df['time_diff'] = abs((df['end_time'] - target_datetime).dt.total_seconds())
    closest = df.loc[df['time_diff'].idxmin()]
    return closest if not df.empty else None

def find_times_by_song(df, track_name, artist_name):
    """Find all play times for a song."""
    matches = df[(df['track'].str.contains(track_name, case=False, na=False)) & 
                 (df['artist'].str.contains(artist_name, case=False, na=False))]
    return matches[['end_time', 'ms_played', 'skipped']].sort_values('end_time') if not matches.empty else pd.DataFrame()

def main():
    st.title("🎵 Spotify Streaming Time Machine 🎵")
    st.markdown("Dive into your 76k+ streams from 2019–2023. Total vibe time: ~1,768 hours!")
    
    df = load_data()
    if df.empty:
        st.stop()
    
    stats = calculate_stats(df)
    
    # Sidebar filters
    st.sidebar.header("Filters")
    date_range = st.sidebar.date_input("Date Range", value=(df['date'].min(), df['date'].max()))
    filtered_df = df[(df['date'] >= date_range[0]) & (df['date'] <= date_range[1])].copy()
    filtered_stats = calculate_stats(filtered_df)
    
    # Metrics
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("Total Hours", f"{filtered_stats['total_hours']:.1f}")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("Skip Rate", f"{filtered_stats['skip_rate']:.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # New Interactive Feature
    st.subheader("🕰️ Time Travel: Song Lookup")
    tab1, tab2 = st.tabs(["Date/Time → Song", "Song → Play Times"])
    
    with tab1:
        st.markdown("Enter a UTC date/time to find what was playing.")
        col_dt1, col_dt2 = st.columns(2)
        with col_dt1:
            selected_date = st.date_input("Date", value=datetime.now().date())
        with col_dt2:
            selected_time = st.time_input("Time (UTC)", value=datetime.now().time())
        target_dt = datetime.combine(selected_date, selected_time)
        
        if st.button("Find Song", key="find_song"):
            closest = find_song_by_datetime(filtered_df, target_dt)
            if closest is not None:
                st.success(f"**{closest['track']}** by **{closest['artist']}** (Album: {closest['album']})")
                st.info(f"Played: {closest['start_time']} to {closest['end_time']} ({closest['ms_played']/1000:.0f}s)")
                if closest['skipped']:
                    st.warning("💨 Skipped!")
                col_img, col_uri = st.columns(2)
                if pd.notna(closest.get('spotify_track_uri')):
                    col_uri.markdown(f"[Spotify Link]({closest['spotify_track_uri']})")
            else:
                st.warning("No streams found nearby. Try a different time!")
    
    with tab2:
        st.markdown("Search for a song to see when you played it.")
        track_input = st.text_input("Track Name", placeholder="e.g., Kesariya")
        artist_input = st.text_input("Artist", placeholder="e.g., Pritam")
        
        if st.button("Find Play Times", key="find_times") and track_input and artist_input:
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
    st.subheader("📊 Groove Charts")
    tab_v1, tab_v2, tab_v3, tab_v4 = st.tabs(["Top Tracks", "Top Artists", "Monthly Vibes", "Platforms"])
    
    with tab_v1:
        fig = px.bar(filtered_stats['top_tracks'], x='hours_played', y='track', orientation='h', 
                     title="Top 10 Bangers", color='hours_played', color_continuous_scale='viridis')
        st.plotly_chart(fig, use_container_width=True)
    
    with tab_v2:
        fig = px.pie(filtered_stats['top_artists'], values='hours_played', names='artist', title="Artist Pie")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab_v3:
        fig = px.line(filtered_stats['top_months'], x='month_year', y='hours_played', title="Peak Months")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab_v4:
        fig = px.bar(filtered_stats['platform_usage'], title="Stream Spots")
        st.plotly_chart(fig, use_container_width=True)
    
    # Export
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Filtered CSV", csv, "filtered_spotify_history.csv", "text/csv")
    
    with st.expander("Data Preview"):
        st.dataframe(filtered_df.head(50))

if __name__ == "__main__":
    main()

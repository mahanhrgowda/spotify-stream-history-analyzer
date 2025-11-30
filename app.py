import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import pytz  # Add for timezone handling
import random  # For fun random features

# Page config
st.set_page_config(page_title="Spotify Analyzer", page_icon="\u1f3b5", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    .fun-fact { background-color: #ffeb3b; padding: 10px; border-radius: 10px; font-weight: bold; }
    .metric-container { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    .warning-fun { background-color: #fff3cd; padding: 10px; border-radius: 10px; font-style: italic; color: #856404; }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data(csv_path="data/full_cleaned_spotify_history.csv"):
    """Load the cleaned CSV."""
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, parse_dates=['end_time', 'start_time'])
            df['date'] = pd.to_datetime(df['date']).dt.date
            # Ensure end_time is timezone-aware UTC
            df['end_time'] = pd.to_datetime(df['end_time'], utc=True)
            df['start_time'] = pd.to_datetime(df['start_time'], utc=True)
            return df
        except pd.errors.EmptyDataError:
            st.error("CSV file is empty! Please ensure the file has data.")
            return pd.DataFrame()
        except pd.errors.ParserError:
            st.error("Invalid CSV format! Please check the file structure.")
            return pd.DataFrame()
    else:
        st.error(f"CSV not found! Please place full_cleaned_spotify_history.csv in the data/ directory.")
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
   
    # New: Day of week listening heatmap data
    df['day_of_week'] = pd.to_datetime(df['end_time']).dt.day_name()
    df['hour'] = pd.to_datetime(df['end_time']).dt.hour
    heatmap_data = df.groupby(['day_of_week', 'hour'])['ms_played'].sum().reset_index()
   
    stats = {
        'total_hours': total_hours,
        'total_tracks': total_tracks,
        'skip_rate': skip_rate,
        'top_tracks': top_tracks,
        'top_artists': top_artists,
        'top_months': monthly,
        'longest_session': longest_session,
        'platform_usage': df['platform_clean'].value_counts(),
        'heatmap_data': heatmap_data
    }
    return stats

def find_song_by_datetime(df, target_datetime_utc):
    """Find closest song to a given UTC datetime."""
    if df.empty:
        return None
    df_temp = df.copy()  # Avoid modifying original
    df_temp['time_diff'] = abs((df_temp['end_time'] - target_datetime_utc).dt.total_seconds())
    min_idx = df_temp['time_diff'].idxmin()
    if pd.isna(min_idx):
        return None
    closest = df_temp.loc[min_idx]
    return closest

def find_times_by_song(df, track_name, artist_name):
    """Find all play times for a song."""
    matches = df[(df['track'].str.contains(track_name, case=False, na=False)) &
                 (df['artist'].str.contains(artist_name, case=False, na=False))]
    return matches[['end_time', 'ms_played', 'skipped']].sort_values('end_time') if not matches.empty else pd.DataFrame()

# New fun feature: Get random fun fact
def get_random_fun_fact(stats):
    facts = [
        f"You've grooved for {stats['total_hours']:.0f} hours \u2013 that's like binge-watching {stats['total_hours']/24:.0f} full days of Netflix! \u1f4fa",
        f"Top banger alert: {stats['top_tracks'].iloc[0]['track']} by {stats['top_tracks'].iloc[0]['artist']} owns your playlist! \u1f525",
        f"Skip master: {stats['skip_rate']:.0f}% skips mean you're curating like a pro DJ. No filler allowed! \u1f39b\ufe0f",
        "Fun stat: Your longest jam session could power a small concert. Encore? \u1f3a4"
    ]
    return random.choice(facts)

# New fun feature: Mood-based random song suggestion
def suggest_random_song(stats, mood="chill"):
    top_tracks = stats['top_tracks']
    if mood == "chill":
        # Mock: Pick slower tracks or random from top
        return top_tracks.iloc[random.randint(0, min(5, len(top_tracks)-1))]
    else:
        return top_tracks.iloc[0]  # Default to top

def main():
    st.title("\u1f3b5 Spotify Streaming Time Machine \u1f3b5")
    st.markdown("Dive into your 76k+ streams from 2019\u20132023. Total vibe time: ~1,768 hours! Let's make it even more epic. \u1f680")
   
    df = load_data()
    if df.empty:
        st.stop()
   
    stats = calculate_stats(df)
   
    # Sidebar filters
    st.sidebar.header("Filters")
    date_range = st.sidebar.date_input("Date Range", value=(df['date'].min(), df['date'].max()), min_value=df['date'].min(), max_value=df['date'].max())
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
   
    # New Fun Feature: Random Fun Fact Button
    if st.button("\u1f3b2 Drop a Random Fun Fact!"):
        fact = get_random_fun_fact(filtered_stats)
        st.markdown(f'<div class="fun-fact">{fact}</div>', unsafe_allow_html=True)
   
    # New Interactive Feature
    st.subheader("\u1f570\ufe0f Time Travel: Song Lookup")
    tab1, tab2 = st.tabs(["Date/Time \u2192 Song", "Song \u2192 Play Times"])
   
    with tab1:
        st.markdown("Enter a date/time to find what was playing. Now with timezone magic! \u1f30d")
        col_tz, col_date = st.columns([1, 2])
        with col_tz:
            timezone = st.selectbox("Your Timezone", options=list(pytz.all_timezones), index=list(pytz.all_timezones).index('UTC'), help="Select your local timezone for input.")
        col_dt1, col_dt2 = st.columns(2)
        with col_dt1:
            selected_date = st.date_input("Date", value=datetime.now().date())
        with col_dt2:
            selected_time = st.time_input("Time", value=datetime.now().time())
        target_local = datetime.combine(selected_date, selected_time)
        tz = pytz.timezone(timezone)
        target_dt_local = tz.localize(target_local)
        target_dt_utc = target_dt_local.astimezone(pytz.UTC)  # Convert to UTC for lookup
       
        if st.button("Find Song", key="find_song"):
            if filtered_df.empty:
                st.markdown('<div class="warning-fun">\u1f570\ufe0f Time machine says: "No vibes in this era yet!" Adjust your date range for some retro hits. \u23f3</div>', unsafe_allow_html=True)
            else:
                closest = find_song_by_datetime(filtered_df, target_dt_utc)
                if closest is not None:
                    st.success(f"**{closest['track']}** by **{closest['artist']}** (Album: {closest['album']})")
                    st.info(f"Played: {closest['start_time']} to {closest['end_time']} ({closest['ms_played']/1000:.0f}s)")
                    if closest['skipped']:
                        st.markdown('<div class="warning-fun">\u1f4a8 Skipped faster than a plot twist! Whoopsie. \u1f60f</div>', unsafe_allow_html=True)
                    col_img, col_uri = st.columns(2)
                    if pd.notna(closest.get('spotify_track_uri')):
                        col_uri.markdown(f"[Spotify Link]({closest['spotify_track_uri']})")
                else:
                    st.markdown('<div class="warning-fun">\u1f52e Crystal ball\'s cloudy: No streams near that cosmic moment. Try a different timestamp? \u2728</div>', unsafe_allow_html=True)
   
    with tab2:
        st.markdown("Search for a song to see when you played it.")
        track_input = st.text_input("Track Name", placeholder="e.g., Kesariya")
        artist_input = st.text_input("Artist", placeholder="e.g., Pritam")
       
        if st.button("Find Play Times", key="find_times") and track_input and artist_input:
            matches = find_times_by_song(filtered_df, track_input, artist_input)
            if not matches.empty:
                st.success(f"Found {len(matches)} plays for '{track_input}' by '{artist_input}'. Time to reminisce! \u1f4bf")
                fig = px.timeline(matches, x_start="end_time", x_end="end_time", y=matches.index,
                                  title="Play Timeline", hover_data=['ms_played', 'skipped'])
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(matches)
            else:
                st.markdown('<div class="warning-fun">\u2753 Song not in your history? Maybe it\'s a future bop waiting to drop. Check the spelling, maestro! \u1f3bc</div>', unsafe_allow_html=True)
   
    # New Fun Feature: Mood Mixer: Random Rec
    st.subheader("\u1f3ad Mood Mixer: Random Rec")
    mood = st.selectbox("Feeling?", options=["Chill Vibes", "Hype Mode", "Random Jam"])
    if st.button("Suggest a Track! \u1f3b6"):
        suggestion = suggest_random_song(filtered_stats, mood.lower().replace(" ", "_"))
        st.balloons()  # Fun animation
        st.success(f"Try this: **{suggestion['track']}** by **{suggestion['artist']}** \u2013 {suggestion['hours_played']:.1f} hrs of pure {mood.lower()} magic!")
   
    # Fun Facts (Enhanced)
    st.subheader("\u1f389 Fun Facts")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="fun-fact">Vibed {filtered_stats["total_hours"]:.0f} hrs \u2013 enough for {filtered_stats["total_hours"]/24:.1f} days of non-stop jams! \u1f973</div>', unsafe_allow_html=True)
    with col2:
        if not filtered_stats['longest_session'].empty:
            longest_date = filtered_stats['longest_session']['date']
            longest_min = filtered_stats['longest_session']['ms_played'] / 60000
            st.markdown(f'<div class="fun-fact">Epic marathon: {longest_date} with {longest_min:.0f} mins! Legend status unlocked. \u1f3c6</div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="fun-fact">Skipped {filtered_stats["skip_rate"]:.0f}% \u2013 You\'re the ultimate playlist surgeon! Scalpel? Nah, skip button. \u2695\ufe0f</div>', unsafe_allow_html=True)
   
    # Visualizations (Added Heatmap Tab)
    st.subheader("\u1f4ca Groove Charts")
    tab_v1, tab_v2, tab_v3, tab_v4, tab_v5 = st.tabs(["Top Tracks", "Top Artists", "Monthly Vibes", "Platforms", "Listening Heatmap"])
   
    with tab_v1:
        fig = px.bar(filtered_stats['top_tracks'], x='hours_played', y='track', orientation='h',
                     title="Top 10 Bangers", color='hours_played', color_continuous_scale='viridis')
        st.plotly_chart(fig, use_container_width=True)
   
    with tab_v2:
        fig = px.pie(filtered_stats['top_artists'], values='hours_played', names='artist', title="Artist Pie \u2013 Who's the MVP?")
        st.plotly_chart(fig, use_container_width=True)
   
    with tab_v3:
        fig = px.line(filtered_stats['top_months'], x='month_year', y='hours_played', title="Peak Months \u2013 When You Peaked!")
        st.plotly_chart(fig, use_container_width=True)
   
    with tab_v4:
        fig = px.bar(filtered_stats['platform_usage'], title="Stream Spots \u2013 Mobile Mayhem or Desktop Dreams?")
        st.plotly_chart(fig, use_container_width=True)
   
    with tab_v5:
        # New Heatmap
        heatmap_pivot = filtered_stats['heatmap_data'].pivot(index='hour', columns='day_of_week', values='ms_played').fillna(0)
        fig = px.imshow(heatmap_pivot, title="When Do You Groove? (Heatmap of Listening)", color_continuous_scale='plasma', aspect="auto")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Hotter colors = More playtime. Spot your weekend warrior vibes? \u1f57a")
   
    # Export
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button("\u1f4e5 Download Filtered CSV", csv, "filtered_spotify_history.csv", "text/csv")
   
    with st.expander("Data Preview"):
        st.dataframe(filtered_df.head(50))

if __name__ == "__main__":
    main()

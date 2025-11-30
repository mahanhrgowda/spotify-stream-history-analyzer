import streamlit as st
import pandas as pd
from datetime import datetime, time
import pytz
import random
import matplotlib.pyplot as plt
import seaborn as sns

# Load the dataset
@st.cache_data
def load_data():
    df = pd.read_csv('dataset.csv')
    # Parse timestamps
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['end_time'] = pd.to_datetime(df['end_time'])
    df['date'] = pd.to_datetime(df['date']).dt.date
    return df

df = load_data()

# Unique songs, artists, albums for dropdowns
unique_songs = sorted(df['track'].dropna().unique())
unique_artists = sorted(df['artist'].dropna().unique())

# Sidebar for timezone selection
st.sidebar.header("Settings")
user_tz = st.sidebar.selectbox(
    "Select your timezone",
    options=pytz.all_timezones,
    index=pytz.all_timezones.index('Asia/Kolkata')  # Default to IN timezone
)

# Fun feature: Theme selector
theme = st.sidebar.radio("App Theme", ["Light", "Dark", "Retro"])
if theme == "Dark":
    st.markdown("<style>body {background-color: #121212; color: white;}</style>", unsafe_allow_html=True)
elif theme == "Retro":
    st.markdown("<style>body {background-color: #f5f5dc; color: #8b4513; font-family: 'Courier New', Courier, monospace;}</style>", unsafe_allow_html=True)

# Title
st.title("🎵 Spotify Time Capsule App")
st.markdown("Travel back in time through your listening history! Enter a date and time to see what you were jamming to, or search for a song to see when you listened to it. With timezone support and some fun surprises! 🚀")

# Tabs for features
tab1, tab2, tab3 = st.tabs(["Time to Song", "Song to Times", "Fun Insights"])

with tab1:
    st.header("What was playing at a specific time?")
    st.markdown("Enter a date and time in your selected timezone, and I'll tell you the song (if any) that was playing.")

    # Date and time inputs
    selected_date = st.date_input("Select Date", value=datetime.now().date())
    selected_time = st.time_input("Select Time", value=time(12, 0))

    if st.button("Open Time Capsule"):
        # Combine date and time
        local_dt = datetime.combine(selected_date, selected_time)
        # Localize to user timezone
        local_tz = pytz.timezone(user_tz)
        local_dt = local_tz.localize(local_dt)
        # Convert to UTC
        utc_dt = local_dt.astimezone(pytz.utc)

        # Find rows where start_time <= utc_dt <= end_time
        playing = df[(df['start_time'] <= utc_dt) & (df['end_time'] >= utc_dt)]

        if not playing.empty:
            row = playing.iloc[0]  # Assume no overlaps
            st.success(f"At {utc_dt} UTC ({local_dt} in {user_tz}), you were listening to:")
            st.markdown(f"**Track:** {row['track']}")
            st.markdown(f"**Artist:** {row['artist']}")
            st.markdown(f"**Album:** {row['album']}")
            st.markdown(f"**Platform:** {row['platform_clean']}")
            st.markdown(f"**Duration Played:** {row['hours_played'] * 60:.2f} minutes")

            # Fun feature: Spotify link
            if pd.notna(row['spotify_track_uri']):
                track_id = row['spotify_track_uri'].split(':')[-1]
                st.markdown(f"[Listen on Spotify](https://open.spotify.com/track/{track_id})")

            # Fun feature: Random fun fact
            fun_facts = [
                "Did you know? This song was played on a {platform} device!",
                "Time travel tip: You skipped {skipped} songs around this time.",
                "Blast from the past: This was in {month_year}!"
            ]
            fact = random.choice(fun_facts).format(
                platform=row['platform_clean'],
                skipped="some" if row['skipped'] else "no",
                month_year=row['month_year']
            )
            st.info(fact)
        else:
            st.warning("No song was playing at that exact time. Maybe you were taking a break? 🎧")
            # Find nearest
            df['time_diff'] = abs(df['start_time'] - utc_dt)
            nearest = df.loc[df['time_diff'].idxmin()]
            st.markdown(f"Nearest song: **{nearest['track']}** by {nearest['artist']} at {nearest['start_time']}")

with tab2:
    st.header("When did I listen to a specific song?")
    st.markdown("Search for a song or artist to see all the times you listened to it.")

    search_type = st.radio("Search by", ["Song", "Artist"])
    if search_type == "Song":
        selected_song = st.selectbox("Select Song", options=unique_songs)
        filtered = df[df['track'] == selected_song]
    else:
        selected_artist = st.selectbox("Select Artist", options=unique_artists)
        filtered = df[df['artist'] == selected_artist]

    if not filtered.empty:
        st.subheader(f"Listen History for {selected_song if search_type == 'Song' else selected_artist}")
        # Convert times to user timezone
        filtered['start_local'] = filtered['start_time'].dt.tz_convert(user_tz)
        filtered['end_local'] = filtered['end_time'].dt.tz_convert(user_tz)

        for _, row in filtered.iterrows():
            st.markdown(f"- {row['start_local']} to {row['end_local']} ({row['hours_played'] * 60:.2f} min) on {row['platform_clean']}")

        # Fun feature: Total plays
        total_plays = len(filtered)
        total_hours = filtered['hours_played'].sum()
        st.info(f"You've listened to this {search_type.lower()} {total_plays} times, for a total of {total_hours:.2f} hours! 🎉")

        # Fun feature: Most common platform
        common_platform = filtered['platform_clean'].mode()[0]
        st.info(f"Most common platform: {common_platform}")
    else:
        st.warning("No listens found for that search.")

with tab3:
    st.header("Fun Insights & Visualizations")
    st.markdown("Dive deeper into your listening habits!")

    # Date selector for daily summary
    insight_date = st.date_input("Select Date for Daily Summary", value=datetime.now().date())
    daily_df = df[df['date'] == insight_date]

    if not daily_df.empty:
        st.subheader(f"Summary for {insight_date}")
        total_hours_day = daily_df['hours_played'].sum()
        st.markdown(f"Total listening time: {total_hours_day:.2f} hours")
        
        # Top songs
        top_songs = daily_df['track'].value_counts().head(5)
        st.markdown("Top Songs:")
        for song, count in top_songs.items():
            st.markdown(f"- {song}: {count} plays")
        
        # Visualization: Listening over the day
        if st.checkbox("Show Daily Listening Chart"):
            daily_df['hour'] = daily_df['start_time'].dt.hour
            fig, ax = plt.subplots()
            sns.countplot(x='hour', data=daily_df, ax=ax)
            ax.set_title("Listening Activity by Hour")
            st.pyplot(fig)
        
        # Fun feature: Generate a "Time Capsule Message"
        if st.button("Generate Time Capsule Message"):
            random_song = daily_df.sample(1).iloc[0]
            message = f"On {insight_date}, you were vibing to '{random_song['track']}' by {random_song['artist']}. Remember the good times! ⏳🎶"
            st.success(message)
            st.balloons()
    else:
        st.warning("No data for that date.")

# Footer
st.markdown("---")
st.markdown("Built with ❤️ by Grok. Data from Mahaan's Spotify history. Deployed on Streamlit! Device Name = @mahanhrgowda !!!")

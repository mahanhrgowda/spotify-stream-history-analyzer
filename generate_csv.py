# save as generate_csv.py and run: python generate_csv.py
import json
import pandas as pd
import os
from datetime import timedelta

# Assume JSONs in ./original_jsons/
json_files = [f for f in os.listdir('./original_jsons') if f.endswith('.json')]
all_data = []

for file in json_files:
    with open(f'./original_jsons/{file}', 'r') as f:
        data = json.load(f)
        for entry in data:
            entry['type'] = 'audio' if 'master_metadata_track_name' in entry else 'video'
            if entry['type'] == 'video':
                entry['master_metadata_track_name'] = entry.get('episode_name', 'Unknown')
                entry['master_metadata_album_artist_name'] = entry.get('episode_show_name', 'Unknown')
                entry['master_metadata_album_album_name'] = entry.get('episode_show_name', 'Unknown')
        all_data.extend(data)

df = pd.DataFrame(all_data)
df['end_time'] = pd.to_datetime(df['ts'])
df['start_time'] = df['end_time'] - pd.to_timedelta(df['ms_played'], unit='ms')
df['date'] = df['end_time'].dt.date
df['month_year'] = df['end_time'].dt.to_period('M')
df['hours_played'] = df['ms_played'] / 3600000
df['track'] = df['master_metadata_track_name'].fillna('Unknown Track')
df['artist'] = df['master_metadata_album_artist_name'].fillna('Unknown Artist')
df['album'] = df['master_metadata_album_album_name'].fillna('Unknown Album')
df['skipped'] = df['skipped'].fillna(False)
df['platform_clean'] = df['platform'].str.split(' ').str[0]
df = df[df['ms_played'] > 0]

df.to_csv('data/full_cleaned_spotify_history.csv', index=False)
print(f"Generated CSV with {len(df)} rows.")

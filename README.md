# Spotify Streaming History Analyzer 🎵🕰️

Interactive Streamlit app for your Spotify data (2019–2023). Load the cleaned CSV and explore!

## Quick Start
1. Clone: `git clone https://github.com/YOURUSERNAME/spotify-stream-history-analyzer.git`
2. Add JSONs to `original_jsons/` and run `python generate_csv.py` to create the CSV in `data/`.
3. `pip install -r requirements.txt`
4. `streamlit run app.py`

## Features
- **Time Machine**: Date/time → Song, or Song → Play history.
- Top tracks/artists, monthly trends, platforms.
- Fun facts & exports.
- Deploy: Streamlit Cloud (public repo).

## Dataset
- `data/full_cleaned_spotify_history.csv`: 76k streams, merged from your JSONs.
- Stats: 1,768 hours, 12.5% skip rate.

Built for easy vibes! 🚀

# Steam Player Engagement Analytics

An automated data pipeline that tracks player engagement across popular Steam games — pulling live data daily, storing it in a cloud database, and surfacing it through an interactive dashboard.

**Live dashboard:** _[add your Streamlit Community Cloud link here after deploying]_

---

## What This Project Does

Rather than analyzing a static, pre-cleaned dataset, this project **builds and runs its own data pipeline end-to-end**:

1. **Pulls** live game data (genres, pricing, current player counts) from the Steam Web API and SteamSpy
2. **Stores** it in a cloud MySQL database (Aiven), building a daily historical snapshot over time
3. **Cleans and reshapes** the raw data — splitting multi-genre strings, parsing dates, filtering out non-game software that occasionally shows up in the source data
4. **Runs automatically every day** via GitHub Actions, with no manual intervention
5. **Visualizes** the results in a live, interactive Streamlit dashboard

## Why This Approach

Steam, Xbox, and Nintendo don't publish real sales figures — that data is proprietary, and most "Steam sales" datasets found online are actually rough, unreliable estimates. Instead, this project uses **live concurrent player counts** as an engagement metric — real, verifiable data pulled directly from Steam's own public API, rather than guessing at unavailable sales numbers.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Steam API   │     │  SteamSpy    │     │  (top-played     │
│ (game details│     │  API         │     │   game list)     │
│  + players)  │     │              │     │                  │
└──────┬───────┘     └──────┬───────┘     └──────────────────┘
       │                    │
       └────────┬───────────┘
                 ▼
       ┌────────────────────┐
       │  fetch_steam_      │   Runs daily at 00:00 UTC
       │  data.py           │   via GitHub Actions
       └─────────┬──────────┘
                 ▼
       ┌────────────────────┐
       │  Aiven MySQL       │
       │  games_raw table   │
       └─────────┬──────────┘
                 ▼
       ┌────────────────────┐
       │  clean_data.py     │   Splits genres, parses dates,
       │                    │   filters non-game entries
       └─────────┬──────────┘
                 ▼
       ┌────────────────────┐
       │  Aiven MySQL       │
       │  games_clean table │
       └─────────┬──────────┘
                 ▼
       ┌─────────────────────┐
       │  app.py             │
       │  Streamlit Dashboard│
       └─────────────────────┘
```

## Tech Stack

- **Python** — requests, pandas
- **MySQL** (hosted on Aiven) — cloud database, SSL-secured
- **GitHub Actions** — daily automated pipeline scheduling
- **Streamlit + Plotly** — interactive dashboard, deployed on Streamlit Community Cloud

## Key Findings So Far

- Free-to-play games draw dramatically higher concurrent player counts than paid games, regardless of genre
- Within paid games specifically, price shows no strong relationship to player count
- Genre-level comparisons are shown alongside sample sizes, since some genres in the tracked dataset are represented by very few games — a deliberate choice to avoid presenting misleading averages

## Data Limitations (Being Upfront)

- **Player counts ≠ sales.** This project deliberately avoids using sales estimates (which aren't publicly available and are unreliable when "estimated"), and instead uses live concurrent player counts as a proxy for engagement.
- **Sample is popularity-biased.** Tracked games come from SteamSpy's "top played" lists, so this isn't a random or complete sample of all Steam games — it's specifically the most popular ones.
- **Time-series depth grows daily.** Trend analysis (player counts over time) becomes more meaningful the longer the automated pipeline runs, since it started collecting data recently.

## Project Structure

```
├── .github/workflows/
│   └── daily_pull.yml       # GitHub Actions automation
├── fetch_steam_data.py      # Ingestion: Steam API + SteamSpy → games_raw
├── clean_data.py            # Transformation: games_raw → games_clean
├── setup_db.py               # One-time schema setup script
├── view_data.py               # Quick CLI script to inspect table contents
├── app.py                    # Streamlit dashboard
├── schema.sql                 # Database schema
├── requirements.txt
├── .env.example               # Template for local environment variables
└── README.md
```

## Running This Locally

1. Clone the repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in your own MySQL credentials (Aiven or local MySQL/XAMPP both supported — see comments in `.env.example`)
3. Set up the database schema:
   ```bash
   python setup_db.py
   ```
4. Pull data and clean it:
   ```bash
   python fetch_steam_data.py
   python clean_data.py
   ```
5. Launch the dashboard:
   ```bash
   streamlit run app.py
   ```

## Automation

The pipeline runs automatically every day at 00:00 UTC via GitHub Actions (`.github/workflows/daily_pull.yml`), fetching fresh data and re-running the cleaning step — no manual steps required. Credentials are stored securely as GitHub Actions repository secrets, never committed to the codebase.

## Features
- Automated Steam data collection
- MySQL database pipeline
- Interactive Streamlit dashboard
- Data visualization with Plotly
- LLM-generated executive insights using the Google Gemini API
- Daily data refresh and caching

## Future Improvements

- Expand tracked game list beyond current top-played titles for broader genre coverage
- Incremental cleaning (append-only) rather than full table rebuild, to support larger-scale data
- Deeper trend analysis once more days of historical data accumulate
- Player count anomaly detection (e.g. flagging unusual spikes around major game updates or sales events)

---

Built as a portfolio project to demonstrate end-to-end data pipeline design: ingestion, cloud storage, LLM utilization, automated orchestration, transformation, and deployment — not just static analysis of a downloaded file.
"""
app.py

Streamlit dashboard for the Steam Player Engagement Analytics project.
Run locally with: streamlit run app.py
Deploy for free on Streamlit Community Cloud when ready to share a live link.
"""

import os
import pandas as pd
import plotly.express as px
import mysql.connector
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Steam Player Engagement Analytics", layout="wide")


BG = "#12151C"
SURFACE = "#1B1F2A"
AMBER = "#FFB347"
TEAL = "#4EC9B0"
TEXT = "#E8E6E1"
MUTED = "#8B92A5"
GRID_COLOR = "#2A2F3D"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;500&display=swap');

    .stApp {{
        background-color: {BG};
        color: {TEXT};
    }}

    h1, h2, h3 {{
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: 0.02em;
    }}

    h1 {{
        color: {AMBER} !important;
    }}

    h2, h3 {{
        color: {TEXT} !important;
        text-transform: uppercase;
        font-size: 1.1rem !important;
        border-left: 3px solid {AMBER};
        padding-left: 0.6rem;
    }}

    p, span, div, label {{
        font-family: 'Inter', sans-serif;
    }}

    /* Metric cards */
    [data-testid="stMetric"] {{
        background-color: {SURFACE};
        border: 1px solid {GRID_COLOR};
        border-radius: 4px;
        padding: 1rem 1.2rem;
        position: relative;
    }}
    [data-testid="stMetric"]::before {{
        content: "";
        position: absolute;
        top: 0; left: 0;
        width: 10px; height: 10px;
        border-top: 2px solid {AMBER};
        border-left: 2px solid {AMBER};
    }}
    [data-testid="stMetricValue"] {{
        font-family: 'JetBrains Mono', monospace !important;
        color: {AMBER} !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: {MUTED} !important;
        text-transform: uppercase;
        font-size: 0.75rem !important;
        letter-spacing: 0.05em;
    }}

    /* Captions */
    [data-testid="stCaptionContainer"] {{
        color: {MUTED} !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.8rem !important;
    }}

    hr {{
        border-color: {GRID_COLOR} !important;
    }}

    /* Live pulse indicator */
    .live-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: {TEAL};
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: -0.5rem;
        margin-bottom: 1rem;
    }}
    .live-dot {{
        width: 8px; height: 8px;
        border-radius: 50%;
        background-color: {TEAL};
        box-shadow: 0 0 0 0 rgba(78, 201, 176, 0.7);
        animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
        0% {{ box-shadow: 0 0 0 0 rgba(78, 201, 176, 0.6); }}
        70% {{ box-shadow: 0 0 0 8px rgba(78, 201, 176, 0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(78, 201, 176, 0); }}
    }}
</style>
""", unsafe_allow_html=True)


def apply_theme(fig):
    """Applies the dashboard's dark HUD theme to a plotly figure."""
    fig.update_layout(
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family="Inter, sans-serif", color=TEXT, size=12),
        legend=dict(bgcolor=SURFACE, font=dict(color=TEXT)),
        margin=dict(t=30, l=10, r=10, b=10),
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, color=MUTED)
    fig.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, color=MUTED)
    return fig


NON_GAME_GENRES = [
    "Animation & Modeling", "Design & Illustration", "Photo Editing",
    "Utilities", "Video Production", "Audio Production", "Software Training",
]


def get_db_config():
    """
    Builds DB connection config from environment variables or Streamlit's
    secrets manager, depending on where this is running.

    Locally: reads from .env via python-dotenv (already loaded above).
    On Streamlit Community Cloud: secrets are set in the app's dashboard
    under Settings > Secrets, and become available via st.secrets instead
    of a local .env file (Community Cloud doesn't read .env files).
    """
    try:
        has_cloud_secrets = "DB_HOST" in st.secrets
    except Exception:
       
        has_cloud_secrets = False

    if has_cloud_secrets:
        return {
            "host": st.secrets["DB_HOST"],
            "user": st.secrets["DB_USER"],
            "password": st.secrets["DB_PASSWORD"],
            "database": st.secrets["DB_NAME"],
            "port": int(st.secrets["DB_PORT"]),
            "ssl_ca": "ca.pem",
        }
    return {
        "host": os.getenv("DB_HOST"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
        "port": int(os.getenv("DB_PORT", 3306)),
        "ssl_ca": os.getenv("DB_SSL_CA", "ca.pem"),
    }


@st.cache_data(ttl=3600) 
def load_data():
    conn = mysql.connector.connect(**get_db_config())
    df = pd.read_sql("SELECT * FROM games_clean", conn)
    conn.close()
    return df


def get_gemini_api_key():
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

    return os.getenv("GEMINI_API_KEY")


@st.cache_data(ttl=86400)
def generate_ai_insights(summary):

    api_key = get_gemini_api_key()

    if not api_key:
        return None

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
You are a senior gaming data analyst.

You are given statistical summaries produced from a Steam analytics pipeline.

Your task is to write an executive summary for a dashboard.

Requirements:
- Write exactly 3–4 sentences.
- Mention specific numbers from the data.
- Highlight the biggest trend.
- Mention one interesting insight.
- Suggest one possible business implication.
- Do NOT invent statistics.
- Keep it professional and concise.

Statistics:

{summary}
"""

    try:
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"(AI insights unavailable: {e})"



df = load_data()
df_games = df[~df["genre"].isin(NON_GAME_GENRES)]

st.title("Steam Player Engagement Analytics")
st.markdown(
    f'<div class="live-badge"><span class="live-dot"></span>'
    f'LIVE — LAST UPDATED {df_games["pulled_at"].max().strftime("%b %d, %Y %H:%M UTC")}</div>',
    unsafe_allow_html=True,
)
st.caption(
    "Tracking real-time player counts, genres, and pricing across popular Steam games, "
    "updated daily via an automated pipeline (Steam API + SteamSpy → MySQL)."
)


col1, col2, col3 = st.columns(3)
col1.metric("Unique Games Tracked", df_games["app_id"].nunique())
col2.metric("Genres Covered", df_games["genre"].nunique())
col3.metric("Total Snapshots Collected", df_games["pulled_at"].nunique())

st.divider()


st.subheader("Average Player Count by Genre")
genre_stats = (
    df_games.groupby("genre")["current_players"]
    .agg(mean="mean", median="median", games="count")
    .round(0)
    .sort_values("mean", ascending=False)
    .reset_index()
)

fig_genre = px.bar(
    genre_stats, x="mean", y="genre", orientation="h",
    hover_data=["median", "games"],
    labels={"mean": "Average Current Players", "genre": "Genre"},
    color_discrete_sequence=[AMBER],
)
fig_genre.update_layout(yaxis={"categoryorder": "total ascending"})
fig_genre = apply_theme(fig_genre)
st.plotly_chart(fig_genre, use_container_width=True)
st.caption(
    "Hover over each bar to see the median and number of games behind that average -- "
    "genres with very few games (shown in the 'games' count) are less statistically reliable."
)

st.divider()


st.subheader("Price vs Current Players")
fig_price = px.scatter(
    df_games, x="price_usd", y="current_players", color="is_free",
    hover_data=["name"],
    labels={"price_usd": "Price (USD)", "current_players": "Current Players", "is_free": "Free to Play"},
    color_discrete_map={0: TEAL, 1: AMBER},
)
fig_price = apply_theme(fig_price)
st.plotly_chart(fig_price, use_container_width=True)
st.caption(
    "Free-to-play titles tend to draw far larger concurrent player counts than paid games. "
    "Within paid games, price alone doesn't show a clear relationship to player count."
)

st.divider()


st.subheader("Top 10 Games by Peak Concurrent Players")
top_games = (
    df_games.groupby("name")["current_players"]
    .max()
    .sort_values(ascending=False)
    .head(10)
    .reset_index()
)
fig_top = px.bar(top_games, x="current_players", y="name", orientation="h", color_discrete_sequence=[TEAL])
fig_top.update_layout(yaxis={"categoryorder": "total ascending"})
fig_top = apply_theme(fig_top)
st.plotly_chart(fig_top, use_container_width=True)

st.divider()


st.subheader("Free vs Paid: Average Player Count")
free_vs_paid = (
    df_games.groupby("is_free")["current_players"]
    .mean()
    .round(0)
    .reset_index()
)
free_vs_paid["is_free"] = free_vs_paid["is_free"].map({0: "Paid", 1: "Free"})
fig_fvp = px.bar(
    free_vs_paid, x="is_free", y="current_players",
    labels={"is_free": "", "current_players": "Average Players"},
    color="is_free", color_discrete_map={"Paid": TEAL, "Free": AMBER},
)
fig_fvp = apply_theme(fig_fvp)
fig_fvp.update_layout(showlegend=False)
st.plotly_chart(fig_fvp, use_container_width=True)

st.divider()


st.subheader("AI Analysis")
api_key = get_gemini_api_key()

if not api_key:
    st.info(
        "Add a GEMINI_API_KEY to your .env (locally) or Streamlit secrets "
    "to enable AI-generated insights."
    )
else:
    summary = f"""
DATASET SUMMARY

Games tracked: {df_games['app_id'].nunique()}

Genres:
{genre_stats.head(8).to_string(index=False)}

Top Games:
{top_games.to_string(index=False)}

Free vs Paid:
{free_vs_paid.to_string(index=False)}

Highest priced game:
{df_games.loc[df_games.price_usd.idxmax()]['name']}
Price:
${df_games.price_usd.max():.2f}

Average game price:
${df_games.price_usd.mean():.2f}

Median player count:
{int(df_games.current_players.median())}
"""

    with st.spinner("Generating insights..."):
        insight_text = generate_ai_insights(summary)

    if insight_text:
        st.markdown(
            f'<div style="background-color:{SURFACE}; border-left:3px solid {TEAL}; '
            f'padding:1rem 1.2rem; border-radius:4px; font-family:Inter, sans-serif;">'
            f'{insight_text}</div>',
            unsafe_allow_html=True,
        )
        st.caption(
    "Generated by Google Gemini based on this dashboard's live analytics. "
    "Refreshes at most once every 24 hours."
)


st.subheader("Player Trends Over Time")
unique_days = df_games["pulled_at"].dt.date.nunique()

if unique_days < 3:
    st.info(
        f"This chart needs at least a few days of collected data to show a meaningful trend. "
        f"Currently tracking {unique_days} day(s) -- the daily automated pipeline is running, "
        f"so check back soon as more history builds up."
    )
else:
    daily_avg = (
        df_games.groupby(df_games["pulled_at"].dt.date)["current_players"]
        .mean()
        .reset_index()
    )
    fig_trend = px.line(daily_avg, x="pulled_at", y="current_players", markers=True)
    fig_trend.update_traces(line_color=AMBER, marker_color=AMBER)
    fig_trend = apply_theme(fig_trend)
    st.plotly_chart(fig_trend, use_container_width=True)

st.caption("Data sourced from the Steam Web API and SteamSpy. Player counts are live concurrent counts, not total sales figures.")
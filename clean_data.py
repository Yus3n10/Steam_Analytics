"""
clean_data.py

Reads from games_raw, cleans and reshapes the data, and loads the result
into games_clean. Run this after fetch_steam_data.py has added new rows.

What this script does, and why:
1. Splits the combined "genres" string (e.g. "Action, RPG, Indie") into
   separate rows -- one row per (game, genre, pulled_at) combination.
   This is necessary because a game like "The Sims 4" belongs to multiple
   genres, and for genre-level analysis (e.g. "average players by genre"),
   we need one genre per row, not a comma-jammed string.
2. Converts release_date from text (e.g. "Dec 21, 2017") into a real DATE
   type, so we can later sort/filter/compute "days since release."
3. Skips rows with no genre or no release date at all, since those can't
   be meaningfully analyzed -- but we count and report how many we skip,
   rather than silently dropping them (this is the kind of data-quality
   transparency worth mentioning in your project README).
4. We do NOT deduplicate across pulled_at -- each pull is a snapshot in
   time, and collapsing them would destroy the time-series data we're
   building up daily.
"""

import os
from datetime import datetime
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

USE_CLOUD_DB = os.getenv("USE_CLOUD_DB", "false").lower() == "true"

if USE_CLOUD_DB:
    DB_CONFIG = {
        "host": os.getenv("DB_HOST"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
        "port": int(os.getenv("DB_PORT", 3306)),
        "ssl_ca": os.getenv("DB_SSL_CA", "ca.pem"),
    }
else:
    DB_CONFIG = {
        "host": os.getenv("DB_HOST_LOCAL", "localhost"),
        "user": os.getenv("DB_USER_LOCAL", "root"),
        "password": os.getenv("DB_PASSWORD_LOCAL", ""),
        "database": os.getenv("DB_NAME_LOCAL", "steam_analytics"),
        "port": int(os.getenv("DB_PORT_LOCAL", 3306)),
    }


def parse_release_date(date_str):
    """
    Converts Steam's release date format ("Dec 21, 2017") into a Python
    date object. Returns None if it can't be parsed (e.g. "Coming soon",
    or a blank value) -- callers should skip rows where this returns None.
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%b %d, %Y").date()
    except ValueError:
        # Some games show non-standard strings like "Coming soon" or a
        # quarter/year only (e.g. "Q4 2026") -- these aren't real dates
        return None


def clean_and_load():
    conn = mysql.connector.connect(**DB_CONFIG)
    read_cursor = conn.cursor(dictionary=True)
    write_cursor = conn.cursor()

    read_cursor.execute("SELECT * FROM games_raw")
    raw_rows = read_cursor.fetchall()
    print(f"Read {len(raw_rows)} rows from games_raw.")

    clean_rows = []
    skipped_no_genre = 0
    skipped_no_date = 0

    for row in raw_rows:
        parsed_date = parse_release_date(row["release_date"])
        if parsed_date is None:
            skipped_no_date += 1
            continue

        if not row["genres"]:
            skipped_no_genre += 1
            continue

        # Split "Action, RPG, Indie" into ["Action", "RPG", "Indie"]
        genre_list = [g.strip() for g in row["genres"].split(",") if g.strip()]

        for genre in genre_list:
            clean_rows.append((
                row["app_id"],
                row["name"],
                genre,
                row["price_usd"],
                row["is_free"],
                parsed_date,
                row["developer"],
                row["current_players"],
                row["pulled_at"],
            ))

    print(f"Skipped {skipped_no_date} rows with unparseable release dates.")
    print(f"Skipped {skipped_no_genre} rows with no genre listed.")
    print(f"Prepared {len(clean_rows)} clean rows (one per game-genre pair).")

    # Clear old clean data before reloading (games_clean is a derived table --
    # always safe to rebuild it fully from games_raw, since games_raw is our
    # source of truth)
    write_cursor.execute("DELETE FROM games_clean")

    insert_query = """
        INSERT INTO games_clean
        (app_id, name, genre, price_usd, is_free, release_date, developer, current_players, pulled_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    write_cursor.executemany(insert_query, clean_rows)
    conn.commit()

    print(f"Inserted {len(clean_rows)} rows into games_clean.")

    read_cursor.close()
    write_cursor.close()
    conn.close()


if __name__ == "__main__":
    clean_and_load()
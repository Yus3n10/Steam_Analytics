"""
fetch_steam_data.py

Pulls game data from Steam's public API and stores it in a MySQL database
(via XAMPP). Run this daily to build up a history of player counts over time.

Beginner notes are included as comments throughout.
"""

import requests
import time
import os
from datetime import datetime
import mysql.connector
from dotenv import load_dotenv

# Load DB credentials from .env file (never hardcode passwords in code)
load_dotenv()

# USE_CLOUD_DB=true connects to Aiven (for GitHub Actions / production runs).
# USE_CLOUD_DB=false (or unset) connects to your local XAMPP MySQL (for
# testing on your own machine). This lets you use the same script for both.
USE_CLOUD_DB = os.getenv("USE_CLOUD_DB", "false").lower() == "true"

if USE_CLOUD_DB:
    DB_CONFIG = {
        "host": os.getenv("DB_HOST"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
        "port": int(os.getenv("DB_PORT", 3306)),
        "ssl_ca": os.getenv("DB_SSL_CA", "ca.pem"),  # Aiven requires SSL
    }
else:
    DB_CONFIG = {
        "host": os.getenv("DB_HOST_LOCAL", "localhost"),
        "user": os.getenv("DB_USER_LOCAL", "root"),
        "password": os.getenv("DB_PASSWORD_LOCAL", ""),
        "database": os.getenv("DB_NAME_LOCAL", "steam_analytics"),
        "port": int(os.getenv("DB_PORT_LOCAL", 3306)),
    }

# --- CONFIG: which games to pull ---
# Instead of pulling all ~150,000 Steam apps (way too slow for a first run),
# we hand-pick a starter list of well-known app IDs. You can expand this list
# later, or pull dynamically from GetAppList once your pipeline works.
STARTER_APP_IDS = [
    730,     # Counter-Strike 2
    570,     # Dota 2
    578080,  # PUBG: BATTLEGROUNDS
    1172470, # Apex Legends
    271590,  # GTA V
    1091500, # Cyberpunk 2077
    1245620, # Elden Ring
    252490,  # Rust
    1938090, # Call of Duty
    1085660, # Destiny 2
    440,     # Team Fortress 2
    413150,  # Stardew Valley
    1174180, # Red Dead Redemption 2
    381210,  # Dead by Daylight
    1085660, # Destiny 2 (dup intentionally removed below via set())
]
STARTER_APP_IDS = list(set(STARTER_APP_IDS))  # remove duplicates


def get_app_details(app_id):
    """
    Calls Steam's appdetails endpoint for one game.
    Returns a dict of relevant fields, or None if the app has no data
    (common for delisted games, DLC, or non-game software).
    """
    url = "https://store.steampowered.com/api/appdetails"
    params = {"appids": app_id, "cc": "us", "l": "en"}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"  [!] Request failed for app_id {app_id}: {e}")
        return None

    app_data = data.get(str(app_id))
    if not app_data or not app_data.get("success"):
        print(f"  [!] No data returned for app_id {app_id} (may be delisted/invalid)")
        return None

    details = app_data["data"]

    # Some fields are missing depending on the game, so we use .get() with
    # defaults everywhere instead of direct dictionary access (which would
    # crash the script on missing keys).
    genres_list = details.get("genres", [])
    genres_str = ", ".join([g["description"] for g in genres_list]) if genres_list else None

    price_info = details.get("price_overview", {})
    price_usd = price_info.get("final", 0) / 100 if price_info else 0.0  # Steam gives cents

    return {
        "app_id": app_id,
        "name": details.get("name", "Unknown"),
        "genres": genres_str,
        "price_usd": price_usd,
        "is_free": details.get("is_free", False),
        "release_date": details.get("release_date", {}).get("date", None),
        "developer": ", ".join(details.get("developers", [])) if details.get("developers") else None,
    }


def get_current_players(app_id):
    """
    Calls Steam's GetNumberOfCurrentPlayers endpoint.
    Returns an integer player count, or None if unavailable.
    """
    url = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
    params = {"appid": app_id}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("response", {}).get("player_count", None)
    except requests.exceptions.RequestException as e:
        print(f"  [!] Player count request failed for app_id {app_id}: {e}")
        return None


def save_to_database(records):
    """
    Inserts a list of game record dicts into the games_raw MySQL table.
    """
    if not records:
        print("No records to save.")
        return

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    insert_query = """
        INSERT INTO games_raw
        (app_id, name, genres, price_usd, is_free, release_date, developer, current_players)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    for record in records:
        cursor.execute(insert_query, (
            record["app_id"],
            record["name"],
            record["genres"],
            record["price_usd"],
            record["is_free"],
            record["release_date"],
            record["developer"],
            record["current_players"],
        ))

    conn.commit()
    print(f"Inserted {len(records)} records into games_raw.")
    cursor.close()
    conn.close()


def main():
    print(f"Starting Steam data pull at {datetime.now()}")
    all_records = []

    for app_id in STARTER_APP_IDS:
        print(f"Fetching app_id {app_id}...")

        details = get_app_details(app_id)
        if details is None:
            continue  # skip games with no usable data

        player_count = get_current_players(app_id)
        details["current_players"] = player_count

        all_records.append(details)

        # IMPORTANT: Steam will rate-limit or temporarily block you if you
        # call too fast. This pause keeps you well under their limits.
        time.sleep(1.5)

    save_to_database(all_records)
    print(f"Done. {len(all_records)} games processed.")


if __name__ == "__main__":
    main()
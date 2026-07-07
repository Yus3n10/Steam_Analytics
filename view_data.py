"""
view_data.py

Quick read-only script to peek at what's in your games_raw table.
Run this anytime you want to sanity-check your data without a GUI tool.
"""

import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "ssl_ca": os.getenv("DB_SSL_CA", "ca.pem"),
}


def view_table(table_name="games_raw", limit=20):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)  # dictionary=True gives column names

    cursor.execute(f"SELECT COUNT(*) as total FROM {table_name}")
    total = cursor.fetchone()["total"]
    print(f"Total rows in {table_name}: {total}\n")

    cursor.execute(f"SELECT * FROM {table_name} ORDER BY pulled_at DESC LIMIT {limit}")
    rows = cursor.fetchall()

    for row in rows:
        print(row)
        print("-" * 80)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    view_table()
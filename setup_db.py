"""
setup_db.py

One-time script: connects to your Aiven MySQL service and runs schema.sql
to create the database and tables. Run this once, then you won't need it
again (unless you change the schema).
"""

import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "ssl_ca": os.getenv("DB_SSL_CA", "ca.pem"),

}


def run_schema_file(filepath="schema.sql"):
    with open(filepath, "r") as f:
        sql_script = f.read()

  
    statements = [s.strip() for s in sql_script.split(";") if s.strip()]

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    for statement in statements:
        print(f"Running: {statement[:60]}...")
        cursor.execute(statement)

    conn.commit()
    cursor.close()
    conn.close()
    print("Schema setup complete.")


if __name__ == "__main__":
    run_schema_file()
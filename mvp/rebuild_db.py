import os
import sqlite3

def rebuild_db():
    DB_PATH = "/home/leeha/tools/sqlite/synth_ehr.db"
    SCHEMA_PATH = "/home/leeha/tools/sqlite/schema.sql"

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)

    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())

    conn.close()

    print("Database rebuilt successfully.")

    return DB_PATH
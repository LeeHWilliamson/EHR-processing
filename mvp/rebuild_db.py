import os
import sqlite3
from pathlib import Path

def rebuild_db(schema : str):
    DB_PATH_PREFIX = "/home/leeha/tools/sqlite/"
    SCHEMA_PATH_PREFIX = "mvp/schemas"
    schema_path = Path(SCHEMA_PATH_PREFIX  / fr"{schema}.sql")
    db_path = Path(DB_PATH_PREFIX / fr"{schema}.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)

    with open(schema_path, "r") as f:
        conn.executescript(f.read())

    conn.close()

    print(f"{schema} database rebuilt successfully.")

    return db_path
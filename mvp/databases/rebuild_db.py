import sqlite3
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = MODULE_DIR / "schemas"
DB_DIR = Path("/home/leeha/tools/sqlite")


def rebuild_db(schema: str):
    # Resolve resources from this module, not from the caller's working directory.
    schema_path = SCHEMA_DIR / f"{schema}.sql"
    db_path = DB_DIR / f"{schema}.db"
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)

    with open(schema_path, "r") as f:
        conn.executescript(f.read())

    conn.close()

    print(f"{schema} database rebuilt successfully.")

    return db_path

if __name__ == "__main__":
    path = rebuild_db("flat_v1")
    print(path)
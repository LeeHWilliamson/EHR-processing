import json
import sqlite3
from pathlib import Path
import traceback
from rebuild_db import rebuild_db
from insert_patient_sqlite3 import insert_patient

# DB_PATH = "/home/leeha/tools/sqlite/synth_ehr.db"
PATIENT_JSON_DIR = "synthea/output/json"
DB_PATH = rebuild_db()

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")

for json_folder in Path(PATIENT_JSON_DIR).glob("*"):
    with open(json_folder/"patient.json", "r") as file:
        patient = json.load(file)
        print(patient["patient"]["firstName"])
        try:
            insert_patient(conn, patient)
        except Exception as e:
            print(e)
            traceback.print_exc()
            continue

conn.close()
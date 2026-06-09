import json
import sqlite3
from pathlib import Path

from insert_patient_sqlite3 import insert_patient

DB_PATH = "/home/leeha/tools/sqlite/synth_ehr.db"
PATIENT_JSON_DIR = "synthea/output/json"

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")

for json_folder in Path(PATIENT_JSON_DIR).glob("*"):
    with open(json_folder/"patient.json", "r") as file:
        patient = json.load(file)
        print(patient["patient"]["firstName"])
        insert_patient(conn, patient)

conn.close()
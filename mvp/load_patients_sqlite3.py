import json
import sqlite3
from pathlib import Path
import traceback
from .rebuild_db import rebuild_db
# from .insert_patient_sqlite3 import insert_patient
from .schema_adapters import flat_v1, normalized_v1

# DB_PATH = "/home/leeha/tools/sqlite/synth_ehr.db"
# SCHEMA_NAMES = ["normalized_v1", "flat_v1"]
PATIENT_JSON_DIR = "synthea/output/json"
def main(schemas : list[str]):
    # schema_path = Path("mvp/schemas") / f"{schema}.sql"
    for schema in schemas:
        db_path = rebuild_db(schema = schema)

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")

        for json_folder in Path(PATIENT_JSON_DIR).glob("*"):
            with open(json_folder/"patient.json", "r") as file:
                patient = json.load(file)
                print(patient["patient"]["firstName"])
                try:
                    if schema == "normalized_v1":
                        normalized_v1.insert_patient(conn, patient)
                    else: 
                        flat_v1.insert_patient(conn, patient)
                    # insert_patient(conn, patient)
                except Exception as e:
                    print(e)
                    traceback.print_exc()
                    continue

        conn.close()
if __name__ == "__main__":
    main()
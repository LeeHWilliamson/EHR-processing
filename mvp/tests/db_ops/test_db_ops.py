'''
In this script we demonstrate that our agent tools return the same database information regardless of the database schema
Currently, our agent tool get_patient takes a patient_id as an argument and queries the database to return 6 specific fields, the formats and values of which are the same no matter the schema
'''
import json
import sqlite3
from pathlib import Path
from mvp.databases.rebuild_db import rebuild_db
from mvp.databases.schema_adapters import flat_v1 as flat, normalized_v1 as normalized
SCHEMAS = ["flat_v1", "normalized_v1"]
TEST_DATA = Path(__file__).parent.parent / "test_data" / "test_patients"

def test_get_patient():
    #first we build the dbs
    test_patient_path = Path(TEST_DATA / "living_patient_1_med.json")
    for schema in SCHEMAS:
        db_path = rebuild_db(schema)

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")

        #we need to insert 1 normal patient
        with open(test_patient_path, "r") as patient_file:
            patient = json.load(patient_file)
            patient_id = patient["patient"]["id"]
            if schema == "normalized_v1":
                normalized.insert_patient(conn, patient)
                normalized_patient_record = normalized.get_patient(conn, patient_id)
            else: 
                flat.insert_patient(conn, patient)
                flat_patient_record = flat.get_patient(conn, patient_id)
    assert normalized_patient_record == flat_patient_record


def test_get_meds():
    test_patient_path = Path(TEST_DATA / "living_patient_1_med.json")
    for schema in SCHEMAS:
        db_path = rebuild_db(schema)

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")

        #we need to insert 1 normal patient
        with open(test_patient_path, "r") as patient_file:
            patient = json.load(patient_file)
            patient_id = patient["patient"]["id"]
            if schema == "normalized_v1":
                normalized.insert_patient(conn, patient)
                normalized_patient_record = normalized.get_medications(conn, patient_id)
            else: 
                flat.insert_patient(conn, patient)
                flat_patient_record = flat.get_medications(conn, patient_id)
    for record in normalized_patient_record:
        assert record in flat_patient_record
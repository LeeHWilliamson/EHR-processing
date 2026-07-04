import sqlite3
import json
import math

#helper function to deal with nans
def clean_fk(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if value == "nan":
        return None
    return "enc_" + value

def clean_json_value(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {key: clean_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_json_value(item) for item in value]
    if value == "nan":
        return None
    return value


def insert_patient(conn, patient: dict):
    patient_id = patient["patient"]["id"]
    cursor = conn.cursor()
    medication_blob = clean_json_value(patient.get("medications", []))
    #deal with nans, iterate thru all med dicts in med list
    for medication in medication_blob:
        medication["encounter"] = clean_fk(medication["encounter"])
    cursor.execute(
        """
        INSERT INTO patients
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patient["patient"]["id"],
            patient["patient"]["firstName"],
            patient["patient"]["lastName"],
            patient["patient"]["birthdate"],
            patient["patient"]["deathdate"],
            patient["patient"]["gender"],
            json.dumps(medication_blob, allow_nan=False)
        )
    )

    conn.commit()

def get_patient(conn, patient_id : str):
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, firstName, lastName, birthdate, deathdate, gender FROM patients WHERE id = ?",
        (patient_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    
    patient = dict(row)
    return patient

def get_medications(conn, patient_id: str):
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT medications_blob FROM patients WHERE id = ?",
        (patient_id,),
    )

    row = cursor.fetchone()

    if row is None:
        return []
    
    return json.loads(row["medications_blob"])

# if __name__ == "__main__":
    # conn = sqlite3.connect(r"/home/leeha/tools/sqlite/flat_v1.db")
    # with open("synthea/output/json/35045da5-4c6b-9fae-b7c9-7d4225b2f367/patient.json", "r") as file:
    #     patient = json.load(file)
    # insert_patient(conn, patient)

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


def insert_patient(conn, patient: dict):
    patient_id = patient["patient"]["id"]
    cursor = conn.cursor()
    medication_blob = patient.get("medications", [])
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
            json.dumps(medication_blob)
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
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
    blob_dict = {}
    blob_dict["encounters_blob"] = clean_json_value(patient.get("encounters", []))
    blob_dict["allergies_blob"] = clean_json_value(patient.get("allergies", []))
    blob_dict["careplans_blob"] = clean_json_value(patient.get("careplans", []))
    blob_dict["devices_blob"] = clean_json_value(patient.get("devices", []))
    blob_dict["conditions_blob"] = clean_json_value(patient.get("conditions", []))
    blob_dict["immunizations_blob"] = clean_json_value(patient.get("immunizations", []))
    blob_dict["medications_blob"] = clean_json_value(patient.get("medications", []))
    blob_dict["procedures_blob"] = clean_json_value(patient.get("procedures", []))
    blob_dict["observations_blob"] = clean_json_value(patient.get("observations", []))
    #deal with nans and make foreign keys match the normalized schema
    for blob_name, records in blob_dict.items():
        if blob_name == "encounters_blob":
            continue
        for record in records:
            record["encounter"] = clean_fk(record["encounter"])

    #SQLite returns values in TEXT columns as strings in the normalized schema
    for medication in blob_dict["medications_blob"]:
        if medication["code"] is not None:
            medication["code"] = str(medication["code"])
    cursor.execute(
        """
        INSERT INTO patients
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            patient["patient"]["id"],
            patient["patient"]["firstName"],
            patient["patient"]["lastName"],
            patient["patient"]["birthdate"],
            patient["patient"]["deathdate"],
            patient["patient"]["gender"],
            json.dumps(blob_dict["encounters_blob"], allow_nan=False),
            json.dumps(blob_dict["allergies_blob"], allow_nan=False),
            json.dumps(blob_dict["careplans_blob"], allow_nan=False),
            json.dumps(blob_dict["devices_blob"], allow_nan=False),
            json.dumps(blob_dict["conditions_blob"], allow_nan=False),
            json.dumps(blob_dict["immunizations_blob"], allow_nan=False),
            json.dumps(blob_dict["medications_blob"], allow_nan=False),
            json.dumps(blob_dict["procedures_blob"], allow_nan=False),
            json.dumps(blob_dict["observations_blob"], allow_nan=False)
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

def get_encounters(conn, patient_id: str):
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, encounters_blob FROM patients WHERE id = ?",
                   (patient_id,),
    )

    row = cursor.fetchone()

    if row is None:
        return []

    encounters_blob = json.loads(row["encounters_blob"])
    for encounter in encounters_blob: 
        encounter["patient_id"] = patient_id

    return encounters_blob

def get_allergies(conn, patient_id: str):
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, allergies_blob FROM patients WHERE id = ?",
        (patient_id,),
    )

    row = cursor.fetchone()

    if row is None:
        return []

    allergies_blob = json.loads(row["allergies_blob"])
    for allergy in allergies_blob:
        allergy["patient_id"] = patient_id

    return allergies_blob

def get_careplans(conn, patient_id: str):
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, careplans_blob FROM patients WHERE id = ?",
        (patient_id,),
    )

    row = cursor.fetchone()

    if row is None:
        return []

    careplans_blob = json.loads(row["careplans_blob"])
    for careplan in careplans_blob:
        careplan["patient_id"] = patient_id

    return careplans_blob

def get_devices(conn, patient_id: str):
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, devices_blob FROM patients WHERE id = ?",
        (patient_id,),
    )

    row = cursor.fetchone()

    if row is None:
        return []

    devices_blob = json.loads(row["devices_blob"])
    for device in devices_blob:
        device["patient_id"] = patient_id

    return devices_blob

def get_conditions(conn, patient_id: str):
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, conditions_blob FROM patients WHERE id = ?",
        (patient_id,),
    )

    row = cursor.fetchone()

    if row is None:
        return []

    conditions_blob = json.loads(row["conditions_blob"])
    for condition in conditions_blob:
        condition["patient_id"] = patient_id

    return conditions_blob

def get_immunizations(conn, patient_id: str):
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, immunizations_blob FROM patients WHERE id = ?",
        (patient_id,),
    )

    row = cursor.fetchone()

    if row is None:
        return []

    immunizations_blob = json.loads(row["immunizations_blob"])
    for immunization in immunizations_blob:
        immunization["patient_id"] = patient_id

    return immunizations_blob

def get_medications(conn, patient_id: str):
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, medications_blob FROM patients WHERE id = ?",
        (patient_id,),
    )

    row = cursor.fetchone()

    if row is None:
        return []

    med_blob = json.loads(row["medications_blob"])
    #make sure to append id so return data is exactly the same as it is for other schemas
    for medication in med_blob:
        medication["patient_id"] = patient_id
        # medication["code"] = str(medication["code"]) #make sure code is str
    
    return med_blob

def get_procedures(conn, patient_id: str):
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, procedures_blob FROM patients WHERE id = ?",
        (patient_id,),
    )

    row = cursor.fetchone()

    if row is None:
        return []

    procedures_blob = json.loads(row["procedures_blob"])
    for procedure in procedures_blob:
        procedure["patient_id"] = patient_id

    return procedures_blob

def get_observations(conn, patient_id: str):
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, observations_blob FROM patients WHERE id = ?",
        (patient_id,),
    )

    row = cursor.fetchone()

    if row is None:
        return []

    observations_blob = json.loads(row["observations_blob"])
    for observation in observations_blob:
        observation["patient_id"] = patient_id

    return observations_blob

if __name__ == "__main__":
    conn = sqlite3.connect(r"/home/leeha/tools/sqlite/flat_v1.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(patients);")
    row = cursor.fetchall()
    print(row)
    with open("/home/leeha/Projects/EHR-processing/mvp/tests/test_data/test_patients/living_patient_0_meds.json", "r") as file:
        patient = json.load(file)
    insert_patient(conn, patient)

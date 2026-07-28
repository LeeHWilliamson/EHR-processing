'''
This script will insert all information for 1 patient into the sqlite DB
input: a DB connection and patient JSON (as dict)
output: none
'''
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

#data will be a single entity from the patient JSON
def insert_dict(cursor, table_name, data):
    columns = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data) #make a "?, " for each field in the dict

    query = f"""
    INSERT INTO {table_name}
    ({columns})
    VALUES ({placeholders})
    """

    # print(query)
    # print(data)
    cursor.execute(query, tuple(data.values()))

def insert_patient(conn, patient: dict):
    patient_id = patient["patient"]["id"]
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO patients
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            patient["patient"]["id"],
            patient["patient"]["firstName"],
            patient["patient"]["lastName"],
            patient["patient"]["birthdate"],
            patient["patient"]["deathdate"],
            patient["patient"]["gender"]
        )
    )
    # MANUALLY WRITE OUT INSERT FOR ENCOUNTERS AS WELL :/
    #  1. Insert encounters first
    for encounter in patient.get("encounters", []):
        row = encounter.copy()
        row["patient_id"] = patient_id
        insert_dict(cursor, "encounters", row)

    #DEBUG check that encounters were inserted
    # cursor.execute("SELECT COUNT(*) FROM encounters")
    # print("Encounter count:", cursor.fetchone()[0]) 
    
    #all other tables

    # # for entity in patient: #keys like 'observations' 'medications' etc
    #     if isinstance(patient[entity], list):
    #         for entity_instance in patient[entity]: #each entity is a list of dicts
    #             row = entity_instance.copy()
    #             row["patient_id"] = patient_id
    #             row["encounter"] = "enc_" + row["encounter"]
    #             insert_dict(cursor, table_name=entity, data=row)
        # 2. Then insert tables that reference patients/encounters
    child_tables = [
        "allergies",
        "careplans",
        "conditions",
        "devices",
        "immunizations",
        "medications",
        "observations",
        "procedures",
    ]

    for table in child_tables:
        for item in patient.get(table, []):
            row = item.copy()
            row["patient_id"] = patient_id
            row["encounter"] = clean_fk(row["encounter"])
            insert_dict(cursor, table, row)



    conn.commit()
    # conn.close()

def get_patient(conn, patient_id: str):
    #specify the format that rows are returned in
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM patients WHERE id = ?",
        (patient_id,),
    )
    #id is the primary key that corresponds to a specific patient, so row should only contain 1 record lol
    row = cursor.fetchone()
    if row is None:
        return None
    patient = dict(row)
    return patient

def get_medications(conn, patient_id: str):
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM medications WHERE patient_id = ?",
        (patient_id,),
    )
    rows = cursor.fetchall()
    return [dict(row) for row in rows]
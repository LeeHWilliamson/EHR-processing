'''
This script will insert all information for 1 patient into the sqlite DB
input: a DB connection and patient JSON (as dict)
output: none
'''
import sqlite3
import json

#data will be a single entity from the patient JSON
def insert_dict(cursor, table_name, data):
    columns = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data) #make a "?, " for each field in the dict

    query = f"""
    INSERT INTO {table_name}
    ({columns})
    VALUES ({placeholders})
    """
    print(query)
    cursor.execute(query, tuple(data.values()))

def insert_patient(conn, patient: dict):
    cursor = conn.cursor()

    # cursor.execute(
    #     """
    #     INSERT INTO patients
    #     VALUES (?, ?, ?, ?, ?)
    #     """,
    #     (
    #         patient["patient"]["id"],
    #         patient["patient"]["firstName"],
    #         patient["patient"]["lastName"],
    #         patient["patient"]["dob"],
    #         patient["patient"]["gender"]
    #     )
    # )
    #MANUALLY WRITE OUT INSERT FOR ENCOUNTERS AS WELL :/
     # 1. Insert encounters first
    patient_id = patient["patient"]["id"]
    for encounter in patient.get("encounters", []):
        row = encounter.copy()
        row["patient_id"] = patient_id
        insert_dict(cursor, "encounters", row)


    #all other tables
    
    # for entity in patient: #keys like 'observations' 'medications' etc
    #     if isinstance(patient[entity], list):
    #         for entity_instance in patient[entity]: #each entity is a list of dicts
    #             row = entity_instance.copy()
    #             row["patient_id"] = patient_id
    #             insert_dict(cursor, table_name=entity, data=row)
    #     else:
    #         print(entity, type(entity))
    #         print(type(patient[entity]))
        # 2. Then insert tables that reference patients/encounters
    child_tables = [
        "conditions",
        "observations",
        "medications",
        "allergies",
        "procedures",
        "immunizations",
        "careplans",
        "devices",
    ]

    print("Encounter count:", cursor.fetchone()[0])
    for table in child_tables:
        for item in patient.get(table, []):
            row = item.copy()
            row["patient_id"] = patient_id
            insert_dict(cursor, table, row)




    conn.commit()
    # conn.close()
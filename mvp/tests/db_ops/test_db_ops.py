'''
In this script we demonstrate that our agent tools return the same database information regardless of the database schema
Currently, our agent tool get_patient takes a patient_id as an argument and queries the database to return 6 specific fields, the formats and values of which are the same no matter the schema
'''
import json
import sqlite3
import pytest
from pathlib import Path
from mvp.databases.rebuild_db import rebuild_db
from mvp.databases.schema_adaptors import flat_v1 as flat, normalized_v1 as normalized
SCHEMAS = ["flat_v1", "normalized_v1"]
TEST_DATA = Path(__file__).parent.parent / "test_data" / "test_patients"

TOOLS = {
    "get_patient" : lambda schema, conn, patient_id: schema.get_patient(conn, patient_id),
    "get_allergies" : lambda schema, conn, patient_id: schema.get_allergies(conn, patient_id),
    "get_careplans" : lambda schema, conn, patient_id: schema.get_careplans(conn, patient_id),
    "get_conditions" : lambda schema, conn, patient_id: schema.get_conditions(conn, patient_id),
    "get_devices" : lambda schema, conn, patient_id: schema.get_devices(conn, patient_id),
    "get_immunizations" : lambda schema, conn, patient_id: schema.get_immunizations(conn, patient_id),
    "get_medications" : lambda schema, conn, patient_id: schema.get_medications(conn, patient_id),
    "get_observations" : lambda schema, conn, patient_id: schema.get_observations(conn, patient_id),
    "get_procedures" : lambda schema, conn, patient_id: schema.get_procedures(conn, patient_id),
}

@pytest.mark.parametrize(
        "agent_tool_name",
        [
            "get_patient",
            "get_allergies",
            "get_careplans",
            "get_conditions",
            "get_devices",
            "get_immunizations",
            "get_medications",
            "get_observations",
            "get_procedures",
        ],
)

def test_adapters(agent_tool_name: str):

    #access patient file to insert into db
    test_patient_path = Path(TEST_DATA / "living_patient_1_med.json")
    with open(test_patient_path, "r") as patient_file:
        patient = json.load(patient_file)
        patient_id = patient["patient"]["id"]

    #create databases
    db_paths = {} #schema as str : path as Path
    for schema in SCHEMAS:
            db_path = rebuild_db(schema)
            db_paths[schema] = db_path

    #run tool in normalized database
    conn = sqlite3.connect(db_paths["normalized_v1"])
    conn.execute("PRAGMA foreign_keys = ON")
    normalized.insert_patient(conn, patient)
    normalized_result = TOOLS[agent_tool_name](normalized, conn, patient_id)
    conn.close()

    #run tool in flat database
    conn = sqlite3.connect(db_paths["flat_v1"])
    conn.execute("PRAGMA foreign_keys = ON")
    flat.insert_patient(conn, patient)
    flat_result = TOOLS[agent_tool_name](flat, conn, patient_id)
    conn.close()

    assert normalized_result == flat_result

# def test_get_patient():
#     #first we build the dbs
#     test_patient_path = Path(TEST_DATA / "living_patient_1_med.json")
#     for schema in SCHEMAS:
#         db_path = rebuild_db(schema)

#         conn = sqlite3.connect(db_path)
#         conn.execute("PRAGMA foreign_keys = ON")

#         #we need to insert 1 normal patient
#         with open(test_patient_path, "r") as patient_file:
#             patient = json.load(patient_file)
#             patient_id = patient["patient"]["id"]
#             if schema == "normalized_v1":
#                 normalized.insert_patient(conn, patient)
#                 normalized_patient_record = normalized.get_patient(conn, patient_id)
#             else: 
#                 flat.insert_patient(conn, patient)
#                 flat_patient_record = flat.get_patient(conn, patient_id)
#     assert normalized_patient_record == flat_patient_record


# def test_get_meds():
#     test_patient_path = Path(TEST_DATA / "living_patient_1_med.json")
#     for schema in SCHEMAS:
#         db_path = rebuild_db(schema)

#         conn = sqlite3.connect(db_path)
#         conn.execute("PRAGMA foreign_keys = ON")

#         #we need to insert 1 normal patient
#         with open(test_patient_path, "r") as patient_file:
#             patient = json.load(patient_file)
#             patient_id = patient["patient"]["id"]
#             if schema == "normalized_v1":
#                 normalized.insert_patient(conn, patient)
#                 normalized_patient_record = normalized.get_medications(conn, patient_id)
#             else: 
#                 flat.insert_patient(conn, patient)
#                 flat_patient_record = flat.get_medications(conn, patient_id)
#     for record in normalized_patient_record:
#         assert record in flat_patient_record

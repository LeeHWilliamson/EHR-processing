import json
from pathlib import Path

WEBAPP_DIR = Path(__file__).resolve().parent.parent
PATIENTS_DIR = WEBAPP_DIR / "patients" / "current_run" / "full_patients" / "json"

def query_entities():
    all_possible_entities = {"allergies", "conditions", "encounters", "immunizations",
                             "medications", "procedures", "observations", "careplans", 
                             "devices", "imaging_studies"}
    current_entities = set()
    for patient_fp in PATIENTS_DIR.iterdir():
        with open(patient_fp, "r") as patient_file:
            patient_dict = json.load(patient_file)
        for entity in patient_dict.keys():
            if current_entities == all_possible_entities:
                return current_entities
            if entity in all_possible_entities:
                current_entities.add(entity)
    return current_entities
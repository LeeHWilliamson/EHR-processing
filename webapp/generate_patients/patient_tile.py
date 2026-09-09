'''
api passes patient id
this script uses that patient id to find the patient json and construct a summary
that summary gets passed back to the frontend
'''
import json
from pathlib import Path
from pydantic import BaseModel

WEBAPP_DIR = Path(__file__).resolve().parent.parent
PATIENTS_DIR = WEBAPP_DIR / "patients" / "current_run" / "json"
class PatientSummaryTile(BaseModel):
    first_name: str
    last_name: str
    dob: str
    gender: str
    conditions: int = 0
    careplans: int = 0
    medications: int = 0
    allergies: int = 0
    keep_attributes: list[str]

def generate_tile_summary() -> list[dict]:
    tiles = []
    for patient_path in PATIENTS_DIR.iterdir():
        with open(PATIENTS_DIR / f"{patient_path.name}", "r") as patient_file:
            patient_dict = json.load(patient_file)

        patient = patient_dict["patient"]
        curr_patient_summary = PatientSummaryTile(
            first_name = patient["firstName"],
            last_name = patient["lastName"],
            dob = patient["birthdate"],
            gender = patient["gender"],
            keep_attributes = patient_dict["metadata"]["keep_attributes"]
        )

        for entity, instance_list in patient_dict.items():
            if hasattr(curr_patient_summary, entity):
                for instance in instance_list:
                    if instance.get("endDate") is None:
                        setattr(curr_patient_summary, entity, getattr(curr_patient_summary, entity) + 1)
        tiles.append(curr_patient_summary)
    return tiles

if __name__ == "__main__":
    res = generate_tile_summary(["pat_e2790340-3a92-c6a0-f86c-8e88d386c585"])
    print(res)
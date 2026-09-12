import json
from pathlib import Path
WEBAPP_DIR = Path(__file__).resolve().parent.parent
PATIENTS_DIR = WEBAPP_DIR / "patients" / "current_run" / "full_patients" / "json"
ENTITY_FIELDS_FP = WEBAPP_DIR / "medical_concepts" / "fields_by_entity.json"

#discern which entities are actually present in current patient population
#if any patient has a field, that field is considered present
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

#calculate intersection among selected attributes to see which fields are common among them
#these fields can be used as keys
def get_key_field_options(selected_entities: list[str]):
    with open(ENTITY_FIELDS_FP, "r") as entity_fields_file:
        entity_fields_dict = json.load(entity_fields_file)
    possible_key_fields = set(entity_fields_dict[selected_entities[0]])
    if len(selected_entities) > 1:
        for selected_entity in selected_entities:
            possible_key_fields = possible_key_fields & set(entity_fields_dict[selected_entity])
    return possible_key_fields

#for each attribute selected, we need to display a list of fields
#then the user can select which they want
def get_fields(entity: str):
    with open(ENTITY_FIELDS_FP, "r") as entity_fields_file:
            entity_fields_dict = json.load(entity_fields_file)
    fields = entity_fields_dict[entity].copy()
    return fields


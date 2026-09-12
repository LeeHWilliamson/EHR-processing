import json
from pathlib import Path
'''
key_field is simply the shared field between all attributes affected by tool
entities_and_fields is a dict where each key is an entity str and each value is a list of fields to return from each instance of that
entity that matches the argument passed for the key field
'''
TOOL_TEMPLATE = {
    "name" : None,
    "description" : None,
    "key_field" : None,
    "entities_and_fields" : {}
}
WEBAPP_DIR = Path(__file__).resolve().parent.parent
PATIENTS_DIR = WEBAPP_DIR / "patients" / "current_run" / "full_patients" / "json"
TOOL_FP = WEBAPP_DIR / "patients" / "current_run" / "tools.json"
#we need to create a reference table for each tool, that way if we use a tool such as reason or code, the AGENT can know what possible args exist
#in cases where two entities have identical field names but not always related field values (e.g. reason exists in medication and procedure)
#we only want the tool to target records where the values do line up
def create_tool_arg_reference(key_field: str, entities: list[str]):
    all_vals_reference = {}
    #we will calculate intersection to find what args are valid
    for entity in entities:
        all_vals_reference[entity] = set()
    #first we run through all patients, adding their values from the entities' key_field to their entry in all_vals_reference
    for patient_json in PATIENTS_DIR.iterdir():
        with open(patient_json, "r") as patient_file:
            patient = json.load(patient_file)
        for entity in patient:
            if entity in all_vals_reference:
                for record in patient[entity]:
                    all_vals_reference[entity].add(record[key_field])
    #now we calculate intersections to see what values are actually valid for this tool
    final_reference = set()

def create_tool(name: str, description: str, key_field: str, entities_and_fields: dict[str]):
    if not TOOL_FP.is_file():
        TOOL_FP.touch()

    tool_dict = TOOL_TEMPLATE.copy()
    tool_dict["name"] = name
    tool_dict["key_field"] = key_field
    tool_dict["entities_and_fields"] = entities_and_fields
    tool_dict["description"] = description
    with open(TOOL_FP, "a") as tool_file:
        json.dump(tool_dict, tool_file, indent = 2)
    return tool_dict



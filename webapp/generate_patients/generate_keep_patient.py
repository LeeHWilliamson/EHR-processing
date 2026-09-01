import json
from pathlib import Path
'''
This module will generate synthea keep modules for the specified attribute
for debugging we will just keep these in a local folder called keep_modules,
but when we implement this demo we will keep them in a temporary run directory, and then move them to a run archive

The gestalt of the process is this
we receive an attribute
we load the keep_module template from medical_concepts folder
we load the conditions.json in medical_concepts folder where each item is an attribute_key : [corresponding attribute strs]
for each str in the item, we make a copy of the attribute template, edit the attribute name, and append it to list in the loaded 
        keep_module template under loaded_template[states][Initial][conditional_transition][condition][conditions]
we json dump the result to current output dir and return the dict to calling module
'''
WEBAPP_DIR = Path(__file__).resolve().parent.parent
CURR_RUN_DIR = WEBAPP_DIR / "debug_keep_modules"
MEDICAL_CONCEPTS_PATH = WEBAPP_DIR / "medical_concepts"

ATTRIBUTE_TEMPLATE = {
    "condition_type" : "Attribute",
    "attribute" : None,
    "operator" : "is not nil"
}

def generate_keep_module(attribute: str):
    #load keep_module template so we can add conditions (stored as attributes in synthea) to keep
    keep_module_template_path = MEDICAL_CONCEPTS_PATH / "keep_template.json"
    with open(keep_module_template_path, "r") as keep_template_file:
            keep_module_template = json.load(keep_template_file)
    keep_module_template["name"] = f"keep_{attribute}"
    output_path = CURR_RUN_DIR / f"{keep_module_template["name"]}.json"
    #load list of attributes that we currently have logic to capture
    possible_attributes_path = MEDICAL_CONCEPTS_PATH / "attributes.json"
    with open(possible_attributes_path, "r") as attributes_file:
        attributes_dict = json.load(attributes_file)
    if attribute not in attributes_dict:
        raise KeyError
    #add create keep condition and add it to our template
    for type in attributes_dict[attribute]:
        attribute_to_add = ATTRIBUTE_TEMPLATE.copy()
        attribute_to_add["attribute"] = type
        keep_module_template["states"]["Initial"]["conditional_transition"][0]["condition"]["conditions"].append(attribute_to_add)
    
    with open(output_path, "w") as keep_module_output_file:
         json.dump(keep_module_template, keep_module_output_file, indent = 2)

    return output_path

if __name__ == "__main__":
        keep_module_path = generate_keep_module("diabetes")
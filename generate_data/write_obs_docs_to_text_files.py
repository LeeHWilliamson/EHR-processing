import json

'''
we pass document
we write to text file
'''
def write_text_file(document, patient):
    with open(f"documents/{document["doc_id"]}/document.txt", "w") as file: #create text file corresponding to document
        for key, value in document.items():
            if key == "entities_provided":
                for entity_type, entity_list in document[key].items():
                    for entity_dict in entity_list:
                        observation_id = entity_dict["entity_id"]
                        for obs_dict in patient["observations"]:
                            if obs_dict["id"] == observation_id:
                                for field in obs_dict:
                                    if field in entity_dict["fields"]:
                                        file.write(f"{field} {obs_dict[field]}\n")
            else:
                print(key, value)
                file.write(f"{key} {value}\n")

with open("documents/doc_00ae1551-34ac-497a-9a7b-92ed5a720480/document.json") as file:
    debug_doc = json.load(file)
debug_patient_id = debug_doc["patient_id"].split('_')[1]
with open(f"patients/{debug_patient_id}/patient.json") as file:
    debug_patient = json.load(file)
write_text_file(debug_doc, debug_patient)
import json

'''
we pass document
we write to text file
'''
def write_text_file(document, patient, output_path):
    # patient_id = document["patient_id"].split('_')[1]
    # # with open(f"patients_debug/{patient_id}/patient.json") as file:
    # #     patient = json.load(file)
    with open(f"{output_path}/{document["doc_id"]}/document.txt", "w") as file: #create text file corresponding to document
        for key, value in document.items():
            if key == "entities_provided":
                for entity_type, entity_list in document[key].items():
                    for entity_dict in entity_list:
                        observation_id = entity_dict["entity_id"]
                        for obs_dict in patient["observations"]:
                            if obs_dict["id"] == observation_id:
                                for field in obs_dict:
                                    if field in entity_dict["fields"]:
                                        print("IF", field, obs_dict[field])
                                        file.write(f"{field} {obs_dict[field]}\n")
            else:
                print("ELSE", key, value)
                file.write(f"{key} {value}\n")

# with open("documents/doc_d8013785-081f-4354-b6d9-38506b66254f/document.json") as file:
#     debug_doc = json.load(file)

# write_text_file(debug_doc)
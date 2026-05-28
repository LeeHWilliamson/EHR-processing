'''
This script will reconstruct patient JSONs via document metadata 
input: path to document directory output output: a patient JSON for each patient mentioned across the docs within the directory
'''
from pathlib import Path
import json
import os
import copy

class patient_reconstructor_metadata:
    def __init__(self, doc_directory):
        self. doc_directory = doc_directory

    '''
    load in doc
    create record of all entities and their field keys
    reference associated log to check what entities and fields were ommitted, remove these from loaded doc data object
    reference patient to populate remaining entities and fields
    '''
    def reconstruct_all(self):
        with open(Path("schemas/patient_template.json"), "r") as f: #load datastructure for reconstructed patient
            patient_template = json.load(f)
        reconstructed_patients = {}
        # docs = {}
        #reconstruct patient 1 doc at a time
        for document in os.listdir(self.doc_directory):
            path = os.path.join(self.doc_directory, document, "document.json")
            with open(path, "r") as f:
                loaded_doc = json.load(f)
            #find associated mapping for this doc to extract realized fields and entities
            curr_mapping = None
            for mapping in os.listdir(r"mappings_debug"):
                path = os.path.join(r"mappings_debug", mapping)
                with open(path, "r") as f:
                    possible_mapping = json.load(f)
                if possible_mapping["doc_id"] == loaded_doc["doc_id"]:
                    curr_mapping = possible_mapping
                    break
            if curr_mapping is None:
                continue
            patient_id = loaded_doc["patient_id"]
            if patient_id not in reconstructed_patients:
                reconstructed_patients[patient_id] = copy.deepcopy(patient_template)
            # reconstructed_patients[patient_id] = patient_template.copy()
                reconstructed_patients[patient_id]["patient"]["id"] = patient_id
            with open(rf"patients_debug/{patient_id[4:]}/patient.json", "r") as f:
                patient = json.load(f)
            #entity_type = category e.g. observations, each item within a category should be a dict...
            for entity_type in curr_mapping["field_expectations"]:
                for entity_id, expectation in curr_mapping["field_expectations"][entity_type].items():
                    #get list of all fields that were rendered
                    realized_fields = expectation["realized_fields"]
                    for entity_instance in patient[entity_type]:
                        if entity_instance["id"] != entity_id:
                            continue

                        entity_dict = {"id" : entity_id}
                        for field in realized_fields:
                            entity_dict[field] = entity_instance[field]

                        existing = next(
                            (e for e in reconstructed_patients[patient_id][entity_type] if e["id"] == entity_id),
                            None
                        )
                        if existing is None:
                            reconstructed_patients[patient_id][entity_type].append(entity_dict)
                        else:
                            existing.update(entity_dict)
                        break
                        
                    # for field in realized_fields:
                    #     reconstructed_patients[patient_id][entity_type][entity_id][field] = patient[entity_type][entity_id][field]
            for patient in reconstructed_patients:
                with open(f"reconstructed_patients/{reconstructed_patients[patient]["patient"]["id"]}", "w") as f:
                    json.dump(reconstructed_patients[patient], f, indent=2)
        #     doc_id = loaded_doc["doc_id"]
        #     docs[doc_id] = {}
        #     docs[doc_id]["patient_id"] = loaded_doc["patient_id"]
        #     docs[doc_id]["entities_provided"] = {}
        #     for entity_type in loaded_doc["entities_provided"]:
        #         docs[doc_id]["entities_provided"] = loaded_doc["entities_provided"] #just copy the whole dictionary over, it contains all entities and fields that should be present
        # #check which fields were ommitted in this run
        # for mapping in os.listdir(r"mappings_debug"):
        #     path = os.path.join(r"mappings_debug", mapping)
        #     entities = {} #we will use this to track entities and their fields to see which were ommitted
        #     with open(path, "r") as f:
        #         curr_mapping = json.load(f)
        #     if curr_mapping["doc_id"] in docs:
        #         doc_id = curr_mapping["doc_id"]
        #     ommitted_entities = curr_mapping["omitted_entities"]
        #     if ommitted_entities != "none":
        #         #check if any whole fields were ommitted 
        #         # for entity_type in docs[doc_id]: #doc_id, patient_id, entities_provided, etc
        #         #     for entity_instance in entity_type:
        #         #         if entity_instance["entity_id"] in ommitted_entities:
        #         #             docs[doc_id]["entities_provided"][entity_type].pop(entity_instance["entity_id"])
        #         #for each entity type, iterate thru instances to find those that were ommitted
        #         for entity_type in docs[doc_id]["entities_provided"]:
        #             for entity_instance in entity_type:
        #                 if entity_instance["entity_id"] in ommitted_entities:
        #                     docs[doc_id]["entities_provided"][entity_type].pop(entity_instance["entity_id"])
        #                 else:
        #                     entities["entity_id"] = entity_instance["fields"]
                


        #populate realized fields using patient json
        # with open(Path("schemas/patient_template.json"), "r") as f:
        #     patient_template = json.load(f)
        # reconstructed_patients = {}
        # for doc_id, document in docs.items():
        #     patient_id = document["patient_id"]
        #     patient_filename = patient_id[4:]
        #     if patient_id not in reconstructed_patients:
        #         reconstructed_patients[patient_id] = patient_template.copy()
        #         reconstructed_patients[patient_id]["patient"]["id"] = patient_id
        #     patient_path = Path(rf"patients_debug/{patient_filename}/patient.json")
        #     with open(patient_path, "r") as f:
        #         patient = json.load(f)
        #     for entity_type, entity_instance_list in document["entities_provided"].items():
        #         for entity_instance in entity_instance_list:
        #             entity_id = entity_instance["entity_id"]
        #             matched_entity = next((dictionary for dictionary in patient[entity_type] if dictionary.get("id") == entity_id), None)
        #             if matched_entity != None:
        #                 reconstructed_patients[patient_id][entity_type].append(matched_entity.copy())
        # for patient in reconstructed_patients:
        #     with open(f"reconstructed_patients/{reconstructed_patients[patient]["patient"]["id"]}", "w") as f:
        #         json.dump(reconstructed_patients[patient], f, indent=2)

            

    

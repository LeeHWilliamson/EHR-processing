import json
import uuid
import os
doc_template = 'schemas/document_instance.json'
'''
template and degrading mode will be randomly selected from what is available
'''
debug_patient_path = "/home/leeha/Projects/EHR-processing/patients/0aaa2164-8de6-4152-8674-14d254aae13a/patient.json"
with open(debug_patient_path) as f:
    debug_patient = json.load(f)

def select_template(type = None):
    OBS_TABLE_V1 = {

        "template_id": "obs_v1",
        "entity_type": ["observations"],
        "fields": ["description", "encounter", "value", "units"],
        "group_by": "date"
    }
    return OBS_TABLE_V1

def select_degrade_mode():
    return "PLACEHOLDER_DEGRADE_MODE"

def select_obs(patient=None, template = "obs_v1"):
    obs = [] #store obs entities by id
    print(patient.keys())
    print("template is... ", template["entity_type"])
    for entity_type in template["entity_type"]:
        print(entity_type)
        for observation in patient[entity_type]: #iterate thru each observation entity
            obs.append(observation["id"]) #build list of entity ids to include
    return obs

def omit_entities(obs = [], mode = None):
    if mode is None:
        return obs
    else:
        pass

def build_and_log_docs(patient = None, entities = None, template = None, degrading_mode = None):
    dates = {} #create dict of dates so we can make doc for each one
    documents = []
    for obs_entity in patient["observations"]:
        if obs_entity["date"] not in dates: 
            dates[obs_entity["date"]] = [obs_entity]
        else:
            dates[obs_entity["date"]].append(obs_entity)
    print(dates.keys())
    for date, entities in dates.items(): #make doc for each encounter
        expected = []
        expected_ids = []
        realized = []
        realized_ids= []
        document = {
            "doc_id": f"doc_{uuid.uuid1()}",
            "doc_category": "obs_table",
            "template_id": template["template_id"],
            "patient_id": patient["patient"]["id"],
            "date": date,
            "entities_provided": {
                "observations": [
                    # {
                    #     "entity_id": obs.id,
                    #     "fields": ["description", "value", "units"]
                    # }
                    # for obs in realized_obs
                ]
            }
        }
        for entity in entities: #add entity corresponding to this encounter to doc
            # document["entities_provided"]["observations"].append(entity)
            expected.append(entity)
            expected_ids.append(entity["id"])
        realized = omit_entities(expected, degrading_mode)
        for entity in realized:
            document["entities_provided"]["observations"].append(entity)
            realized_ids.append(entity["id"])
        with open(f"documents/{document["doc_id"]}", "w") as file: #create doc
            json.dump(document, file, indent = 2)
        documents.append(document)
        for document in documents:
            log = {
            "log_id": f"log_{uuid.uuid1()}",
            "patient_id" : patient["patient"]["id"],
            "doc_id" : document["doc_id"],
            "template_id" : document["template_id"],
            "expected" : expected_ids,
            "realized" : realized_ids,
            "degrading_mode" : degrading_mode
            }
            with open(f"logs/{log["log_id"]}", "w") as file:
                json.dump(log, file, indent = 2)

    return documents
# def log_docs(documents = None, patient = None, expected_obs = None, realized_obs = None, degrading_mode = None):
#     for document in documents:
#         log = {
#             "log_id": f"log_{uuid.uuid1()}",
#             "patient_id" : patient["patient"]["id"],
#             "doc_id" : document["doc_id"],
#             "template_id" : document["template_id"],
#             "expected" : expected_obs,
#             "realized" : realized_obs,
#             "degrading_mode" : degrading_mode

#         }
#         with open(f"logs/{log["log_id"]}", "w") as file:
#             json.dump(log, file, indent = 2)

def generate_observation_table(patient): #patient will be a json style dict
    template = select_template("observations")
    degrade_mode = select_degrade_mode()
    expected_obs = select_obs(patient, template)
    realized_obs = omit_entities(obs = expected_obs, mode = degrade_mode)
    docs = build_and_log_docs(patient = patient, entities = realized_obs, template = template)
    # log_docs(docs, patient, expected_obs, realized_obs, degrade_mode)

generate_observation_table(debug_patient)
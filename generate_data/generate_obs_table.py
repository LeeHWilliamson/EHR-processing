import json
import uuid
import os
import random
doc_template = 'schemas/document_instance.json'
'''
template and omitting mode will be randomly selected from what is available
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

def select_omit_mode():
    mode_selection = random.randint(0, 1)
    if mode_selection == 0:
        return "NO OMISSION"
    elif mode_selection == 1:
        return "HEIGHT-WEIGHT"
    return "PLACEHOLDER_OMIT_MODE"

def select_obs(patient=None, template = "obs_v1"):
    obs = [] #store obs entities by id
    print(patient.keys())
    print("template is... ", template["entity_type"])
    for entity_type in template["entity_type"]:
        print(entity_type)
        for observation in patient[entity_type]: #iterate thru each observation entity
            obs.append(observation) #build list of entity ids to include
    return obs

def omit_entities(obs=None, mode=None):
    if obs is None:
        return []

    if mode != "HEIGHT-WEIGHT":
        return obs

    realized = []
    BODY_TERMS = {"Mass", "Weight", "Height"}
    for observation in obs:
        desc = observation["description"]
        if "Body" in desc and any(term in desc for term in BODY_TERMS):
            print("removing", desc)
            continue
        realized.append(observation)

    return realized


def group_obs(observations = None, grouping = "date"):
    entity_groups = {} #each key need be a grouping value (e.g. a date or encounterID), each value need be a list of entities
    for obs in observations: #observations == [] of obs entities
        if obs[grouping] not in entity_groups:
            entity_groups[obs[grouping]] = [obs]
        else:
            entity_groups[obs[grouping]].append(obs)
    print(entity_groups.keys())
    return entity_groups

def build_and_log_doc(patient = None, date = None, expected_obs = None, realized_obs = None, template = None, omitting_mode = None):
    document = {
        "doc_id": f"doc_{uuid.uuid4()}",
        "doc_category": "obs_table",
        "template_id": template["template_id"],
        "patient_id": patient["patient"]["id"],
        "date": date,
        "entities_provided": {
            "observations": [
                {
                    "entity_id": obs["id"],
                    "fields": template["fields"]
                }
                for obs in realized_obs
            ]
        }
    }

    log = {
        "log_id": f"log_{uuid.uuid4()}",
        "patient_id" : patient["patient"]["id"],
        "doc_id" : document["doc_id"],
        "template_id" : document["template_id"],
        "expected" : [obs["id"] for obs in expected_obs],
        "realized" : [obs["id"] for obs in realized_obs],
        "omitting_mode" : omitting_mode
    }

    return document, log
# def log_doc(document = None, patient = None, expected_obs = None, realized_obs = None, omitting_mode = None):
    # for document in documents:
    log = {
        "log_id": f"log_{uuid.uuid4()}",
        "patient_id" : patient["patient"]["id"],
        "doc_id" : document["doc_id"],
        "template_id" : document["template_id"],
        "expected" : expected_obs,
        "realized" : realized_obs,
        "omitting_mode" : omitting_mode
    }
    with open(f"logs/{log["log_id"]}", "w") as file:
        json.dump(log, file, indent = 2)
def write_doc(document):
    with open(f"documents/{document['doc_id']}", "w") as file:
        json.dump(document, file, indent=2) 

def write_log(log):
    with open(f"logs/{log['log_id']}", "w") as file:
        json.dump(log, file, indent = 2)

def generate_observation_table(patient): #patient will be a json style dict
    template = select_template("observations")
    # omit_mode = select_omit_mode()
    # print(omit_mode)
    expected_obs = select_obs(patient, template)
    grouped_obs = group_obs(expected_obs, grouping="date")
    documents = []
    for date, obs_for_date in grouped_obs.items():
        omit_mode = select_omit_mode()
        print(omit_mode)
        realized_obs = omit_entities(obs_for_date, omit_mode)
        document, log = build_and_log_doc(patient, date, obs_for_date, realized_obs, template, omit_mode)
        # print(document["doc_id"])
        write_doc(document)
        write_log(log)
        documents.append(document)

    return documents

generate_observation_table(debug_patient)
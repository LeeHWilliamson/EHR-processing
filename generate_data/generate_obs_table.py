import json
import uuid
import os
import random
import copy

'''
refactor
start by grouping patient obs by date/encounterID (create a dict of lists), each grouping should result in >= 1 docs
then convert each list to a grouping by obs category (e.g. body measurements vs blood tests) pass nested grouping to generate_doc
generate_doc will generate a doc object for each category for each date
    for each category_date_grouping:
        pass category to select_template to return random relevant template
        select omit mode for doc
        apply omission for doc
        build and log the doc
'''
class Entity_Grouping:
    def __init__(self):
        self.grouping = {} #each grouping will be a dict(grouping_category : [entities])
        
doc_template = 'schemas/document_instance.json'

'''
for obs, we want to build a singly-nested dict that groups by date or encounterID at the top level, and observation category at the second level
'''
def group_obs(patient = None, grouping = "date"): #default to date for top level grouping
    entity_grouping = Entity_Grouping()
    for obs_entity in patient["observations"]:
        if obs_entity[grouping] not in entity_grouping.grouping: #if we don't have a grouping for this date, make one
            entity_grouping.grouping[obs_entity[grouping]] = Entity_Grouping()
        top_level_group = entity_grouping.grouping[obs_entity[grouping]]
        if obs_entity["category"] not in top_level_group.grouping:
            top_level_group.grouping[obs_entity["category"]] = []
        top_level_group.grouping[obs_entity["category"]].append(obs_entity)  #sort entity into its proper date and obs category
    
    # entity_groups = {} #each key need be a grouping value (e.g. a date or encounterID), each value need be a list of entities
    # for obs in observations: #observations == [] of obs entities
    #     if obs[grouping] not in entity_groups:
    #         entity_groups[obs[grouping]] = [obs]
    #     else:
    #         entity_groups[obs[grouping]].append(obs)
    # print(entity_groups.keys())
    print(entity_grouping.grouping.keys())
    for date, category in entity_grouping.grouping.items():
        for cat_label in category.grouping.keys():
            print(cat_label)
    return grouping, entity_grouping
'''
template and omitting mode will be randomly selected from what is available
'''
debug_patient_path = "/home/leeha/Projects/EHR-processing/patients/0aaa2164-8de6-4152-8674-14d254aae13a/patient.json"
with open(debug_patient_path) as f:
    debug_patient = json.load(f)

'''
Each doc type will have multiple templates, templates will differ in layout, fields rendered, and what entities are included
(e.g. a lab template allows blood work obs but not height and weight)
'''

def select_template(group_cat = "date", obs_cat = "other", entity_list = []):
    if obs_cat == "body_measurement":
        if group_cat == "date":
            template = {

                "template_id": "obs_date_body_measurements_v1",
                "entity_type": ["observations"],
                "fields": set(["description", "encounter", "value", "units"]),
                "grouped_by": group_cat,
                "category" : obs_cat
            }
        elif group_cat == "encounter":
            template = {

                "template_id": "obs_encounter_body_measurements_v1",
                "entity_type": ["observations"],
                "fields": set(["description", "date", "value", "units"]),
                "grouped_by": group_cat,
                "category" : obs_cat
            }            

    else:
        if group_cat == "date":
            template = {

                "template_id": "obs__date_table_other_v1",
                "entity_type": ["observations"],
                "fields": set(["description", "encounter", "value", "units"]),
                "grouped_by": group_cat,
                "category" : obs_cat
            }
        elif group_cat == "encounter":
            template = {

                "template_id": "obs_encounter_table_other_v1",
                "entity_type": ["observations"],
                "fields": set(["description", "date", "value", "units"]),
                "grouped_by": group_cat,
                "category" : obs_cat
            }

    
    return template

'''
Select patients entities and fields based on doc template
'''
def select_obs(patient=None, template = "obs_v1"):
    obs = [] #store obs entities by id
    print(patient.keys())
    print("template is... ", template["entity_type"])
    for entity_type in template["entity_type"]:
        print(entity_type)
        for observation in patient[entity_type]: #iterate thru each observation entity
            obs.append(observation) #build list of entity ids to include
    return obs

'''
Omit modes simulate recorder error by selecting entity fields to not be realized on final document render
'''
def select_omit_mode():
    mode_selection = random.randint(0, 1)
    if mode_selection == 0:
        return "NO_OMISSION"
    elif mode_selection == 1:
        return "FORGOT_UNITS"
    return "PLACEHOLDER_OMIT_MODE"


def omit_entities(entity_list=None, mode=None, template = None):
    if entity_list is None:
        return []
    realized = []
    omitted = []
    #first we need to omit fields that simply don't aren't placed on this template
    for entity in entity_list:
        entity_copy = copy.deepcopy(entity)
        for field, value in entity.items():
            to_omit = [] #list of fields to omit
            if field not in template["fields"]:
                # omitted = entity.pop(field, None)
                to_omit.append((field, value))
                # omitted_tuple = (field, entity["field"])
                # removed.append(omitted_tuple)
        # for tup in to_omit: #OMITS FIELDS THAT ARE NOT COMPATIBLE WITH TEMPLATE, MOVE TO TEMPLATE SELECTION AND ADD AS FIELD IN LOG
        #     entity_copy[tup[0]] = "OMITTED"
        omitted = omitted + to_omit
    if mode == "NO_OMISSION":
        return entity_list, []
    
    if mode == "FORGOT_UNITS":
        for entity in entity_list:
            entity_copy = copy.deepcopy(entity)
            omitted_field = entity_copy.pop("units", None)
            omitted_tuple = ("units", omitted_field)
            realized.append(entity_copy)
            omitted.append(omitted_tuple)

    return realized, omitted


def build_and_log_doc(patient = None, group_cat = None, top_level_key = None, second_level_grouping = None):
    #pass a top_level_key (usually either a date or encounterID) and a grouping of observations (dict{obs_category : entity_list})
    #for each grouping of obs_entities, we generate a doc
    for obs_cat, entity_list in second_level_grouping.grouping.items(): #the obs_cat (observation category) will be a str field in the observation entity. It will determine the possible obs_doc templates
        #select template for doc
        documents = []
        logs = []
        template = select_template(group_cat, obs_cat, entity_list)
        template_fields = template["fields"]
        template["fields"] = list(template["fields"]) #convert set back to list to make json serializable
        #select omit_mode for doc
        omit_mode = select_omit_mode()
        realized_obs, omitted = omit_entities(entity_list, omit_mode, template) #we return obs_that were rendered and fields+obs that were omitted 
        omitted_fields = []
        for tup in omitted:
            if tup[0] in template_fields: #tup[0] will be a field name, if it's a field that would have otherwise been rendered on template, this info must be included in log
                omitted_fields.append(tup[1])

        #create doc
        document = {
        "doc_id": f"doc_{uuid.uuid4()}",
        "doc_category": "obs_table",
        "template_id": template["template_id"],
        "patient_id": patient["patient"]["id"],
        "grouping": top_level_key,
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
        
        documents.append(document)
        write_doc(document)
        
        #create log
        #return doc, log
    

    log = {
        "log_id": f"log_{uuid.uuid4()}",
        "patient_id" : patient["patient"]["id"],
        "doc_id" : document["doc_id"],
        "template_id" : document["template_id"],
        "expected" : [obs["id"] for obs in entity_list],
        "realized" : [obs["id"] for obs in realized_obs],
        "omitted_fields" : omitted_fields,
        "omitting_mode" : omit_mode
    }
    logs.append(log)
    write_log(log)

    return documents, logs
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
    group_cat, grouped_obs = group_obs(patient, grouping="date")
    # template = select_template("observations")
    # omit_mode = select_omit_mode()
    # print(omit_mode)
    # expected_obs = select_obs(patient, template)

    documents = []
    for top_level_key, second_level_grouping in grouped_obs.grouping.items(): #top_level_key will be a string, often the date or an encounterID, second_level_grouping will be the grouping associated with that key
        # omit_mode = select_omit_mode()
        # realized_obs = omit_entities(second_level_grouping, omit_mode)
        docs_for_this_grouping, logs_for_this_grouping = build_and_log_doc(patient, group_cat, top_level_key, second_level_grouping)
        # print(document["doc_id"])
        
        documents.append(docs_for_this_grouping)

    return documents

generate_observation_table(debug_patient)
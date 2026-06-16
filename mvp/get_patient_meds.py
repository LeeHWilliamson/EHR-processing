'''
This script will get the GT for a patient for the medication task
input: a patient path
output: a list of strs corresponding to descriptions of patient's current meds
'''
import json
from pathlib import Path

def get_meds(patient_json = None):
    if patient_json == None:
        return "Please pass a valid patient object"
    # with open(Path(patient_path), "r") as file:
    #     whole_patient = json.load(file)
    #extract current medications
    current_med_decsriptions = []
    for medication in patient_json["medications"]:
        #if we don't have an endDate, we consider this a current medication
        if type(medication["endDate"]) != str:
            current_med_decsriptions.append(medication["description"])
    return current_med_decsriptions
'''
This script will reconstruct patient observation entities via regex of obs_tables
>create reconstructed_patients dict
>open ocr output as string
>load patient template
>load observation entities template
>read ocr line by line
    if we encounter "patient_id" 
        update "id" in patient template
    if we encounter a key in obs template, enter entity population loop
        >create obs dict
        >while {"description", encounter, value, date, units, category} in line.text
            >append all text in line that is not a key as key : text to dict
            >go to next line
        append obs dict to obs entities template
update observations entity of patient template
>update reconstructed patients dict
'''
import json
import re
from pathlib import Path
import copy

OBSERVATION_FIELDS = {"description", "encounter", "value", "units", "date", "category"}

def populate_obs_entity(ocr_text_lines, start):
    print("hello")
    obs_dict = {}
    curr_index = start
    split_line = ocr_text_lines[curr_index].split(" ")
    while not OBSERVATION_FIELDS.isdisjoint(set(split_line)):
        field = split_line[0]
        value = split_line[1]
        if field in obs_dict:
            return obs_dict
        obs_dict[field] = value
        curr_index += 1
        if curr_index < len(ocr_text_lines):

            split_line = ocr_text_lines[curr_index].split(" ")
    print(set(split_line))
    return obs_dict

def obs_table_regex(ocr_output_path = r"ocr/doc_68d4831c-7458-4968-be29-ea64b0aedf8f.txt"):
    
    observations = []
    lines = []
    #load patient template for reconstruction
    with open("schemas/patient_template.json", "r") as f:
        reconstructed_patient = json.load(f)
    with open (ocr_output_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            else:
                lines.append(line)
        # ocr_text = f.read()
    # print(ocr_text)
    # lines = ocr_text.splitlines()
    for index in range(len(lines)):
        split_line = lines[index].split(" ")
        if "patient_id" in split_line:
            id = split_line[1]
            reconstructed_patient["patient"]["id"] = id
        split_line_set = set(split_line)
        if not OBSERVATION_FIELDS.isdisjoint(split_line_set):
            # print(split_line_set)
            observations.append(populate_obs_entity(lines, index))
    for obs_entity in observations:
        if obs_entity not in reconstructed_patient["observations"]:
            reconstructed_patient["observations"].append(obs_entity)
    print(reconstructed_patient)
obs_table_regex()
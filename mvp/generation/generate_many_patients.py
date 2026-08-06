'''
This script exists to generate many patients, so we can then
extract all the possible values for certain fields, namely allergies, medications, conditions
'''
from pathlib import Path
from ..databases.db_ops import load_patients_sqlite3 as load_patients
from ..orchestration.main import generate_patients
from .load_patient_gt import run_end_to_end
import sqlite3
import csv
import re
import json
import subprocess
import time

#call synthea to create patient data
generate_patients()
#call function to assemble jsons
patient_paths = run_end_to_end(input_directory=r'synthea/output/csv', output_directory=r'synthea/output/json')
#load patients, lets just use normalized schema
load_patients.main(["normalized_v1"])
with sqlite3.connect(Path("/home/leeha/tools/sqlite/normalized_v1.db")) as conn:
    # conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    #select all unique allergies and write to csv
    allergy_query = cursor.execute("SELECT DISTINCT description FROM allergies")
    allergies = allergy_query.fetchall()
    allergies_list = []
    with open("/home/leeha/Projects/EHR-processing/mvp/tests/test_data/possible_allergies.csv", "w") as allergies_file:
        writer = csv.writer(allergies_file)
        for allergy in allergies:
            allergies_list.append(allergy[0].lower())
        for allergy in sorted(allergies_list):
            print(allergy)
            writer.writerow([allergy])

    #select all unique conditions and write to csv
    conditions_query = cursor.execute("SELECT DISTINCT condition FROM conditions")
    conditions = conditions_query.fetchall()
    conditions_list = []
    with open("/home/leeha/Projects/EHR-processing/mvp/tests/test_data/possible_conditions.csv", "w") as conditions_file:
        writer = csv.writer(conditions_file)
        for condition in conditions:
            conditions_list.append(condition[0].lower())
        for condition in sorted(conditions_list):
            print(condition)
            writer.writerow([condition])

    #medications...
    medications_query = cursor.execute("SELECT DISTINCT description FROM medications")
    medications = medications_query.fetchall()
    medications_list = []
    with open ("/home/leeha/Projects/EHR-processing/mvp/tests/test_data/possible_medications.csv", "w") as medications_file:
        writer = csv.writer(medications_file)
        for medication in medications:
            medications_list.append(medication[0].lower())
        for medication in sorted(medications_list):
            print(medication)
            writer.writerow([medication])


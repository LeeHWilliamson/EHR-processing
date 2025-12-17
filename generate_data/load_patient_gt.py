'''
this script loads patient data from synthea csvs and converts each patient to a standard json object
first we load the patients csv file as a pandas dataframe and use it to initialize a json object for each patient
then we load other csvs in sequence and use them to populate the json object of each patient
'''
import os
import json
import pandas
import csv
#we will use some constant paths for our schemas and datafiles for now
canonical_patient_json = 'schemas/canonical_patient.json'
patients_output_path = 'sample_data/patients.json'
patients_csv = 'sample_data/patients.csv'
allergies_csv = 'sample_data/allergies.csv'
conditions_csv = 'sample_data/conditions.csv'
encounters_csv = 'sample_data/encounters.csv'
immunizations_csv = 'sample_data/immunizations.csv'
medications_csv = 'sample_data/medications.csv'
procedures_csv = 'sample_data/procedures.csv'



'''
create dict of all patient ids
load json schema for each
iterate through rows of csvs, if id in dict, update that entries json object
'''

patients_df = pandas.read_csv(patients_csv)
patients = {}
for row in patients_df.itertuples(index=True):
    with open(canonical_patient_json) as file:
        patients[row.Id] = json.load(file)
print(len(patients))

#load patient info
for row in patients_df.itertuples(index=True):
    patients[row.Id]["patient"]["id"] = row.Id
    patients[row.Id]["patient"]["firstName"] = row.FIRST
    patients[row.Id]["patient"]["lastName"] = row.LAST
    patients[row.Id]["patient"]["dob"] = row.BIRTHDATE
    patients[row.Id]["patient"]["gender"] = row.GENDER

#load allergies
allergies_df = pandas.read_csv(allergies_csv)

for row in allergies_df.itertuples(index=True):
    patients[row.PATIENT]["allergies"].append(row.DESCRIPTION)

#load encounters
encounters_df = pandas.read_csv(encounters_csv)
for row in encounters_df.itertuples(index=True):
    patients[row.PATIENT]["encounters"].append({"type" : row.ENCOUNTERCLASS, "description" : row.DESCRIPTION, "reason" : row.REASONDESCRIPTION, "startDate" : row.START, "endDate" : row.STOP})

#load conditions
conditions_df = pandas.read_csv(conditions_csv)
for row in conditions_df.itertuples(index=True):
    patients[row.PATIENT]["conditions"].append({"condition" : row.DESCRIPTION, "startDate" : row.START, "endDate" : row.STOP})

#load immunizations
immunizations_df = pandas.read_csv(immunizations_csv)
for row in immunizations_df.itertuples(index=True):
    patients[row.PATIENT]["immunizations"].append({"name" : row.DESCRIPTION, "date" : row.DATE})

#load medications
medications_df = pandas.read_csv(medications_csv)
for row in medications_df.itertuples(index=True):
    patients[row.PATIENT]["medications"].append({"description" : row.DESCRIPTION, "reason" : row.REASONDESCRIPTION, "startDate" : row.START, "endDate" : row.STOP})

#load procedures
procedures_df = pandas.read_csv(procedures_csv)
for row in procedures_df.itertuples(index=True):
    dateTime = row.DATE.split('T')
    patients[row.PATIENT]["procedures"].append({"description" : row.DESCRIPTION, "reason" : row.REASONDESCRIPTION, "date" : dateTime[0], "time" : dateTime[1]})

with open(patients_output_path, 'w') as file:
    for key, value in patients.items():
        json.dump(value, file)
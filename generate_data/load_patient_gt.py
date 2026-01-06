'''
this script loads patient data from synthea csvs and converts each patient to a standard json object
first we load the patients csv file as a pandas dataframe and use it to initialize a json object for each patient
then we load other csvs in sequence and use them to populate the json object of each patient
'''
import os
import json
import pandas
import uuid
import csv
#we will use some constant paths for our schemas and datafiles for now, we import all clinical data
patient_template = 'schemas/patient_template.json'
patients_output_path = 'sample_data/patients.json'
patients_csv = 'sample_data/patients.csv'
allergies_csv = 'sample_data/allergies.csv'
conditions_csv = 'sample_data/conditions.csv'
encounters_csv = 'sample_data/encounters.csv'
immunizations_csv = 'sample_data/immunizations.csv'
medications_csv = 'sample_data/medications.csv'
procedures_csv = 'sample_data/procedures.csv'
observations_csv = "sample_data/observations.csv"
careplans_csv = "sample_data/careplans.csv"
devices_csv = "sample_data/devices.csv"
imaging_studies_csv = "sample_data/imaging_studies.csv"


'''
create dict of all patient ids
load json schema for each
iterate through rows of csvs, if id in dict, update that entries json object
'''

def csv_to_record(csv_path=None):
    if csv_path is None:
        return
    dataframe = pandas.read_csv(csv_path)
    return dataframe.dropna(how="all").to_dict(orient="records")

def load_patients(directory = None, clinical_datasets = None): #each clinical_dataset should simply be a filename, e.g. "careplans"
    if clinical_datasets is None:
        return "no dataset names were passed, please try again"
    dataframe_dicts = {}
    for dataset in clinical_datasets: #create paths to all datasets
        dataset_filepath = directory+ "/" + dataset + ".csv"
        dataframe_dicts[dataset] = csv_to_record(dataset_filepath)
    return dataframe_dicts

#trackers for incrementing instance ids
med_count = 1
proc_count = 1
obs_count = 1
cond_count = 1
immu_count = 1

with open(f"schemas/canonical_patient.json") as file:
    patient_schema = json.load(file) #create dict for each patient, key is patient id, val is all other data


patients_df = pandas.read_csv(patients_csv)
patients = {}
for row in patients_df.itertuples(index=True):
    with open(patient_template) as file:
        patients[row.Id] = json.load(file)
print(len(patients))

# load patient info, each patient will only have 1 entry in patients table, so we simply load each row as an individual record
for row in patients_df.itertuples(index=True):
    patients[row.Id]["patient"]["id"] = "pat_" + row.Id
    patients[row.Id]["patient"]["firstName"] = row.FIRST
    patients[row.Id]["patient"]["lastName"] = row.LAST
    patients[row.Id]["patient"]["dob"] = row.BIRTHDATE
    patients[row.Id]["patient"]["gender"] = row.GENDER
# for record in records(dataframe=patients_df):
#     patient_record = {key: value for key, value in record.items() if pandas.notna(value)}

#load allergies
allergies_df = pandas.read_csv(allergies_csv)
for row in allergies_df.itertuples(index=True):
    allergyID = f"all_{uuid.uuid1()}"
    # patients[row.PATIENT]["patient"]["entities"].append(allergyID)
    patients[row.PATIENT]["allergies"].append({"id": allergyID, "start": row.START, "stop" : row.STOP, "encounter" : row.ENCOUNTER, "description" : row.DESCRIPTION})

#load careplans
careplans_df = pandas.read_csv(careplans_csv)
for row in careplans_df.itertuples(index=True):
    careplanID = "care_" + row.Id
    # patients[row.PATIENT]["patient"]["entities"].append(careplanID)
    patients[row.PATIENT]["careplans"].append({"id" : careplanID, "startDate" : row.START, "endDate" : row.STOP, "encounter" : row.ENCOUNTER, "description" : row.DESCRIPTION, "reasonDescription" : row.REASONDESCRIPTION})

#load devices
devices_df = pandas.read_csv(devices_csv)
for row in devices_df.itertuples(index=True):
    devicesID = f"dev_{uuid.uuid1()}"
    # patients[row.PATIENT]["patient"]["entities"].append(devicesID)
    patients[row.PATIENT]["devices"].append({"id": devicesID, "startDate" : row.START, "encounter" : row.ENCOUNTER, "description" : row.DESCRIPTION})

#load encounters
encounters_df = pandas.read_csv(encounters_csv)
for row in encounters_df.itertuples(index=True):
    startDateTime = row.START.split("T")
    startTime = startDateTime[1][:-1] #omit the z in the time
    endDateTime = row.STOP.split("T")
    endTime = endDateTime[1][:-1]
    encountersID = "enc_" + row.Id
    # patients[row.PATIENT]["patient"]["entities"].append(encountersID)
    patients[row.PATIENT]["encounters"].append({"id" : encountersID, "type" : row.ENCOUNTERCLASS, "description" : row.DESCRIPTION, "reason" : row.REASONDESCRIPTION, "startDate" : startDateTime[0], "endDate" : endDateTime[0], "startTime" : startTime, "endTime" : endTime})

#load imaging studies
imaging_studies_df = pandas.read_csv(imaging_studies_csv)

for row in imaging_studies_df.itertuples(index=True):
    dateTime = row.DATE.split("T")
    imagingID = "img_" + row.Id
    # patients[row.PATIENT]["patient"]["entities"].append(imagingID)
    patients[row.PATIENT]["imaging_studies"].append({"id" : imagingID, "date" : dateTime[0], "encounter" : row.ENCOUNTER, "bodysite" : row.BODYSITE_DESCRIPTION, "modality" : row.MODALITY_DESCRIPTION})

#load conditions
conditions_df = pandas.read_csv(conditions_csv)
conditions_df = conditions_df.dropna(how="all")

for row in conditions_df.itertuples(index=True):
    startDateTime = row.START.split("T")
    print(row.STOP)
    if pandas.notna(row.STOP):
        endDateTime = row.STOP.split("T")
    else:
        endDateTime = [None]
    conditionsID = f"cond_{uuid.uuid1()}"
    # patients[row.PATIENT]["patient"]["entities"].append(conditionsID)
    patients[row.PATIENT]["conditions"].append({"condition" : row.DESCRIPTION, "id": conditionsID, "encounter" : row.ENCOUNTER, "startDate" : startDateTime[0], "endDate" : endDateTime[0]})
    cond_count += 1

#load immunizations
immunizations_df = pandas.read_csv(immunizations_csv)
for row in immunizations_df.itertuples(index=True):
    dateTime = row.DATE.split("T")
    immunizationsID = f"immu_{uuid.uuid1()}"
    # patients[row.PATIENT]["patient"]["entities"].append(immunizationsID)
    patients[row.PATIENT]["immunizations"].append({"name" : row.DESCRIPTION, "id" : immunizationsID, "date" : dateTime[0], "encounter" : row.ENCOUNTER})
    immu_count += 1

#load medications
medications_df = pandas.read_csv(medications_csv)
medications_df = medications_df.dropna(how="all")

for row in medications_df.itertuples(index=True):
    startDateTime = row.START.split("T")
    if pandas.notna(row.STOP):
        endDateTime = row.STOP.split("T")
    else:
        endDateTime = [None]
    medicationsID = f"med_{uuid.uuid1()}"
    # patients[row.PATIENT]["patient"]["entities"].append(medicationsID)
    patients[row.PATIENT]["medications"].append({"description" : row.DESCRIPTION, "id" : medicationsID, "encounter" : row.ENCOUNTER, "reason" : row.REASONDESCRIPTION, "startDate" : startDateTime[0], "endDate" : endDateTime[0]})
    med_count += 1
#load procedures
procedures_df = pandas.read_csv(procedures_csv)
for row in procedures_df.itertuples(index=True):
    dateTime = row.DATE.split('T')
    proceduresID = f"proc_{uuid.uuid1()}"
    # patients[row.PATIENT]["patient"]["entities"].append(proceduresID)
    patients[row.PATIENT]["procedures"].append({"description" : row.DESCRIPTION, "id" : proceduresID, "encounter" : row.ENCOUNTER, "reason" : row.REASONDESCRIPTION, "date" : dateTime[0], "time" : dateTime[1]})
    proc_count += 1

#load observations
observations_df = pandas.read_csv(observations_csv)
BODY_TERMS = {"Mass", "Weight", "Height"}
for row in observations_df.itertuples(index=True):
    dateTime = row.DATE.split("T")
    observationsID = f"obs_{uuid.uuid1()}"
    # patients[row.PATIENT]["patient"]["entities"].append(observationsID)
    if "Body" in row.DESCRIPTION and any(term in row.DESCRIPTION for term in BODY_TERMS): #entity type + entity category will be used to select document template
        category = "body_measurement"
    else:
        category = "other"
    patients[row.PATIENT]["observations"].append({"description" : row.DESCRIPTION, "id" : observationsID, "encounter" : row.ENCOUNTER, "value" : row.VALUE, "units" : row.UNITS, "date" : dateTime[0], "category" : category})
    obs_count += 1

for key, value in patients.items():
    # os.mkdir(f"patients/{key}")
    os.makedirs(f"patients/{key}", exist_ok=True)
    with open(f"patients/{key}/patient.json", 'w') as file:
        json.dump(value, file, indent=2)
        
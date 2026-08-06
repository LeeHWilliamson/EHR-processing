import json
from pathlib import Path
import csv
from datetime import datetime

def calculate_age(birthdate_str, date_format="%Y-%m-%d"):
    """
    convert age str in patient json to datetime and calculate difference from today's date
    """
    try:
        # Parse the birthdate string into a datetime object
        birthdate = datetime.strptime(birthdate_str, date_format).date()
    except ValueError:
        raise ValueError(f"Invalid date format. Expected format: {date_format}")

    today = datetime.today().date()

    if birthdate > today:
        raise ValueError("Birthdate cannot be in the future. Check patient generation settings and try again.")

    # Calculate age
    age = today.year - birthdate.year
    # Adjust if birthday hasn't occurred yet this year
    if (today.month, today.day) < (birthdate.month, birthdate.day):
        age -= 1

    if age < 15:
        return "too young"
    elif age > 80:
        return "too old"
    else:
        return None
    # return age

def get_anesthesia_prep(patient_json = None):
    '''
    a patient is disqualified from this surgery if they are not 15 < years old < 80, if they are allergic to latex, if they are diabetic, or if they take warfarin
    '''
    disqualifiers_master = set()
    patient_disqualifiers = set()
    with open("/home/leeha/Projects/EHR-processing/mvp/tests/test_data/surgery_disqualifiers.csv", newline='', mode="r") as file:
        reader = csv.reader(file)
        for row in reader:
            disqualifiers_master.add(row[0])

    age = calculate_age(patient_json["patient"]['birthdate'])
    if age:
        patient_disqualifiers.add(age)

    #diabetes doesn't really end so just check if they were ever diagnosed
    for condition in patient_json["conditions"]:
        if condition["condition"] in disqualifiers_master:
            patient_disqualifiers.add(condition["condition"])
    #check if they are taking a disqualifier medication at this time
    for medication in patient_json["medications"]:
        if medication["description"] in disqualifiers_master and medication["endDate"]:
            patient_disqualifiers.add(medication["description"])
    #check if they have allergy to latex
    for allergy in patient_json["allergies"]:
        if allergy["description"] in disqualifiers_master:
            patient_disqualifiers.add(allergy["description"])
    return list(patient_disqualifiers)

if __name__ == "__main__":
    with open("/home/leeha/Projects/EHR-processing/mvp/tests/test_data/test_patients/surgery_disqualified.json", "r") as file:
        test_json = json.load(file)
    print(get_anesthesia_prep(test_json))
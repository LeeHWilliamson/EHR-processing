# from generate_data.load_patient_gt import run_end_to_end
import sys
from pathlib import Path
from generate_data.load_patient_gt import run_end_to_end
from .agent import run_workflow
from .get_patient_meds import get_meds
from .calculate_accuracy import calc_accuracy
from . import load_patients_sqlite3 as load_patients
import json
import subprocess
from pathlib import Path
import time
import requests
from datetime import datetime, timezone

SYNTHEA_DIR = Path("/home/leeha/Projects/EHR-processing/synthea")
def generate_patients():
    cmd = [
        "java",
        "-jar",
        "synthea-with-dependencies.jar",
        "-c",
        "/home/leeha/Projects/EHR-processing/synthea/settings.properties",
        "Texas",
        "Houston"
    ]
    subprocess.run(
        cmd,
        cwd=SYNTHEA_DIR,
        check=True,
    )
def launch_api():
    api_process = subprocess.Popen(
        ["uvicorn", "mvp.api_endpoints:app", "--reload"],
    )
    time.sleep(5)
    requests.get("http://127.0.0.1:8000/docs")
    return api_process

if __name__ == '__main__': 
    print("starting")
    #generate patients
    print("calling synthea")
    generate_patients()
    #assemble patient ground truth
    print("creating patient JSONs")
    patient_paths = run_end_to_end(input_directory=r'synthea/output/csv', output_directory=r'synthea/output/json')
    #launch app
    print("launching DB")
    api_process = launch_api()
    try:
        #populate SQLite DB
        print("populating DB")
        load_patients.main()
        # all_analytics = {}
        #For each patient...
        for patient_folder in Path('synthea/output/json').iterdir():
            patient_folder_str = str(patient_folder)
            with open(f"{patient_folder_str}/patient.json", "r") as file:
                patient = json.load(file)
            #run agent, return analytics_dict and response_text
            analytics_dict, response_text = run_workflow(patient["patient"]["id"])
            #get patient GT
            current_meds_gt = get_meds(patient)
            #compare GT to response_text to calc accuracy and get list of mistakes, update analytics_dict
            accuracy, hallucinated_meds, missed_meds = calc_accuracy(current_meds_gt, response_text)
            analytics_dict["accuracy"] = accuracy
            analytics_dict["missed_meds"] = missed_meds
            analytics_dict["hallucinated_meds"] = hallucinated_meds
            # all_analytics[patient["patient"]["id"]] = analytics_dict
            #output analytics as json
            curr_datetime = str(datetime.now(timezone.utc).isoformat())
            curr_date = curr_datetime[:10]
            with open(fr"mvp/agent_reports/{curr_date}.json", "w") as file:
                json.dump(analytics_dict, file, indent=2)
    finally:
        api_process.terminate()
        api_process.wait()
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

SYNTHEA_DIR = Path("/home/leeha/Projects/EHR-processing/synthea")
def generate_patients():
    cmd = [
        "run_synthea",
        "-c",
        "settings.properties",
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
        ["uvicorn", "api_endpoints:app", "--reload"],
    )
    time.sleep(5)
    requests.get("http://127.0.0.1:8000/docs")
    return api_process

if __name__ == '__main__': 
    print("starting")
    #generate patients
    generate_patients()
    #assemble patient ground truth
    patient_paths = run_end_to_end(input_directory=r'synthea/output/csv', output_directory=r'synthea/output/json')
    #launch app
    api_process = launch_api()
    #populate SQLite DB
    load_patients.main()
    all_analytics = {}
    #For each patient...
    for patient_folder in Path('synthea/output/json').iterdir():
        patient = json.load(patient_folder/"patient.json")
        #run agent, return analytics_dict and response_text
        analytics_dict, response_text = run_workflow("pat_" + patient["patient"]["id"])
        #get patient GT
        current_meds_gt = get_meds(patient)
        #compare GT to response_text to calc accuracy and get list of mistakes, update analytics_dict
        accuracy, hallucinated_meds, missed_meds = calc_accuracy(current_meds_gt, response_text)
        analytics_dict["accuracy"] = accuracy
        analytics_dict["missed_meds"] = missed_meds
        analytics_dict["hallucinated_meds"] = hallucinated_meds
        all_analytics.add(analytics_dict)
    #output analytics as json
    json.dump(all_analytics, "agent_reports", indent=2)
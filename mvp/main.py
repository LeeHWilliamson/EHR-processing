# from generate_data.load_patient_gt import run_end_to_end
import sys
from pathlib import Path
from generate_data.load_patient_gt import run_end_to_end
from .agent import run_workflow
from .get_patient_meds import get_meds
from .calc_output_metrics import calc_metrics
from .calc_workflow_metrics import analyze_workflow
from . import load_patients_sqlite3 as load_patients
import json
import subprocess
from pathlib import Path
import time
import requests
from datetime import datetime, timezone

SYNTHEA_DIR = Path("/home/leeha/Projects/EHR-processing/synthea")
SCHEMA_NAMES = ["normalized_v1", "flat_v1"]
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
    # generate patients
    # print("calling synthea")
    # generate_patients()
    # # assemble patient ground truth
    # print("creating patient JSONs")
    # patient_paths = run_end_to_end(input_directory=r'synthea/output/csv', output_directory=r'synthea/output/json')
    #launch app
    print("launching DB")
    api_process = launch_api()
    try:
        #build and populate SQLite DB for each schema
        print("populating DB")
        load_patients.main(schemas = SCHEMA_NAMES)
        #run workflow for each schema
        for schema in SCHEMA_NAMES:
            #For each patient...
            for patient_folder in Path('synthea/output/json').iterdir():
                patient_folder_str = str(patient_folder)
                with open(f"{patient_folder_str}/patient.json", "r") as file:
                    patient = json.load(file)
                #run agent, return analytics_dict and response_text
                analytics_dict = run_workflow(patient["patient"]["id"], task = "medication_retrieval_v1", schema = schema)
                #analyze workflow compared to ideal workflow
                workflow_metrics = analyze_workflow(analytics_dict)
                analytics_dict["workflow_metrics"] = workflow_metrics
                #get patient GT
                current_meds_gt = get_meds(patient)
                analytics_dict["patient_gt"] = current_meds_gt
                #compare GT to response_text to calc output accuracy and get list of mistakes, update analytics_dict
                output_metrics = calc_metrics(current_meds_gt, analytics_dict["raw_response"])
                analytics_dict["output_metrics"] = output_metrics
                # all_analytics[patient["patient"]["id"]] = analytics_dict
                #output analytics as json
                curr_datetime = str(datetime.now(timezone.utc).isoformat())
                curr_date = curr_datetime[:10]
                #append results to agent file
                report_dir = Path(f"mvp/agent_reports/{analytics_dict["task"]}")
                report_dir.mkdir(parents=True, exist_ok=True)
                report_path = report_dir / f"{analytics_dict["agent"]}.jsonl"
                with report_path.open("a", encoding="utf-8") as file:
                    file.write(json.dumps(analytics_dict, indent=2) + "\n")
    finally:
        api_process.terminate()
        api_process.wait()
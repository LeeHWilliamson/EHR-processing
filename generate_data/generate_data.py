'''
Generate Synthea data according to user specifications
Convert Synthea data to patient-oriented JSON objects
Distribute patient data across document JSONS
'''
import json
import argparse
import generate_patient_data
from load_patient_gt import run_end_to_end
from generate_obs_table import generate_observation_table


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "data_generation parameters")
    parser.add_argument("--data_directory_path", help="path to deposit raw synthetic data")
    parser.add_argument("--patient_json_path", help="path to deposit patient JSONs")
    parser.add_argument("--document_json_path", help="path to deposit doc jsons")
    parser.add_argument("--mapping_json_path", help="path to deposit mappings")
    # parser.add_argument("document_files_path", help="path to deposit rendered files")
    args = parser.parse_args()

    patient_paths = run_end_to_end("sample_data", args.patient_json_path) #create patient JSONs
    counter = 0
    for patient in patient_paths:
        if counter < 10:
            generate_observation_table(patient, args.document_json_path, args.mapping_json_path, args.document_json_path)
            counter +=1

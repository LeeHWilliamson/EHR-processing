'''
This script will pass arguments to Synthea to generate a set of patients with user-selected params
'''
import subprocess
from pathlib import Path
import argparse
import json
from mvp.generation.load_patient_gt import (
    run_end_to_end as create_simplified_patient_jsons,
)
from webapp.generate_patients.generate_keep_patient import generate_keep_module

WEBAPP_DIR = Path(__file__).resolve().parent.parent
CURR_RUN_DIR = WEBAPP_DIR / "patients" / "current_run" / "full_patients"

'''
This function will call synthea with all args specified by the user
'''
def run_synthea(synthea_path: Path, count: int, state: str, city: str | None = None, min_age: int | None = None, max_age: int | None = None, keep_attribute: Path | None = None):

    if min_age is None or min_age < 1:
        min_age = 1
    if max_age is None or max_age > 100 or max_age < min_age:
        max_age = 100
    #if we have not yet made a keep module for this attribute, make one real quick
    if keep_attribute is not None:
        keep_module_path = (WEBAPP_DIR / "debug_keep_modules" / f"keep_{keep_attribute}.json")
        if not keep_module_path.exists():
            keep_module_path = generate_keep_module(keep_attribute)


    cmd = [
        "./run_synthea",
        "-p", str(count),
        "-a", f"{min_age}-{max_age}",
        state,
        "--exporter.baseDirectory", f"{CURR_RUN_DIR}"
    ]
    if city is not None:
        cmd.append(city)
    if keep_attribute is not None:
        cmd.append('-k')
        cmd.append(keep_module_path)
        
    subprocess.run(cmd, cwd = synthea_path, check = True)
    

'''
this function will process CLI args into a dict to pass to synthea runner
'''
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthea-path", type=Path, default = Path("/home/leeha/Projects/synthea"), help = "path to your synthea runtime")
    parser.add_argument("--count", type=int, default = 1, help = "whole number representing number of patients to generate")
    parser.add_argument("--state", type=str, default="Texas", help = "name of state whose census data we will sample to generate our population")
    parser.add_argument("--city", type=str, help = "optional, name of city to sample from")
    parser.add_argument("--min-age", type=int, help = "minimum age of individuals in population (min of 1)")
    parser.add_argument("--max-age", type=int, help = "maximum age of individuals in population (max of 100)")
    parser.add_argument("--keep-attribute", type=str)
    args = parser.parse_args()

    #support user relative paths (i.e. ~) then convert that to an absolute path
    synthea_path: Path = args.synthea_path
    synthea_path = synthea_path.expanduser().resolve()

    if not args.synthea_path.is_dir():
        parser.error(
            f"Synthea directory does not exist: {args.synthea_path}"
        )

    runner = args.synthea_path / "run_synthea"
    if not runner.is_file():
        parser.error(f"run_synthea not found in: {args.synthea_path}")

    return args

def generate(generation_request):
    run_synthea(synthea_path = generation_request.synthea_path,
                    count = generation_request.count,
                    state = generation_request.state, 
                    city = generation_request.city, 
                    min_age = generation_request.min_age, 
                    max_age = generation_request.max_age,
                    keep_attribute= generation_request.keep_attribute)
    patient_paths = create_simplified_patient_jsons(CURR_RUN_DIR / "csv", CURR_RUN_DIR / "json")
    for path in patient_paths:
        with open(path, "r") as patient_file:
            patient_dict = json.load(patient_file)
        patient_dict["metadata"] = {}
        patient_dict["metadata"]["keep_attributes"] = [generation_request.keep_attribute] if generation_request.keep_attribute else []
        with open(path, "w") as patient_file:
            json.dump(patient_dict, patient_file, indent = 2)

def run(generation_request):
    if generation_request:
        request_fields = generation_request
    else:
        generation_request = parse_args()
    generate(generation_request)
    


if __name__ == "__main__":
    run()
'''
Here we will test the ground truth assembly for our various tasks
'''
from mvp.tasks.medication_retrieval_v1.get_patient_meds import get_meds
import json
from pathlib import Path
'''
The gt should return an empty list if patient is deceased as of current date
Otherwise, it should return an accurate list of current meds
'''

TEST_DATA = Path(__file__).parent.parent / "test_data" / "test_patients"


def load_patient_record(filename: str):
    patient_path = Path(TEST_DATA / filename)
    with open(patient_path, "r") as patient_file:
            patient = json.load(patient_file)
    return patient

#deceased patient should have no current meds, return []
def test_deceased_patient_returns_empty_list():
    deceased_patient = load_patient_record("deceased_patient.json")
    assert get_meds(deceased_patient) == []

#living patient with 1 current meds, should return list with 1 string
def test_living_patient_returns_current_medication():
    living_patient_1_med = load_patient_record("living_patient_1_med.json")
    med_list = get_meds(living_patient_1_med)
    correct_answer = [206905]
    assert len(med_list) == len(correct_answer)
    for item in correct_answer:
        assert item in med_list

#living patient with no current meds, should return []
def test_living_patient_with_no_current_medications():
    living_patient_0_meds = load_patient_record("living_patient_0_meds.json")
    med_list = get_meds(living_patient_0_meds)
    correct_answer = []
    assert len(med_list) == len(correct_answer)
    for item in correct_answer:
        assert item in med_list
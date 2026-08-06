from .anesthesia_prep_v1.get_anesthesia_prep_gt import get_anesthesia_prep
from .medication_retrieval_v1.get_patient_meds import get_meds

GT_SCRIPTS = {"medication_retrieval_v1" : get_meds,
              "anesthesia_prep_v1" : get_anesthesia_prep}

def run(task, patient_json = None):
    return GT_SCRIPTS[task](patient_json)
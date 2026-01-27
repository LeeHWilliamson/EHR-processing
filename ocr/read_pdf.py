
from datetime import datetime
import json
from pdf2image import convert_from_path
from PIL import ImageFilter
import pytesseract
import random
import uuid

def config_degredation():
    possible_degredations = {"dpi_reduction" : [50, 100, 150], "gaussian_blur" : [0.5, 1.0, 1.5]}
    degredations = {}
    for degredation in possible_degredations.keys():
        include = random.randint(0, 1)
        if include == 1:
            select_param = random.randint(0, 2)
            degredations[degredation] = possible_degredations[degredation][select_param]
        else:
            degredations[degredation] = 0
    return degredations


def read_pdf(pdf_path):
    ocr_text = []
    degredations = {}
    text = ""
    degredation_settings = config_degredation()
    for degredation in degredation_settings:
        if degredation_settings[degredation] > 0:
            degredations[degredation] = degredation_settings[degredation]
    dpi = 150 #300 - degredation_settings["dpi_reduction"]
    psm = "--psm 6"
    image_batch = convert_from_path(pdf_path, dpi) #create image
    for image in image_batch:
        blurred = image.filter(ImageFilter.GaussianBlur(radius=degredation_settings["gaussian_blur"]))
        text = text + pytesseract.image_to_string(blurred, config = psm) + "\n" + "\n"
    # # Get verbose data including boxes, confidences, line and page numbers
    # print(pytesseract.image_to_data(image[0]))
    # # Get information about orientation and script detection
    # print(pytesseract.image_to_osd(image[0]))
    print(text)
    fileName = pdf_path.split("/")
    source_doc_id = fileName[1]
    fileName = fileName[-1].split(".")
    fileName = fileName[0]
    ocr_output_path = f"ocr/{source_doc_id}.txt"
    with open(ocr_output_path, "w") as file:
        file.write(text)
    ocr_id = f"ocr_{uuid.uuid4()}"
    ocr_log = {
        "ocr_id" : ocr_id,
        "source_doc_id" : source_doc_id,
        "output_local" : ocr_output_path,
        "source_file": fileName,
        "num_pages" : len(image_batch),
        "dpi": dpi,
        "engine": "pytesseract",
        "psm": psm,
        "timestamp": datetime.utcnow().isoformat(),
        "degredations" : degredations
    }
    with open(f"logs/ocr/{ocr_id}", "w") as file:
        json.dump(ocr_log, file, indent = 2)
    return ocr_log

def score_ocr(ocr_log):
    ocr_file = ocr_log["output_local"]
    with open(f"documents/{ocr_log["source_doc_id"]}/document.json", "r") as file: #get document so we can know what entities and fields should be present
        doc_instance = json.load(file)
    patient_directory = doc_instance["patient_id"].split("_") #FORMAT PATIENT DIRECTORY NAME BECAUSE I DIDNT SAVE THEM WITH PROPER NAME
    patient_directory = patient_directory[1]
    with open(f"patients/{patient_directory}/patient.json", "r") as file: #get patient so we know what exact values should be present
        patient_instance = json.load(file)
    with open(ocr_file, 'r') as file: #get ocr output
        ocr_output = file.read()
    processed_output = " ".join(ocr_output.lower().split()) #convert to processed string
    print(processed_output)
    checks = {}
    for entity_class, entity_list in doc_instance["entities_provided"].items(): #entity_class is observations, encounters, etc, entity_list is the associated list of entity dicts
        for entity in entity_list: #iterate thru each entity dict
            checks[entity["entity_id"]] = {}
            for realized_field in entity["fields"]: #iterate thru list of fields in doc for this entity
                checks[entity["entity_id"]][realized_field] = "no match found" #default to 'no_match_found'
                for entity_patient in patient_instance[entity_class]: #iterate thru all entities in patient to try and match field
                    if str(entity_patient[realized_field]).lower() in processed_output:
                        checks[entity["entity_id"]][realized_field] = "match found"
                    else:
                        # checks[entity["entity_id"]][realized_field] = "no match found"
                        continue
    matches = 0
    misses = 0
    for entity, checkDict in checks.items():
        for field, result in checkDict.items():
            if result == "match found":
                matches += 1
            else:
                misses += 1
    ocr_eval = {
        "eval_id" : f"eval_f{uuid.uuid4()}",
        "doc_id" : doc_instance["doc_id"],
        "ocr_id" : ocr_log["ocr_id"],
        "checks" : checks,

        "fields_found": matches,
        "fields_missed": misses
    }
    with open(f"logs/ocr_eval/{ocr_eval["eval_id"]}.json", "w") as file:
        json.dump(ocr_eval, file, indent=2)          

ocr_log = read_pdf("documents/doc_2a568192-03e6-4521-a092-f38b911358ba/test_obs_render.pdf")                
#since we have the doc, we have the GT of the entities and fields that made it to the doc, connect this to the patient to get the exact values, and see if those values are in
#output txt file
score_ocr(ocr_log)
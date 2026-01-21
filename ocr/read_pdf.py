
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
    degredations = []
    text = ""
    degredation_settings = config_degredation()
    for degredation in degredation_settings:
        if degredation_settings[degredation] > 0:
            degredations.append(degredation)
    dpi = 100
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
    fileName = fileName[-1].split(".")
    fileName = fileName[0]
    with open(f"ocr/{fileName}.txt", "w") as file:
        file.write(text)
    ocr_id = f"ocr_{uuid.uuid4()}"
    ocr_log = {
        "ocr_id" : ocr_id,
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

read_pdf("documents/doc_2a568192-03e6-4521-a092-f38b911358ba/test_obs_render.pdf")                


from datetime import datetime
import json
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import uuid

def read_pdf(pdf_path):
    ocr_text = []
    dpi = 300
    psm = "--psm 6"
    image = convert_from_path(pdf_path, dpi)
    text = pytesseract.image_to_string(image[0], config = psm)
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
        "num_pages" : len(image),
        "dpi": dpi,
        "engine": "pytesseract",
        "psm": psm,
        "timestamp": datetime.utcnow().isoformat(),
    }
    with open(f"logs/ocr/{ocr_id}", "w") as file:
        json.dump(ocr_log, file, indent = 2)

read_pdf("test_obs_render.pdf")                

from reportlab.pdfgen import canvas
import json



'''
we pass document
we write to text file
'''
def write_obs_table_pdf(document, patient):
    c= canvas.Canvas(f"documents/{document["doc_id"]}/test_obs_render.pdf", pagesize=(595.27, 841.89))
    xCoord = 50
    yCoord = 780
    for key, value in document.items():
        if key == "entities_provided":
            for entity_type, entity_list in document[key].items():
                for entity_dict in entity_list:
                    observation_id = entity_dict["entity_id"]
                    for obs_dict in patient["observations"]:
                        if obs_dict["id"] == observation_id:
                            for field in obs_dict:
                                if field in entity_dict["fields"]:
                                    # file.write(f"{field} {obs_dict[field]}\n")
                                    toWrite = field + " " + obs_dict[field]
                                    print(toWrite)
                                    c.drawString(xCoord+20, yCoord, toWrite)
                                    yCoord -= 16
        else:
            # print(key, value)
            toWrite = key + " " + value
            print(toWrite)
            c.drawString(xCoord, yCoord, toWrite)
            yCoord -= 16
    c.showPage()
    c.save()

with open("documents/doc_2a568192-03e6-4521-a092-f38b911358ba/document.json") as file:
    debug_doc = json.load(file)
debug_patient_id = debug_doc["patient_id"].split('_')[1]
with open(f"patients/{debug_patient_id}/patient.json") as file:
    debug_patient = json.load(file)
write_obs_table_pdf(debug_doc, debug_patient)

# c = canvas.Canvas("bork.pdf", pagesize=(595.27, 841.89)) #A4 pagesize

# c.drawString(50, 780, "bork")

# c.showPage()

# c.save()
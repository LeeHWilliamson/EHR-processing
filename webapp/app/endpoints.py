from fastapi import FastAPI, HTTPException, Request
#FileResponse is a FastAPI class that sends a file back as HTTP reponse
#which the browser then interprets
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel
from ..generate_patients.generate_patients import run as generate_patients
from ..generate_patients.patient_tile import generate_tile_summary
# from ..create_tools.query_entities import query_entities
from ..create_tools.query_current_patients import get_key_field_options, get_fields, query_entities

WEBAPP_DIR = Path(__file__).resolve().parent.parent
PATIENTS_DIR = WEBAPP_DIR / "patients" / "current_run" / "full_patients" / "normalized_json"

app = FastAPI()
'''
We want all static requests to be handled by our static directory
app.mount says 'any request whose path starts with static should be sent
to webapp/static because that is our StaticFiles application'
That's where our javascript is!
'''
app.mount(
    "/static",
    StaticFiles(directory="webapp/static"),
    name="static",
)
class PatientGenerationRequest(BaseModel): #run synthea
    synthea_path: str
    count: int
    state: str
    city: str | None = None
    min_age: int | None = None
    max_age: int | None = None
    keep_attribute: str | None = None


@app.get("/")
def home():
    return FileResponse("webapp/static/index.html")

@app.get("/patients")
def get_patients():
    return generate_tile_summary()

@app.get("/patients/entities/current")
def get_current_entities():
    return query_entities()

# @app.get("/patients/entities/all")
# def get_all_entities():
#     return get_fields()

@app.get("/patients/key_fields")
def get_possible_key_fields(selected_entities: list[str]):
    return get_key_field_options(selected_entities)

@app.get("/patients/fields")
def display_entity_fields(entity: str):
    return get_fields(entity)



# @app.get("/patients/{patient_id}/tile")
# def get_patient_tile(patient_ids: list[str]):
#     return generate_tile_summary(patient_ids)

@app.post("/generate")
def generate(request: PatientGenerationRequest):
    print(request)
    generate_patients(request)
from fastapi import FastAPI, HTTPException, Request
#FileResponse is a FastAPI class that sends a file back as HTTP reponse
#which the browser then interprets
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel
from ..generate_patients.generate_patients import run as generate_patients
from ..generate_patients.patient_tile import generate_tile_summary

WEBAPP_DIR = Path(__file__).resolve().parent.parent
PATIENTS_DIR = WEBAPP_DIR / "patients" / "current_run" / "json"

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

# @app.get("/patients/{patient_id}/tile")
# def get_patient_tile(patient_ids: list[str]):
#     return generate_tile_summary(patient_ids)

@app.post("/generate")
def generate(request: PatientGenerationRequest):
    print(request)
    generate_patients(request)
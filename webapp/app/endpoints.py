from fastapi import FastAPI, HTTPException, Request
#FileResponse is a FastAPI class that sends a file back as HTTP reponse
#which the browser then interprets
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from ..generate_patients.generate_patients import run as generate_patients

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

@app.post("/generate")
def generate(request: PatientGenerationRequest):
    print(request)
    generate_patients(request)
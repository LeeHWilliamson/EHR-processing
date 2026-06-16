import json
import requests
BASE_URL = "http://127.0.0.1:8000" #url on our local machine
'''
~~~~~~~FUNCTION TOOLS FOR AGENT~~~~~~~~~
Recall earlier that we wrote some API endpoints (i.e. functions + url locations to execute those functions).
Also recall that those functions our executed automatically by the backend when those urls are accessed.
Here, we create wrappers for our agent to use to access those urls to retrieve the data it needs.
Our first wrapper is get_patient.
The only thing this wrapper is doing is sending a request to http://127.0.0.1:8000/patients/{patient_id} (the url of our get_patient endpoint)
and assembling whatever it gets back (whether that be an error, an access denial, or data, etc) into a JSON.
Since these wrappers are functions used by our AI agent, we can refer to them as function 'tools.'
'''
def get_patient(patient_id: str):
    response = requests.get(
        f"{BASE_URL}/patients/{patient_id}",
        headers={
            "X-Agent-ID": "agent_brobot",
            "X-Task-ID": "retrieve currents meds"
        }
    )
    response.raise_for_status()
    return response.json()

def get_observations(patient_id: str):
    response = requests.get(
        f"{BASE_URL}/patients/{patient_id}/observations",
        headers={
            "X-Agent-ID": "agent_brobot",
            "X-Task-ID": "retrieve currents meds"
        }
    )

    response.raise_for_status()
    return response.json()

def get_encounters(patient_id: str):
    response = requests.get(
        f"{BASE_URL}/patients/{patient_id}/encounters",
        headers={
            "X-Agent-ID": "agent_brobot",
            "X-Task-ID": "retrieve currents meds"
        }
    )

    response.raise_for_status()
    return response.json()

def get_medications(patient_id: str):
    response = requests.get(
        f"{BASE_URL}/patients/{patient_id}/medications",
        headers={
            "X-Agent-ID": "agent_brobot",
            "X-Task-ID": "retrieve currents meds"
        }
    )

    response.raise_for_status()
    return response.json()

def get_allergies(patient_id: str):
    response = requests.get(
        f"{BASE_URL}/patients/{patient_id}/allergies",
        headers={
            "X-Agent-ID": "agent_brobot",
            "X-Task-ID": "retrieve currents meds"
        }
    )

    response.raise_for_status()
    return response.json()

def get_conditions(patient_id: str):
    response = requests.get(
        f"{BASE_URL}/patients/{patient_id}/conditions",
        headers={
            "X-Agent-ID": "agent_brobot",
            "X-Task-ID": "retrieve currents meds"
        }
    )

    response.raise_for_status()
    return response.json()

def get_immunizations(patient_id: str):
    response = requests.get(
        f"{BASE_URL}/patients/{patient_id}/immunizations",
        headers={
            "X-Agent-ID": "agent_brobot",
            "X-Task-ID": "retrieve currents meds"
        }
    )

    response.raise_for_status()
    return response.json()

def get_devices(patient_id: str):
    response = requests.get(
        f"{BASE_URL}/patients/{patient_id}/devices",
        headers={
            "X-Agent-ID": "agent_brobot",
            "X-Task-ID": "retrieve currents meds"
        }
    )

    response.raise_for_status()
    return response.json()

def get_procedures(patient_id: str):
    response = requests.get(
        f"{BASE_URL}/patients/{patient_id}/procedures",
        headers={
            "X-Agent-ID": "agent_brobot",
            "X-Task-ID": "retrieve currents meds"
        }
    )

    response.raise_for_status()
    return response.json()

def get_careplans(patient_id: str):
    response = requests.get(
        f"{BASE_URL}/patients/{patient_id}/careplans",
        headers={
            "X-Agent-ID": "agent_brobot",
            "X-Task-ID": "retrieve currents meds"
        }
    )

    response.raise_for_status()
    return response.json()

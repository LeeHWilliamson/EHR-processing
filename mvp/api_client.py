import json
import requests
BASE_URL = "http://127.0.0.1:8000" #url on our local machine

'''
~~~~~~~~~~~~~DATABASE SCHEMA~~~~~~~~~~~~~~~~~~~
When evaluating an AI agent, it is important to consider how a specific database schema may impact performance.
For example, does spreading out patient information across multiple tables lead to the agent accessing more data that it
shouldn't? 
That said, evaluating this requires an agent to be able to use the same set of tools to retrieve data across different
schemas. I.e. where patient data lives in the DB should change, but to the agent its "retrieve patient data" tool is
functionally the same. 
It also requires the agent not have any knowledge of the schema it's navigating.
So here, we make it so the schema can change without the AI's tools changing.
'''
ACTIVE_SCHEMA = "normalized_v1"

def set_schema(schema: str):
    global ACTIVE_SCHEMA
    ACTIVE_SCHEMA = schema


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
        params={"schema": ACTIVE_SCHEMA},
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
        params={"schema": ACTIVE_SCHEMA},
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
        params={"schema": ACTIVE_SCHEMA},
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
        params={"schema": ACTIVE_SCHEMA},
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
        params={"schema": ACTIVE_SCHEMA},
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
        params={"schema": ACTIVE_SCHEMA},
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
        params={"schema": ACTIVE_SCHEMA},
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
        params={"schema": ACTIVE_SCHEMA},
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
        params={"schema": ACTIVE_SCHEMA},
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
        params={"schema": ACTIVE_SCHEMA},
        headers={
            "X-Agent-ID": "agent_brobot",
            "X-Task-ID": "retrieve currents meds"
        }
    )

    response.raise_for_status()
    return response.json()

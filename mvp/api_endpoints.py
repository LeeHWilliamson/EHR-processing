'''
This file contains the API endpoints for the MVP (and some server side helper functions). These endpoints are essentially points of interaction between a server and a client. 
They typically rely on decorator functions like 

'''
from fastapi import FastAPI, HTTPException, Request
from mvp.schema_adapters import flat_v1, normalized_v1
import sqlite3
from datetime import datetime, timezone
import json

DB_DIR = "/home/leeha/tools/sqlite"
#schema adapter filenames
ADAPTERS = {
    "flat_v1": flat_v1,
    "normalized_v1": normalized_v1,
}
'''
#we are using FastAPI decorators
#app object will have decorator functions, decorator functions are nested argument functions with an outer function like 'get', 
#and inner functions that typically take functions as arguments. In the case of FastAPI, the name of the decorator is just telling you 
#how the functions you pass to it will be handled
''' 
app = FastAPI()

#server side helper function, not an api endpoint but will be called at API endpoints
def get_connection(schema: str):
    db_path = f"{DB_DIR}/{schema}.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

#server side helper function for updating log table
def log_api_call(
        schema,
        request: Request,
        endpoint: str,
        method: str,
        status_code: int,
        rows_returned: int = 0,
        patient_id: str | None = None,
        encounter_id: str | None = None,
):
    agent_id = request.headers.get("X-Agent-ID")
    task_id = request.headers.get("X-Task-ID")

    conn = get_connection(schema)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO api_access_log (
            timestamp, agent_id, task_id, endpoint, method,
            patient_id, encounter_id, status_code, rows_returned, query_params
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            agent_id,
            task_id,
            endpoint,
            method,
            patient_id,
            encounter_id,
            status_code,
            rows_returned,
            json.dumps(dict(request.query_params)),
        ),
    )

    conn.commit()
    conn.close()

def get_adapter(schema: str):
    try: 
        return ADAPTERS[schema]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown schema: {schema}")
'''
Now we get to the actual API endpoints
Here, the @ denotes a decorator as we described earlier. .get is the outer function that takes a predefined path as an argument. .get also
contains an inner function (referred to as a decorator, it takes an instance of the function we define here, get_patient,
as an argument and handles it according to the function definition. In this case, 'handling it' means adding it to a lookup table that says what functions to call at
what paths. So we just added the function get_patient to the "/patients/{patient_id}" url path
So the following code is doing the following...
On startup, tell our app that the function, get_patient is associated with GET operations. Please register it in a lookup table associated
with the url route "/patients/{patient_id}". If someone accesses that URL, please execute the function.
'''
#retrieve patients by id
@app.get("/patients/{patient_id}")
def get_patient(patient_id: str, schema: str, request: Request):
    adapter = get_adapter(schema)
    conn = get_connection(schema)
    try:
        patient = adapter.get_patient(conn, patient_id)
    finally:
        conn.close()
    # cursor = conn.cursor()

    # cursor.execute(
    #     "SELECT * FROM patients WHERE id = ?",
    #     (patient_id,),
    # )
    # #id is the primary key that corresponds to a specific patient, so row should only contain 1 record lol
    # row = cursor.fetchone()
    # conn.close()

    if patient is None:
        log_api_call(
            schema,
            request=request,
            endpoint=f"/patients/{patient_id}",
            method="GET",
            patient_id=patient_id,
            status_code=404,
        )
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # result = dict(row)

    log_api_call(
        schema,
        request=request,
        endpoint=f"/patients/{patient_id}",
        method="GET",
        patient_id=patient_id,
        status_code=200,
        rows_returned=1,
    )

    return patient

#get list of encounters associated with a patient
@app.get('/patients/{patient_id}/encounters')
def get_patient_encounters(patient_id: str, schema: str, request: Request):
    adapter = get_adapter(schema)
    conn = get_connection(schema)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM encounters WHERE patient_id = ?",
        (patient_id,),
    )
    #fetch all the results
    rows = cursor.fetchall()
    conn.close()

    #not all patients have all entities so we should always include this
    if rows is None:
        log_api_call(
            request=request,
            endpoint=f"/patients/{patient_id}/encounters",
            method="GET",
            patient_id=patient_id,
            status_code=404,
        )
        raise HTTPException(status_code=404, detail="No encounters associated with that patient ID")
    
    results = [dict(row) for row in rows]

    log_api_call(
        request=request,
        endpoint=f"/patients/{patient_id}/encounters",
        method="GET",
        patient_id=patient_id,
        status_code=200,
        rows_returned=len(results),
    )

    return results

#Get list of medications associated with a patient
@app.get("/patients/{patient_id}/medications")
def get_patient_medications(patient_id: str, schema: str, request: Request):
    adapter = get_adapter(schema)
    #connect to server
    conn = get_connection(schema)
    #utilize adapter for schema specific SQL
    try:
        medications = adapter.get_medications(conn, patient_id)
    finally:
        conn.close()
    # #create cursor object (whatever that is)
    # cursor = conn.cursor()
    # #query db
    # cursor.execute("SELECT * FROM medications WHERE patient_id = ?", (patient_id,),)
    # #fetch all results
    # rows = cursor.fetchall()
    # #close connection
    # conn.close()
    #log attempt and outcome
    if medications is None:
        log_api_call(
            schema,
            request=request,
            endpoint=f"/patients/{patient_id}/medications",
            method="GET",
            patient_id=patient_id,
            status_code=404,
        )
        raise HTTPException(status_code=404, detail="No medications associated with that patient ID")
    #convert result to serializable format

    log_api_call(
        schema,
        request=request,
        endpoint=f"/patients/{patient_id}/medications",
        method="GET",
        patient_id=patient_id,
        status_code=200,
        rows_returned=len(medications),
    )
    return medications



#get all observations associated with a patient
@app.get("/patients/{patient_id}/observations")
def get_patient_observations(patient_id: str, schema: str, request: Request):
    adapter = get_adapter(schema)
    #connect to server
    conn = get_connection(schema)
    #create cursor
    cursor = conn.cursor()
    #query
    cursor.execute("SELECT * FROM observations WHERE patient_id = ?", (patient_id,),)
    #fetch results
    rows = cursor.fetchall()
    #close connection
    conn.close()
    #log failure
    if rows is None:
        log_api_call(
            request=request,
            endpoint=f"/patients/{patient_id}/observations",
            method="GET",
            patient_id=patient_id,
            status_code=404,
        )
        raise HTTPException(status_code=404, detail="No observations associated with that patient ID")
    #serialize
    results = [dict(row) for row in rows]
    #log success
    log_api_call(
        request=request,
        endpoint=f"/patients/{patient_id}/observations",
        method="GET",
        patient_id=patient_id,
        status_code=200,
        rows_returned=len(results),
    )
    #return
    return results


@app.get("/patients/{patient_id}/allergies")
def get_patient_allergies(patient_id: str, schema: str, request: Request):
    adapter = get_adapter(schema)
    #connect to db
    conn = get_connection(schema)
    cursor = conn.cursor()

    #query
    rows = cursor.execute("SELECT * FROM allergies WHERE patient_id = ?", (patient_id,),)

    if rows is None:
        log_api_call(
            request=request, 
            endpoint=f"/patients/{patient_id}/allergies",
            method="GET",
            patient_id=patient_id,
            status_code=404,
        )
        raise HTTPException(status_code=404, detail="No observations associated with that patient ID")
    #serialize
    results = [dict(row) for row in rows]
    #log_success
    log_api_call(
        request=request,
        endpoint=f"/patients/{patient_id}/allergies",
        method="GET",
        patient_id=patient_id,
        status_code=200,
        rows_returned=len(results),
    )
    return results
#get patient conditions
@app.get("/patients/{patient_id}/conditions")
def get_patient_conditions(patient_id: str, schema: str, request: Request):
    adapter = get_adapter(schema)
    #connect to db
    conn = get_connection(schema)
    cursor = conn.cursor()

    #query
    rows = cursor.execute("SELECT * FROM conditions WHERE patient_id = ?", (patient_id,),)

    if rows is None:
        log_api_call(
            request=request, 
            endpoint=f"/patients/{patient_id}/conditions",
            method="GET",
            patient_id=patient_id,
            status_code=404,
        )
        raise HTTPException(status_code=404, detail="No conditions associated with that patient ID")
    #serialize
    results = [dict(row) for row in rows]
    #log_success
    log_api_call(
        request=request,
        endpoint=f"/patients/{patient_id}/conditions",
        method="GET",
        patient_id=patient_id,
        status_code=200,
        rows_returned=len(results),
    )
    return results
#get patient immunizations
@app.get("/patients/{patient_id}/immunizations")
def get_patient_immunizations(patient_id: str, schema: str, request: Request):
    adapter = get_adapter(schema)
    #connect to db
    conn = get_connection(schema)
    cursor = conn.cursor()

    #query
    rows = cursor.execute("SELECT * FROM immunizations WHERE patient_id = ?", (patient_id,),)

    if rows is None:
        log_api_call(
            request=request, 
            endpoint=f"/patients/{patient_id}/immunizations",
            method="GET",
            patient_id=patient_id,
            status_code=404,
        )
        raise HTTPException(status_code=404, detail="No immunizations associated with that patient ID")
    #serialize
    results = [dict(row) for row in rows]
    #log_success
    log_api_call(
        request=request,
        endpoint=f"/patients/{patient_id}/immunizations",
        method="GET",
        patient_id=patient_id,
        status_code=200,
        rows_returned=len(results),
    )
    return results
#get patient devices
@app.get("/patients/{patient_id}/devices")
def get_patient_devices(patient_id: str, schema: str, request: Request):
    adapter = get_adapter(schema)
    #connect to db
    conn = get_connection(schema)
    cursor = conn.cursor()

    #query
    rows = cursor.execute("SELECT * FROM devices WHERE patient_id = ?", (patient_id,),)

    if rows is None:
        log_api_call(
            request=request, 
            endpoint=f"/patients/{patient_id}/devices",
            method="GET",
            patient_id=patient_id,
            status_code=404,
        )
        raise HTTPException(status_code=404, detail="No devices associated with that patient ID")
    #serialize
    results = [dict(row) for row in rows]
    #log_success
    log_api_call(
        request=request,
        endpoint=f"/patients/{patient_id}/devices",
        method="GET",
        patient_id=patient_id,
        status_code=200,
        rows_returned=len(results),
    )
    return results
#get patient procedures
@app.get("/patients/{patient_id}/procedures")
def get_patient_procedures(patient_id: str, schema: str, request: Request):
    adapter = get_adapter(schema)
    #connect to db
    conn = get_connection(schema)
    cursor = conn.cursor()

    #query
    rows = cursor.execute("SELECT * FROM procedures WHERE patient_id = ?", (patient_id,),)

    if rows is None:
        log_api_call(
            request=request, 
            endpoint=f"/patients/{patient_id}/procedures",
            method="GET",
            patient_id=patient_id,
            status_code=404,
        )
        raise HTTPException(status_code=404, detail="No procedures associated with that patient ID")
    #serialize
    results = [dict(row) for row in rows]
    #log_success
    log_api_call(
        request=request,
        endpoint=f"/patients/{patient_id}/procedures",
        method="GET",
        patient_id=patient_id,
        status_code=200,
        rows_returned=len(results),
    )
    return results
#get patient careplans
@app.get("/patients/{patient_id}/careplans")
def get_patient_careplans(patient_id: str, schema: str, request: Request):
    adapter = get_adapter(schema)
    #connect to db
    conn = get_connection(schema)
    cursor = conn.cursor()

    #query
    rows = cursor.execute("SELECT * FROM careplans WHERE patient_id = ?", (patient_id,),)

    if rows is None:
        log_api_call(
            request=request, 
            endpoint=f"/patients/{patient_id}/careplans",
            method="GET",
            patient_id=patient_id,
            status_code=404,
        )
        raise HTTPException(status_code=404, detail="No careplans associated with that patient ID")
    #serialize
    results = [dict(row) for row in rows]
    #log_success
    log_api_call(
        request=request,
        endpoint=f"/patients/{patient_id}/careplans",
        method="GET",
        patient_id=patient_id,
        status_code=200,
        rows_returned=len(results),
    )
    return results

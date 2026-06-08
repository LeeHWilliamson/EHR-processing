# Synth-EHR

## Purpose
Synth-EHR is a synthetic healthcare database platform for generating and hosting synthetic patient electronic health records and implementing and evaluating AI tools and workflows. Patient data is distributed across an electronic health record database backend. This synthetic data is intended to be deployed in medical contexts for the purpose of evaluating AI tools in a secure environment without providing AI with access to actual patient records. Patient records and documents are also stored as plain text ground truths to facilitate metric analysis of the efficacy of AI tools.

## Motivation
Modern AI tools show great promise in enhancing medical workflow tasks such as assembling relevant medical histories, creating tailored treatment plans, and more. Deploying AI tools in a medical context, however, requires an exhaustive evaluation of the tool's performance as well as its risks of hallucination, privacy violation, and data leakage. Such an evaluation is uniquely challenging in the medical field. While true electronic health records contain patient data, they rarely do so in a way that trvializes AI output assessment.
For example, say one wanted to investigate the ability of an AI model to recreate a patient's health history over the last few years. Corroborating the AI's assembled records against the ground truth present in the EHR is a mostly manual task that requires different steps for different patients. 
While there are tools available that assist in generating quality synthetic patient data, these tools do not recreate the full zero-trust database environment in which any medical AI tool will work. Thus these tools don't allow for benchmarking AI tools in actual workflows. This tool seeks to build on an existing patient data generation tool (Synthea) by creating a local platform for hosting synthetic data.
By generating synthetic patient health data, we can generate a large amount of quality data without risking privacy violations and assemble an easily interpretable ground truth for each generated health record. By hosting this data in a simulated EHR environment that reproduces common healthcare information access patterns, we can test AI tools in an a way that actually allows us to assess their performance in an actual healthcare system.
By offering a platform that allows investigators to audit AI performance in realistic medical workflows, this tool can enable researchers to develop better AI models. Furthermore, it can enable healthcare providers to identify failure modes and compare AI approaches before exposing real patient data. 


## Core Features
- Synthetic patient generation via Synthea
- Simulated EHR backend with API-based data access
- Ground-truth patient records for automated evaluation
- AI workflow tracing and audit logging
- Quantitative metrics for reconstruction accuracy, omissions, and hallucinations
- Dashboard for patient exploration and AI performance analysis


<!-- ## Current Architecture

![Architecture Diagram](assets/rough_ehrAI_diagram.drawio.png) -->

## Patient, document, and log structure
For a more detailed look, please go to schemas folder.

### Patient
Each patient will consist of various entities (e.g. allergies, conditions, medications), and each entity will consist of fields (e.g. date started/observed, name, units). 
These fields and entities are what get mapped to rendered documents.
```json
{
"patient": {
    "id": "string",
    "firstName": "string",
    "lastName": "string",
    "dob": "YYYY-MM-DD",
    "gender": "string",
    "entities": []
},
"allergies": [
],
"careplans": [
],
"devices": [
],
"encounters":[
],
"imaging_studies":[
],
"conditions": [
],
"immunizations":[
],
"medications":[
],
"procedures":[
],
"observations":[
]
}
```
### Document
Each document receives patient entities and fields based on the type of document being rendered.
```json
{
  "doc_id": "string",
  "doc_category": "string",
  "template_id": "string",
  "patient_id": "string",
  "date": "YYYY-MM-DD",

  "entities_provided": {
    "<entity_type>": [
      {
        "entity_id": "string",
        "fields": ["string", "..."]
      }
    ]
  }
}
```
### Patient -> Documents Mappings
Mappings track what entities and fields were received by documents (expected), what fields were actually rendered (realized), and what fields were omitted (to simulate mistakes in record keeping)
```json
{
  "log_id": "log_4b59f091-595e-4bf6-a490-a37557c0ce90",
  "patient_id": "pat_fc817953-cc8b-45db-9c85-7c0ced8fa90d",
  "doc_id": "doc_fc156d69-d41f-4747-beea-0c7d9c6c8c82",
  "doc_category": "obs_table",
  "template_id": "obs_date_body_measurements_v1",
  "expected_entities": [
    "obs_2dc14d6e-5305-11f1-a6a5-00155d35d14f",
    "obs_2dc14d96-5305-11f1-a6a5-00155d35d14f",
    "obs_2dc14da0-5305-11f1-a6a5-00155d35d14f"
  ],
  "realized_entities": [
    "obs_2dc14d6e-5305-11f1-a6a5-00155d35d14f",
    "obs_2dc14d96-5305-11f1-a6a5-00155d35d14f",
    "obs_2dc14da0-5305-11f1-a6a5-00155d35d14f"
  ],
  "omitted_entities": "none",
  "field_expectations": {
    "observations": {
      "obs_2dc14d6e-5305-11f1-a6a5-00155d35d14f": {
        "expected_fields": [
          "description",
          "encounter",
          "value",
          "units"
        ],
        "realized_fields": [
          "description",
          "encounter",
          "value"
        ],
        "omitted_fields": ["units"],
        "omission_mode": "FORGOT_UNITS"
      }
    }
  },
  "omitting_mode": "FORGOT_UNITS",
  "degredations": ["blur"]
}
```

<!-- ### Example degraded documents
The following image pair shows an observations document with and without degradations. In this case, the degradation is the ommission of units for each measurement
![Full Document](assets/no_ommission_doc.png)
![Without Units](assets/forgot_units_doc.png) -->

### Current status
Developed pipeline that creates patient JSONs, creates documents that contain body measurement information, reads these documents to text via OCR, and measures OCR accuracy

### Future steps
- Create GUI that allows users to easily set population parameters for generated patients
- Convert JSON structure to simulated electronic health record structure
- Implement AI tool for reconstructing patient records from documents
- Dashboard for viewing patient summary data and AI tool performance
- Generation of PDFs, text files, and images for patient health data
- Random degradation of generated documents via effects such as blur, image downsampling, typos, information ommission and more*
- OCR/AI pipeline for recreating patient health records from generated documents
- Simple EHR frontend

### MVP
- Synthetic patient JSON
- SQLite/Postgres tables
- FastAPI endpoints
- AI agent queries endpoints
- AI outputs reconstructed JSON
- evaluator compares AI JSON vs ground truth
- Streamlit dashboard shows errors

Stack
# Synth-EHR

## Purpose
Synth-EHR is an application for evaluating AI Agents in a clinical setting, assessing accuracy and performance of the agents as well as the degree to which an agent's workflow follows HIPPA compliance and in-house rules of individual healthcare providers. Assess AI agents on your system, at scale, without exposing protected information. 

## At a glance
This tool allows users to easily create large numbers of realistic patients, organize and distribute patient data across customizable databases, design custom tools for accessing patient data, assign AI agents with data tasks, and intuitively measure and visualize agent accuracy, workflow adherence, token usage, and more.

## Motivation
    Modern AI tools show great potential in their ability to carry out nuanced clinical tasks and are already being adopted for tasks such as summarizing patient medical history, interpreting imaging results, and supporting accurate diagnosis. Evaluating the efficacy of AI tools for certain tasks, however, can be subjective, time-intensive, and require expert feedback. These complications largely stem from the fact that patient health records are dynamic, ever-growing entities. New information is being added to these records all the time, and determining the relevance of any specific information to the current clinical task often requires a human in the loop.
    Furthermore, medical providers have no shortage of vendors that offer AI agents for handling clinical tasks. These AI agents often come with data outlining their accuracy and ability to generally handle complex tasks. As anyone who has used AI tools in a clinical setting will testify, however, the performance of a specific AI agent can vary. Performance can vary by agent, task, and by the exact layout of data contained in an provider's servers. Meanwhile, the medical providers are often limited in the options they have for determining whether any particular AI agent will be successful in their specific context without exposing protected patient data to external AI agents.
    By using research-backed models of disease progression, however, this application generates patients from the ground up. The exact conditions that a patient presents with at any time are known, as well as the exact time sequence of symtpoms that proceeded that condition, and this ground truth is contained in a single datastructure for each patient. By assembling patients in this way, we can objectively determine the ideal outcome for a variety of clinical tasks at scale and without needing human intervention.
These complications largely stem from the fact that there is almost never a single objective ground truth for a patient that can be used to easily answer these questions. For example, when it comes to summarizing a patient's medical history as is relevant to their current conditions, the information for doing that does exist in the patient's electronic health record, but not in one single place. Furthermore, the exact appointment notes, lab results, and other information that needs to be captured can vary greatly from patient to patient.

## Core Features
- Generating high-quality synthetic patients: By implementing the Synthea platform for creating patients, we utilize research-backed models of disease progression. This means that generated patient populations accurately recreate real-world populations, and individual patient health histories mirror realistic disease progression. Generate patient populations that mirror real-world demographic distributions, or insert individual patients according to your needs.
- Customizable databases for hosting simulated data: This application supports custom database schema designs. The user decides what data will exist on what tables, what entities should be allowed to access these tables, and what data standards these database adheres to, whether it be FHIR, C-CDA, or something else.
- No-code generation of data querying tools based on user specifications: The user decides what tools exist for accessing patient data and what data those tools expose. Synth-EHR automatically generates the tools based on the database design set by the user.
- Quantitative AI evaluation that is agnostic to database design and specific AI agent being used: this application includes end-to-end implementations for carrying out and evluating AI performance in routine clinical tasks such as patient medical history summaries, collection of relevant conditions, and health diagnoses. Users can create customized tasks for their simulated databases, or edit existing tasks, and the application will pass these workflows on the user's AI agent of choice.
- Quantifying, performance, workflow adherence, and resource usage at scale: Visualize performance of an AI agent across different tasks, compare workflows used by different AI models to evaluate compliance, quantify token usage for different agents across different tasks, and much more. 

## Purpose
Synth-EHR is a healthcare database platform for generating and hosting synthetic patient electronic health records and implementing and evaluating AI tools and workflows. Patient data is distributed across an electronic health record database backend. This synthetic data is intended to be deployed in medical contexts for the purpose of evaluating AI tools in a secure environment without providing AI with access to actual patient records. Patient records and documents are also stored as plain text ground truths to facilitate metric analysis of the efficacy of AI tools.

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


'''
Docstring for schemas.document_schemas
'''
'''
VisitSummarySchema
this schema applies to 2 different documents, those generated for outpatient visits (Visit Summaries, when the encounter end date is the same as the encounter start date), and those generated for inpatient visits (Discharge
Summaries, when the encounter end date is different from the encounter start date). It will include all details for encounters, conditions, procedures, medications, allergies, careplans, immunizations, and devices associated with the same
encounterID, it will provide only the ids of patient, imaging_studies and observations
'''
VisitSummarySchema = {
  "doc_category": "visit_summary",
  "allowed_entities": ["encounters", "patients", "conditions", "procedures", "medications", "allergies", "careplans", "devices", "imaging_studies", "immunizations", "observations"],
  "required_entities": ["encounters", "patients"],
  "optional_entities": ["conditions", "procedures", "medications", "allergies", "careplans", "devices", "imaging_studies", "immunizations", "observations"]
}

'''
MedListSchema: Will include patient medication information, some templates will have current and past medications, some templates will have only current, and others will have only past medications, some templates will include vaccinations
information for each medication will be description (name and dosage), reason, startDate, endDate
information for patient will simply be patient id
if included, immunizations info will include name, id, date
'''
MedListSchema = {
    "doc_category": "med_list",
    "allowed_entities" : ["medications", "patients", "immunizations"],
    "required_entities" : ["medications", "patients"],
    "optional_entities" : ["immunizations"],
    }

'''
ObservationTableSchema: Will include all observation results data for a specific date, the associated encounterid, and any coditions associated with that encounter. Measured labs will be on separate template from other
observations (e.g. smoking questionnare response)
'''
ObservationTableSchema = {
    "doc_category": "obs_table",
    "allowed_entities" : ["observations", "patients", "encounters", "conditions"],
    "required_entities" : ["observations", "patients"],
    "optional_entities" : ["encounters", "conditions"]
}

'''
RadiologyReportSchema: Will include all imaging_study information associated with a specific encounterID:date combination, will include descriptions of any devices associated with the patient
'''
RadiologyReportSchema = {
    "doc_category": "rad_report",
    "allowed_entities" : ["imaging_studies", "patients", "encounters", "devices"],
    "required_entities" : ["imaging_studies", "patients", "encounters"],
    "optional_entities" : ["devices"]
}

'''
PatientDemographicSchema: Will Include all patient identifying information
'''
PatientDemographicSchema = {
    "doc_category": "demographic_form",
    "allowed_entities" : ["patients"],
    "required_entities" : ["patients"],
    "optional_entities" : []
}
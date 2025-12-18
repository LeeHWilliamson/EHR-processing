'''
Docstring for schemas.document_schemas
'''
'''
will include all information that happened for all encounters on a specific date. So if a patient has 2 encounters on 12/1/25, all info from both will be on the form (separate pages)
Will include any all information for any conditions that have an encounter id corresponding to an encounter id of an encounter on doc
Will include all procedure information for any procedures with encounter ids corresponding to encounters on doc
Same for medication
'''
VisitSummarySchema = {
  "allowed_entities": ["encounter", "condition", "procedure", "medication"],
  "required_entities": ["encounter"],
  "optional_entities": ["condition", "procedure", "medication"]
}

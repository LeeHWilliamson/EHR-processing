CREATE TABLE patients(
id TEXT PRIMARY KEY,
firstName TEXT,
lastName TEXT,
birthdate TEXT,
deathdate TEXT,
gender TEXT
, medications_blob TEXT);
CREATE TABLE api_access_log (
id INTEGER PRIMARY KEY AUTOINCREMENT,
timestamp TEXT NOT NULL,
agent_id TEXT,
task_id TEXT,
endpoint TEXT NOT NULL,
method TEXT NOT NULL,
patient_id TEXT,
encounter_id TEXT,
status_code INTEGER,
rows_returned INTEGER,
query_params TEXT);

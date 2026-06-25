CREATE TABLE patients(
id TEXT PRIMARY KEY,
firstName TEXT,
lastName TEXT,
birthdate TEXT,
deathdate TEXT,
gender TEXT
);
CREATE TABLE encounters(
id TEXT PRIMARY KEY,
patient_id TEXT,
type TEXT,
description TEXT,
reason TEXT,
startDate TEXT,
endDate TEXT,
startTime TEXT,
endTime TEXT,
FOREIGN KEY (patient_id)
REFERENCES patients(id)
);
CREATE TABLE allergies (
id TEXT PRIMARY KEY,
patient_id TEXT,
encounter TEXT,
start TEXT,
stop TEXT,
description TEXT,
FOREIGN KEY (patient_id)
REFERENCES patients(id),
FOREIGN KEY (encounter)
REFERENCES encounters(id)
);
CREATE TABLE careplans(
id TEXT PRIMARY KEY,
patient_id TEXT,
encounter TEXT,
startDate TEXT,
endDate TEXT,
description TEXT,
reasonDescription TEXT,
FOREIGN KEY (patient_id)
REFERENCES patients(id),
FOREIGN KEY (encounter)
REFERENCES encounters(id));
CREATE TABLE devices(
id TEXT PRIMARY KEY,
patient_id TEXT,
encounter TEXT,
startDate TEXT,
description TEXT,
FOREIGN KEY (patient_id)
REFERENCES patients(id),
FOREIGN KEY (encounter)
REFERENCES encounters(id));
CREATE TABLE conditions(
id TEXT PRIMARY KEY,
patient_id TEXT,
encounter TEXT,
condition TEXT,
startDate TEXT,
endDate TEXT,
FOREIGN KEY (patient_id)
REFERENCES patients(id),
FOREIGN KEY (encounter)
REFERENCES encounters(id));
CREATE TABLE immunizations(
id TEXT PRIMARY KEY,
patient_id TEXT,
encounter TEXT,
name TEXT,
date TEXT,
FOREIGN KEY (patient_id)
REFERENCES patients(id),
FOREIGN KEY (encounter)
REFERENCES encounters(id));
CREATE TABLE medications(
id TEXT PRIMARY KEY,
patient_id TEXT,
encounter TEXT,
description TEXT,
code TEXT,
reason TEXT,
startDate TEXT,
endDate TEXT,
FOREIGN KEY (patient_id)
REFERENCES patients(id),
FOREIGN KEY (encounter)
REFERENCES encounters(id));
CREATE TABLE procedures(
id TEXT PRIMARY KEY,
patient_id TEXT,
encounter TEXT,
description TEXT,
reason TEXT,
date TEXT,
time TEXT,
FOREIGN KEY (patient_id)
REFERENCES patients(id),
FOREIGN KEY (encounter)
REFERENCES encounters(id));
CREATE TABLE observations(
id TEXT PRIMARY KEY,
patient_id TEXT,
encounter TEXT,
description TEXT,
value TEXT,
units TEXT,
date TEXT,
category TEXT,
FOREIGN KEY (patient_id)
REFERENCES patients(id),
FOREIGN KEY (encounter)
REFERENCES encounters(id));
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

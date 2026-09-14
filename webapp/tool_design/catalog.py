"""Build the editable entity/field catalog from agent-visible records."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from webapp.records.repository import PatientRepository


EXCLUDED_ENTITIES = {"metadata"}


def value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return "string"


def build_catalog(repository: PatientRepository) -> dict[str, Any]:
    field_types: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for patient_id in repository.patient_ids():
        patient = repository.load_agent_visible(patient_id)
        for entity, records in patient.items():
            if entity in EXCLUDED_ENTITIES or entity.startswith("_"):
                continue
            iterable = [records] if isinstance(records, dict) else records if isinstance(records, list) else []
            for record in iterable:
                if isinstance(record, dict):
                    for field, value in record.items():
                        field_types[entity][field].add(value_type(value))

    entities = {}
    for entity in sorted(field_types):
        fields = sorted(field_types[entity])
        entities[entity] = {
            "fields": {field: sorted(field_types[entity][field]) for field in fields},
            "key_fields": ["patient_id", *fields],
        }
    return {"virtual_key_fields": ["patient_id"], "entities": entities}


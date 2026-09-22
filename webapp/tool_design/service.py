"""Validate, compile, and execute declarative tools without generated code."""

from __future__ import annotations

import time
from typing import Any

from webapp.records.repository import PatientRepository
from webapp.tool_design.catalog import build_catalog
from webapp.tool_design.models import ToolDefinition, Toolset


class ToolConfigurationError(ValueError):
    pass


class ToolExecutionError(ValueError):
    pass

'''
confirm
Returned entities really exist in the cohort catalog.
Selected fields exist.
Key fields can be used across all returned entities.
The tool can be compiled and executed safely.
'''
def validate_toolset(toolset: Toolset, repository: PatientRepository) -> Toolset:
    catalog = build_catalog(repository)["entities"]
    errors = []
    for tool in toolset.tools:
        for entity, fields in tool.returns.items():
            if entity not in catalog:
                errors.append(f"{tool.name}: unknown entity '{entity}'")
                continue
            unknown = sorted(set(fields) - set(catalog[entity]["fields"]))
            if unknown:
                errors.append(f"{tool.name}: unknown fields for {entity}: {', '.join(unknown)}")
        if tool.key.field != "patient_id":
            incompatible = [
                entity for entity in tool.returns
                if entity in catalog and tool.key.field not in catalog[entity]["fields"]
            ]
            if incompatible:
                errors.append(
                    f"{tool.name}: key '{tool.key.field}' is not present in: {', '.join(incompatible)}"
                )
    if errors:
        raise ToolConfigurationError("; ".join(errors))
    return toolset


def argument_references(
    tool: ToolDefinition,
    assigned_patient_id: str,
    repository: PatientRepository,
) -> list[str]:
    canonical = repository.canonical_id(assigned_patient_id)
    if tool.key.field == "patient_id":
        repository.load_agent_visible(canonical)
        return [canonical]
    values = set()
    for patient_id in repository.patient_ids():
        patient = repository.load_agent_visible(patient_id)
        for entity in tool.returns:
            records = patient.get(entity, [])
            iterable = [records] if isinstance(records, dict) else records
            for record in iterable:
                value = record.get(tool.key.field)
                if value is not None and not isinstance(value, (dict, list)):
                    values.add(str(value))
    return sorted(values)

#Builds the dropdown values shown in the preview interface.
def argument_reference_options(
    tool: ToolDefinition,
    assigned_patient_id: str,
    repository: PatientRepository,
) -> list[dict[str, str]]:
    canonical = repository.canonical_id(assigned_patient_id)
    if tool.key.field == "patient_id":
        patient = repository.load_agent_visible(canonical)
        details = patient["patient"]
        return [{
            "value": canonical,
            "label": f'{canonical} — {details["firstName"]} {details["lastName"]}',
        }]

    labels_by_value: dict[str, set[str]] = {}
    for patient_id in repository.patient_ids():
        patient = repository.load_agent_visible(patient_id)
        for entity in tool.returns:
            source = patient.get(entity, [])
            records = [source] if isinstance(source, dict) else source
            for record in records:
                value = record.get(tool.key.field)
                if value is None or isinstance(value, (dict, list)):
                    continue
                text = str(value)
                labels_by_value.setdefault(text, set())
                description = record.get("description") or record.get("reasonDescription") or record.get("name")
                if description and str(description) != text:
                    labels_by_value[text].add(str(description))

    options = []
    for value in sorted(labels_by_value):
        descriptions = sorted(labels_by_value[value])
        label = f"{value} — {'; '.join(descriptions)}" if descriptions else value
        options.append({"value": value, "label": label})
    return options

'''
Calculates allowed argument values across the entire cohort when the toolset is finalized.
This prevents the available argument dropdown from revealing facts about the currently selected patient.
'''
def finalized_argument_vocabularies(
    toolset: Toolset,
    repository: PatientRepository,
) -> dict[str, dict[str, Any]]:
    """Snapshot cohort-wide non-patient arguments when a toolset is finalized."""
    fallback_patient_id = repository.patient_ids()[0]
    return {
        tool.id: {
            "key_field": tool.key.field,
            "scope": "assigned_patient" if tool.key.field == "patient_id" else "cohort",
            "options": (
                []
                if tool.key.field == "patient_id"
                else argument_reference_options(tool, fallback_patient_id, repository)
            ),
        }
        for tool in toolset.tools
    }

#convert tool into OpenAI function schema
def compile_openai_tool(
    tool: ToolDefinition,
    assigned_patient_id: str,
    repository: PatientRepository,
) -> dict[str, Any]:
    references = argument_references(tool, assigned_patient_id, repository)
    return {
        "type": "function",
        "name": tool.name,
        "description": tool.description,
        "parameters": {
            "type": "object",
            "properties": {
                tool.key.field: {
                    "type": "string",
                    "description": f"Exact {tool.key.field} to look up.",
                    "enum": references, #this field prevents the agent from requesting another patient before completing the task for current patient
                }
            },
            "required": [tool.key.field],
            "additionalProperties": False,
        },
        "strict": True,
    }


def _matches(record: dict[str, Any], field: str, argument: str) -> bool:
    value = record.get(field)
    return value is not None and str(value) == argument


def _evidence_ids(manifest: dict[str, Any]) -> set[tuple[str, str | None]]:
    keys = ("causal_records", "decision_input_records", "diagnostic_evidence_records")
    return {
        (record["entity"], record.get("id"))
        for key in keys
        for record in manifest.get(key, [])
        if record.get("id") is not None
    }

'''
Currently, each tool is simply indexing a JSON
So we receive the agent request, validate it, return the info, and log what information was accessed
'''
def execute_tool(
    tool: ToolDefinition,
    assigned_patient_id: str,
    argument: str,
    repository: PatientRepository,
    patient_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    canonical = repository.canonical_id(assigned_patient_id)
    if tool.key.field == "patient_id" and repository.canonical_id(argument) != canonical:
        raise ToolExecutionError("The supplied patient_id does not match the patient assigned to this run")
    if tool.key.field != "patient_id" and argument not in argument_references(tool, canonical, repository):
        raise ToolExecutionError("The supplied argument is not in the finalized cohort vocabulary")
    patient = patient_record if patient_record is not None else repository.load_agent_visible(canonical)
    manifest = repository.load_manifest(canonical)
    evidence_ids = _evidence_ids(manifest)
    output: dict[str, list[dict[str, Any]]] = {}
    returned_internal_ids: set[tuple[str, str | None]] = set()

    for entity, fields in tool.returns.items():
        source = patient.get(entity, [])
        records = [source] if isinstance(source, dict) else source
        if tool.key.field != "patient_id":
            records = [record for record in records if _matches(record, tool.key.field, argument)]
        output[entity] = [{field: record.get(field) for field in fields} for record in records]
        returned_internal_ids.update((entity, record.get("id")) for record in records)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    return {
        "output": output,
        "audit": {
            "tool_id": tool.id,
            "tool_name": tool.name,
            "key_field": tool.key.field,
            "argument": argument,
            "assigned_patient_id": canonical,
            "records_returned": sum(len(records) for records in output.values()),
            "relevant_records_returned": len(returned_internal_ids & evidence_ids),
            "returned_records": [
                {"entity": entity, "record_id": record_id}
                for entity, record_id in sorted(
                    item for item in returned_internal_ids if item[1] is not None
                )
            ],
            "elapsed_ms": elapsed_ms,
        },
    }

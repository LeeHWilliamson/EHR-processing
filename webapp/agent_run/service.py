from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from typing import Any, Awaitable, Callable

from openai import AsyncOpenAI

from webapp.noise.models import NoiseConfiguration
from webapp.records.repository import PatientRepository
from webapp.task_design.models import DiagnosticTask
from webapp.task_design.service import validate_task
from webapp.tool_design.models import ToolDefinition, Toolset
from webapp.tool_design.service import compile_openai_tool, execute_tool, validate_toolset


DEFAULT_MODEL = "gpt-5-mini"
MAX_RESPONSE_TURNS = 15
MAX_TOOL_CALLS = 30
RELEVANT_RECORD_KEYS = ("causal_records", "decision_input_records", "diagnostic_evidence_records")


class AgentRunError(RuntimeError):
    pass


ProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]


async def _emit(callback: ProgressCallback | None, event: dict[str, Any]) -> None:
    if callback is not None:
        await callback(event)


def _record_summary(entity: str, record: dict[str, Any]) -> dict[str, Any]:
    description = (
        record.get("description")
        or record.get("reasonDescription")
        or record.get("type")
        or record.get("bodysite")
        or "No description"
    )
    return {"entity": entity, "record_id": str(record["id"]), "description": str(description)}


def _patient_record_inventory(patient: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (entity, str(record["id"])): _record_summary(entity, record)
        for entity, records in patient.items()
        if isinstance(records, list) and entity != "metadata"
        for record in records
        if isinstance(record, dict) and record.get("id") is not None
    }


def _relevant_record_keys(manifest: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (record["entity"], str(record["id"]))
        for classification in RELEVANT_RECORD_KEYS
        for record in manifest.get(classification, [])
        if record.get("id") is not None
    }


def _result_lists(
    inventory: dict[tuple[str, str], dict[str, Any]],
    found_keys: set[tuple[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    found = [inventory[key] for key in sorted(inventory) if key in found_keys]
    missed = [inventory[key] for key in sorted(inventory) if key not in found_keys]
    return found, missed


def _diagnosis_schema() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": "diabetes_diagnosis",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "diagnosis": {"type": "string", "enum": ["present", "absent"]},
                "explanation": {"type": "string"},
            },
            "required": ["diagnosis", "explanation"],
            "additionalProperties": False,
        },
    }


def _usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


async def run_patient_agent(
    patient_id: str,
    toolset: Toolset,
    task: DiagnosticTask,
    noise: NoiseConfiguration,
    repository: PatientRepository,
    client: Any,
    model: str,
    event_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    noisy_patient, _ = repository.load_noisy_agent_visible(patient_id, noise)
    inventory = _patient_record_inventory(noisy_patient)
    tools_by_name = {tool.name: tool for tool in toolset.tools}
    tools = [compile_openai_tool(tool, patient_id, repository) for tool in toolset.tools]
    prompt = (
        f"{task.user_instructions}\n\nAssigned patient ID: {patient_id}\n"
        "Use the available tools to inspect the patient. Do not infer facts from argument availability."
    )
    response = await client.responses.create(
        model=model,
        instructions=task.system_instructions,
        input=prompt,
        tools=tools,
        tool_choice="auto",
        parallel_tool_calls=False,
        text={"format": _diagnosis_schema()},
        max_output_tokens=1000,
    )
    usage = defaultdict(int)
    tool_calls: list[dict[str, Any]] = []
    found_keys: set[tuple[str, str]] = set()

    for _ in range(MAX_RESPONSE_TURNS):
        for key, value in _usage(response).items():
            usage[key] += value
        calls = [item for item in response.output if item.type == "function_call"]
        if not calls:
            break
        if len(tool_calls) + len(calls) > MAX_TOOL_CALLS:
            raise AgentRunError(f"Agent exceeded the {MAX_TOOL_CALLS}-call safety limit")
        outputs = []
        for call in calls:
            tool = tools_by_name.get(call.name)
            try:
                if tool is None:
                    raise ValueError("Unknown tool")
                arguments = json.loads(call.arguments)
                argument = arguments[tool.key.field]
                result = execute_tool(tool, patient_id, str(argument), repository, patient_record=noisy_patient)
                for item in result["audit"]["returned_records"]:
                    found_keys.add((item["entity"], str(item["record_id"])))
                tool_calls.append({
                    "tool_name": tool.name,
                    "argument": str(argument),
                    "records_returned": result["audit"]["records_returned"],
                })
                await _emit(event_callback, {
                    "type": "tool_completed",
                    "patient_id": patient_id,
                    "tool_name": tool.name,
                    "records_returned": result["audit"]["records_returned"],
                    "tool_call_number": len(tool_calls),
                })
                output = result["output"]
            except Exception as error:
                tool_calls.append({"tool_name": call.name, "error": str(error)})
                await _emit(event_callback, {
                    "type": "tool_error",
                    "patient_id": patient_id,
                    "tool_name": call.name,
                    "message": str(error),
                    "tool_call_number": len(tool_calls),
                })
                output = {"error": str(error)}
            outputs.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": json.dumps(output),
            })
        response = await client.responses.create(
            model=model,
            instructions=task.system_instructions,
            input=outputs,
            previous_response_id=response.id,
            tools=tools,
            tool_choice="auto",
            parallel_tool_calls=False,
            text={"format": _diagnosis_schema()},
            max_output_tokens=1000,
        )
    else:
        raise AgentRunError(f"Agent exceeded the {MAX_RESPONSE_TURNS}-turn safety limit")

    if any(item.type == "function_call" for item in response.output):
        raise AgentRunError("Agent stopped before producing a diagnosis")
    try:
        diagnosis = json.loads(response.output_text)
    except (json.JSONDecodeError, TypeError) as error:
        raise AgentRunError("Agent returned an invalid diagnosis") from error
    manifest = repository.load_manifest(patient_id)
    expected = "present" if manifest.get("has_type_2_diabetes") else "absent"
    relevant_inventory = {
        key: record
        for key, record in inventory.items()
        if key in _relevant_record_keys(manifest)
    }
    found, missed = _result_lists(relevant_inventory, found_keys)
    return {
        "patient_id": patient_id,
        "diagnosis": diagnosis["diagnosis"],
        "expected_diagnosis": expected,
        "correct": diagnosis["diagnosis"] == expected,
        "explanation": diagnosis["explanation"],
        "records_found": len(found),
        "total_records": len(relevant_inventory),
        "total_entity_records_retrieved": len(found_keys & set(inventory)),
        "found_records": found,
        "missed_records": missed,
        "tool_calls": tool_calls,
        "usage": dict(usage),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
    }


async def run_cohort_agent(
    toolset: Toolset,
    task: DiagnosticTask,
    noise: NoiseConfiguration,
    repository: PatientRepository,
    client: Any | None = None,
    model: str | None = None,
    event_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    cohort_started = time.perf_counter()
    validated_tools = validate_toolset(toolset, repository)
    validated_task = validate_task(task, validated_tools)
    selected_model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    api_key = os.getenv("OPENAI_API_KEY")
    if client is None and not api_key:
        raise AgentRunError("OPENAI_API_KEY is not configured on the server")
    active_client = client or AsyncOpenAI(api_key=api_key)
    summaries = {item["patient_id"]: item for item in repository.summaries()}
    results = []
    patient_ids = repository.patient_ids()
    for patient_number, patient_id in enumerate(patient_ids, start=1):
        patient_started = time.perf_counter()
        summary = summaries[patient_id]
        patient_name = f'{summary["first_name"]} {summary["last_name"]}'
        await _emit(event_callback, {
            "type": "patient_started",
            "patient_id": patient_id,
            "patient_name": patient_name,
            "patient_number": patient_number,
            "patient_total": len(patient_ids),
        })
        try:
            result = await run_patient_agent(
                patient_id, validated_tools, validated_task, noise, repository, active_client, selected_model,
                event_callback,
            )
        except Exception as error:
            inventory = _patient_record_inventory(repository.load_noisy_agent_visible(patient_id, noise)[0])
            manifest = repository.load_manifest(patient_id)
            expected = "present" if manifest.get("has_type_2_diabetes") else "absent"
            relevant_inventory = {
                key: record
                for key, record in inventory.items()
                if key in _relevant_record_keys(manifest)
            }
            result = {
                "patient_id": patient_id,
                "correct": False,
                "error": str(error),
                "expected_diagnosis": expected,
                "records_found": 0,
                "total_records": len(relevant_inventory),
                "total_entity_records_retrieved": 0,
                "found_records": [],
                "missed_records": [relevant_inventory[key] for key in sorted(relevant_inventory)],
                "tool_calls": [],
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                "elapsed_ms": round((time.perf_counter() - patient_started) * 1000, 1),
            }
        result["patient_name"] = patient_name
        results.append(result)
        await _emit(event_callback, {
            "type": "patient_completed",
            "patient_number": patient_number,
            "patient_total": len(patient_ids),
            "result": result,
        })
    return {
        "model": selected_model,
        "patients": results,
        "summary": {
            "correct": sum(result["correct"] for result in results),
            "total": len(results),
            "total_tokens": sum(result["usage"]["total_tokens"] for result in results),
            "errors": sum("error" in result for result in results),
            "elapsed_ms": round((time.perf_counter() - cohort_started) * 1000, 1),
        },
    }

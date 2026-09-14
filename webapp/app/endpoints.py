"""FastAPI application for the Synth-EHR guided tutorial."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import asyncio
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, ValidationError

from webapp.records.repository import PatientNotFoundError, PatientRepository
from webapp.noise.models import NoiseConfiguration
from webapp.noise.service import noise_sources, summarize_noise_impact
from webapp.agent_run.models import AgentRunRequest
from webapp.agent_run.service import AgentRunError, run_cohort_agent
from webapp.task_design.defaults import default_task
from webapp.task_design.models import DiagnosticTask
from webapp.task_design.service import TaskConfigurationError, validate_task
from webapp.verification.service import verify_cohort
from webapp.tool_design.catalog import build_catalog
from webapp.tool_design.defaults import default_toolset
from webapp.tool_design.models import ToolExecutionRequest, ToolReferenceRequest, Toolset
from webapp.tool_design.service import (
    ToolConfigurationError,
    ToolExecutionError,
    argument_reference_options,
    compile_openai_tool,
    execute_tool,
    finalized_argument_vocabularies,
    validate_toolset,
)


WEBAPP_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = WEBAPP_DIR / "static"

app = FastAPI(title="Synth-EHR Guided Tutorial", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
repository = PatientRepository()
# A cohort run can make many paid API calls and holds the worker for a while.
# This process-level lock deliberately rejects overlapping runs rather than
# queueing them and surprising the user with a delayed, duplicate charge.
agent_run_lock = asyncio.Lock()


def _agent_run_busy_error() -> HTTPException:
    return HTTPException(
        status_code=409,
        detail="Another agent run is already in progress. Please wait for it to finish.",
    )


async def _acquire_agent_run_lock() -> None:
    if agent_run_lock.locked():
        raise _agent_run_busy_error()
    await agent_run_lock.acquire()


class CompileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    toolset: Toolset
    assigned_patient_id: str


class TaskValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: DiagnosticTask
    toolset: Toolset


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/patients")
async def get_patients() -> list[dict[str, Any]]:
    return repository.summaries()


@app.get("/patients", include_in_schema=False)
async def get_patients_legacy() -> list[dict[str, Any]]:
    """Compatibility alias for the first frontend prototype."""
    return await get_patients()


@app.get("/api/patients/{patient_id}/agent-view")
async def get_agent_view(patient_id: str) -> dict[str, Any]:
    try:
        return repository.load_agent_visible(patient_id)
    except PatientNotFoundError as error:
        raise HTTPException(status_code=404, detail="Patient not found") from error


@app.get("/api/patients/{patient_id}/original-view")
async def get_original_view(patient_id: str) -> dict[str, Any]:
    """Return the evaluator-only normalized fixture, including target leakage."""
    try:
        return repository.load_pristine(patient_id)
    except PatientNotFoundError as error:
        raise HTTPException(status_code=404, detail="Patient not found") from error


@app.get("/api/tool-design/catalog")
async def tool_catalog() -> dict[str, Any]:
    return build_catalog(repository)


@app.get("/api/tool-design/defaults")
async def default_tools() -> dict[str, Any]:
    return default_toolset().model_dump()


@app.get("/api/task-design/defaults")
async def task_defaults() -> dict[str, Any]:
    return default_task().model_dump()


@app.post("/api/task-design/validate")
async def validate_diagnostic_task(request: TaskValidationRequest) -> dict[str, Any]:
    try:
        validated_tools = validate_toolset(request.toolset, repository)
        validated_task = validate_task(request.task, validated_tools)
    except (ToolConfigurationError, TaskConfigurationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"valid": True, "task": validated_task.model_dump()}


@app.get("/api/noise/defaults")
async def noise_defaults() -> dict[str, Any]:
    return {
        "configuration": NoiseConfiguration().model_dump(),
        "sources": noise_sources(),
    }


@app.post("/api/noise/validate")
async def validate_noise(configuration: NoiseConfiguration) -> dict[str, Any]:
    records = [
        (patient_id, repository.load_agent_visible(patient_id))
        for patient_id in repository.patient_ids()
    ]
    return {
        "valid": True,
        "configuration": configuration.model_dump(),
        "sources": noise_sources() if configuration.enabled else [],
        "impact": summarize_noise_impact(records, configuration),
    }


@app.post("/api/verification/run")
async def run_verification(configuration: NoiseConfiguration) -> dict[str, Any]:
    return verify_cohort(configuration, repository)


@app.post("/api/agent/run")
async def run_agent_task(request: AgentRunRequest) -> dict[str, Any]:
    await _acquire_agent_run_lock()
    try:
        return await run_cohort_agent(request.toolset, request.task, request.noise, repository)
    except AgentRunError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (ToolConfigurationError, TaskConfigurationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        agent_run_lock.release()


@app.post("/api/agent/run-stream")
async def stream_agent_task(request: AgentRunRequest) -> StreamingResponse:
    await _acquire_agent_run_lock()

    async def events():
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async def publish(event: dict[str, Any]) -> None:
            await queue.put(event)

        async def worker() -> None:
            try:
                result = await run_cohort_agent(
                    request.toolset,
                    request.task,
                    request.noise,
                    repository,
                    event_callback=publish,
                )
                await queue.put({"type": "run_completed", "result": result})
            except Exception as error:
                await queue.put({"type": "run_error", "message": str(error)})

        task = asyncio.create_task(worker())
        try:
            while True:
                event = await queue.get()
                yield json.dumps(event, separators=(",", ":")) + "\n"
                if event["type"] in {"run_completed", "run_error"}:
                    break
        finally:
            if not task.done():
                task.cancel()
            agent_run_lock.release()

    return StreamingResponse(events(), media_type="application/x-ndjson")


def _user_fixable_toolset_error(payload: dict[str, Any]) -> str | None:
    tools = payload.get("tools")
    if not isinstance(tools, list):
        return None
    if not tools:
        return "Add at least one tool before finalizing the toolset."
    if len(tools) > 15:
        return "The toolset can contain no more than 15 tools. Remove at least one tool."
    if any(not isinstance(tool, dict) for tool in tools):
        return None
    raw_names = [tool.get("name") for tool in tools]
    if any(not isinstance(name, str) for name in raw_names):
        return None
    names = [name.strip() for name in raw_names]
    if any(not name for name in names):
        return "Every tool needs a name."
    if len(names) != len(set(names)):
        return "Every tool name must be unique. Rename the duplicated tool."
    descriptions = [tool.get("description") for tool in tools]
    if all(isinstance(description, str) for description in descriptions) and any(
        not description.strip() for description in descriptions
    ):
        return "Every tool needs a description."
    for tool in tools:
        if not isinstance(tool, dict):
            return None
        returns = tool.get("returns")
        if not isinstance(returns, dict) or not returns:
            return "Every tool must return at least one entity with selected fields."
        if any(not isinstance(fields, list) or not fields for fields in returns.values()):
            return "Select at least one return field for every entity in each tool."
    return None


@app.post("/api/tool-design/validate")
async def validate_tools(payload: dict[str, Any]) -> dict[str, Any]:
    fixable_error = _user_fixable_toolset_error(payload)
    if fixable_error:
        raise HTTPException(status_code=422, detail=fixable_error)
    try:
        toolset = Toolset.model_validate(payload)
        validated = validate_toolset(toolset, repository)
    except (ValidationError, ToolConfigurationError) as error:
        raise HTTPException(
            status_code=422,
            detail="The toolset could not be finalized. Reset the defaults or try editing the affected tool.",
        ) from error
    return {
        "valid": True,
        "toolset": validated.model_dump(),
        "argument_vocabularies": finalized_argument_vocabularies(validated, repository),
    }


@app.post("/api/tool-design/compile")
async def compile_tools(request: CompileRequest) -> dict[str, Any]:
    try:
        toolset = validate_toolset(request.toolset, repository)
        tools = [
            compile_openai_tool(tool, request.assigned_patient_id, repository)
            for tool in toolset.tools
        ]
    except (ToolConfigurationError, PatientNotFoundError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"tools": tools}


@app.post("/api/tool-design/preview")
async def preview_tool(request: ToolExecutionRequest) -> dict[str, Any]:
    try:
        validate_toolset(Toolset(tools=[request.tool]), repository)
        return execute_tool(
            request.tool,
            request.assigned_patient_id,
            request.argument,
            repository,
        )
    except PatientNotFoundError as error:
        raise HTTPException(status_code=404, detail="Patient not found") from error
    except (ToolConfigurationError, ToolExecutionError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/tool-design/references")
async def tool_references(request: ToolReferenceRequest) -> dict[str, Any]:
    try:
        validate_toolset(Toolset(tools=[request.tool]), repository)
        options = argument_reference_options(request.tool, request.assigned_patient_id, repository)
    except PatientNotFoundError as error:
        raise HTTPException(status_code=404, detail="Patient not found") from error
    except ToolConfigurationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"key_field": request.tool.key.field, "options": options}

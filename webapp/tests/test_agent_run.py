import asyncio
import json
from types import SimpleNamespace

import httpx

import webapp.app.endpoints as endpoint_module
from webapp.agent_run.service import run_patient_agent
from webapp.app.endpoints import app
from webapp.noise.models import NoiseConfiguration
from webapp.records.repository import PatientRepository
from webapp.task_design.defaults import default_task
from webapp.tool_design.defaults import default_toolset
from webapp.tool_design.models import Toolset


repository = PatientRepository()


class FakeResponses:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    async def create(self, **kwargs):
        self.requests.append(kwargs)
        return next(self.responses)


def fake_response(response_id, output, output_text="", tokens=10):
    return SimpleNamespace(
        id=response_id,
        output=output,
        output_text=output_text,
        usage=SimpleNamespace(input_tokens=tokens - 2, output_tokens=2, total_tokens=tokens),
    )


def test_patient_agent_executes_tools_scores_diagnosis_and_tracks_records() -> None:
    patient_id = "pat_3faad1f1-8c4f-806f-4fb0-8587b4fede7a"
    condition_tool = next(tool for tool in default_toolset().tools if tool.id == "get_conditions")
    call = SimpleNamespace(
        type="function_call",
        name=condition_tool.name,
        arguments=json.dumps({"patient_id": patient_id}),
        call_id="call_1",
    )
    first = fake_response("resp_1", [call])
    second = fake_response(
        "resp_2",
        [SimpleNamespace(type="message")],
        json.dumps({"diagnosis": "present", "explanation": "Clinical evidence supports diabetes."}),
    )
    client = SimpleNamespace(responses=FakeResponses([first, second]))

    events = []

    async def collect(event):
        events.append(event)

    result = asyncio.run(
        run_patient_agent(
            patient_id=patient_id,
            toolset=Toolset(tools=[condition_tool]),
            task=default_task(),
            noise=NoiseConfiguration(enabled=True),
            repository=repository,
            client=client,
            model="test-model",
            event_callback=collect,
        )
    )

    assert result["correct"] is True
    assert result["diagnosis"] == "present"
    assert result["records_found"] > 0
    assert result["records_found"] < result["total_records"]
    assert len(result["found_records"]) == result["records_found"]
    assert len(result["missed_records"]) == result["total_records"] - result["records_found"]
    relevant_keys = {
        (record["entity"], str(record["id"]))
        for key in ("causal_records", "decision_input_records", "diagnostic_evidence_records")
        for record in repository.load_manifest(patient_id).get(key, [])
        if record.get("id") is not None
    }
    assert {
        (record["entity"], record["record_id"])
        for record in result["found_records"] + result["missed_records"]
    } <= relevant_keys
    assert result["usage"]["total_tokens"] == 20
    assert result["elapsed_ms"] >= 0
    assert client.responses.requests[1]["previous_response_id"] == "resp_1"
    assert events == [{
        "type": "tool_completed",
        "patient_id": patient_id,
        "tool_name": condition_tool.name,
        "records_returned": result["tool_calls"][0]["records_returned"],
        "tool_call_number": 1,
    }]


def test_agent_stream_endpoint_emits_progress_and_final_result(monkeypatch) -> None:
    expected_result = {
        "model": "test-model",
        "patients": [],
        "summary": {"correct": 0, "total": 0, "total_tokens": 0, "errors": 0},
    }

    async def fake_run(toolset, task, noise, repository, event_callback=None, **kwargs):
        await event_callback({
            "type": "patient_started",
            "patient_id": "pat_test",
            "patient_name": "Test Patient",
            "patient_number": 1,
            "patient_total": 1,
        })
        return expected_result

    monkeypatch.setattr(endpoint_module, "run_cohort_agent", fake_run)

    async def request_stream() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/agent/run-stream",
                json={
                    "toolset": default_toolset().model_dump(),
                    "task": default_task().model_dump(),
                    "noise": {"enabled": True},
                },
            )
        assert response.status_code == 200
        events = [json.loads(line) for line in response.text.splitlines()]
        assert events[0]["type"] == "patient_started"
        assert events[-1] == {"type": "run_completed", "result": expected_result}

    asyncio.run(request_stream())


def test_agent_endpoint_rejects_overlapping_run() -> None:
    async def request_while_busy() -> None:
        await endpoint_module.agent_run_lock.acquire()
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/agent/run-stream",
                    json={
                        "toolset": default_toolset().model_dump(),
                        "task": default_task().model_dump(),
                        "noise": {"enabled": True},
                    },
                )
        finally:
            endpoint_module.agent_run_lock.release()

        assert response.status_code == 409
        assert response.json()["detail"].startswith("Another agent run")

    asyncio.run(request_while_busy())

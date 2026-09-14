import asyncio
import httpx
import pytest

from webapp.app.endpoints import _user_fixable_toolset_error, app
from webapp.records.repository import PatientRepository, REDACTED
from webapp.task_design.defaults import default_task
from webapp.task_design.models import WorkflowStep
from webapp.task_design.service import TaskConfigurationError, validate_task
from webapp.tool_design.defaults import default_toolset
from webapp.tool_design.models import ToolDefinition, ToolKey, Toolset
from webapp.tool_design.service import (
    ToolConfigurationError,
    ToolExecutionError,
    argument_reference_options,
    compile_openai_tool,
    execute_tool,
    validate_toolset,
)


repository = PatientRepository()


def positive_patient_id() -> str:
    for patient_id in repository.patient_ids():
        if repository.load_manifest(patient_id).get("has_type_2_diabetes"):
            return patient_id
    raise AssertionError("Fixture cohort has no positive patient")


def test_default_toolset_is_valid_and_uses_patient_id() -> None:
    toolset = validate_toolset(default_toolset(), repository)
    assert len(toolset.tools) == 10
    assert {tool.key.field for tool in toolset.tools} == {"patient_id"}


def test_default_task_is_binary_and_valid() -> None:
    task = default_task()
    assert task.allowed_outcomes == ("present", "absent")
    assert task.task_type == "diagnose_condition"
    assert task.condition == "diabetes"
    assert validate_task(task, default_toolset()) == task


def test_task_workflow_must_reference_current_toolset() -> None:
    task = default_task().model_copy(
        update={"ideal_workflow": [WorkflowStep(tool_id="missing_tool")]}
    )
    with pytest.raises(TaskConfigurationError):
        validate_task(task, default_toolset())


def test_patient_summary_counts_only_records_without_end_dates() -> None:
    summary = repository.summaries()[0]
    patient = repository.load_pristine(summary["patient_id"])
    for entity in ("conditions", "medications", "careplans", "allergies"):
        expected = sum(1 for record in patient[entity] if record.get("endDate") is None)
        assert summary["counts"][entity] == expected


def test_intentional_diabetes_cohort_is_explicitly_identified() -> None:
    keep_patients = {
        summary["patient_id"]
        for summary in repository.summaries()
        if summary["cohort_group"] == "diabetes_keep"
    }
    assert keep_patients == {
        "pat_3faad1f1-8c4f-806f-4fb0-8587b4fede7a",
        "pat_d51799f2-25b2-4bab-11b5-d618b6e4e782",
        "pat_59c02207-551f-6eea-de28-5a6ead6997f5",
    }


def test_patient_id_tool_is_scoped_to_assigned_patient() -> None:
    patient_ids = repository.patient_ids()
    tool = default_toolset().tools[0]
    with pytest.raises(ToolExecutionError):
        execute_tool(tool, patient_ids[0], patient_ids[1], repository)


def test_agent_view_removes_exact_diagnosis_and_redacts_leaking_fields() -> None:
    patient_id = positive_patient_id()
    visible = repository.load_agent_visible(patient_id)
    assert all(str(condition.get("code")) != "44054006" for condition in visible["conditions"])
    assert any(
        REDACTED in (record.get("reason"), record.get("reasonDescription"))
        for entity in ("encounters", "medications", "procedures", "careplans")
        for record in visible.get(entity, [])
    )


def test_executor_returns_only_selected_fields_and_audit_counts() -> None:
    patient_id = repository.patient_ids()[0]
    tool = ToolDefinition(
        id="observations_preview",
        name="observations_preview",
        description="Preview observation descriptions.",
        key=ToolKey(field="patient_id"),
        returns={"observations": ["description"]},
    )
    result = execute_tool(tool, patient_id, patient_id, repository)
    assert result["output"]["observations"]
    assert all(set(record) == {"description"} for record in result["output"]["observations"])
    assert result["audit"]["records_returned"] == len(result["output"]["observations"])


def test_non_patient_key_filters_exactly() -> None:
    patient_id = repository.patient_ids()[0]
    patient = repository.load_agent_visible(patient_id)
    description = patient["observations"][0]["description"]
    tool = ToolDefinition(
        id="observation_by_description",
        name="observation_by_description",
        description="Returns matching observations.",
        key=ToolKey(field="description"),
        returns={"observations": ["description", "value"]},
    )
    result = execute_tool(tool, patient_id, description, repository)
    assert result["output"]["observations"]
    assert {record["description"] for record in result["output"]["observations"]} == {description}


def test_non_patient_argument_outside_cohort_vocabulary_is_rejected() -> None:
    patient_id = repository.patient_ids()[0]
    tool = ToolDefinition(
        id="observation_by_description",
        name="observation_by_description",
        description="Returns matching observations.",
        key=ToolKey(field="description"),
        returns={"observations": ["description"]},
    )
    with pytest.raises(ToolExecutionError, match="cohort vocabulary"):
        execute_tool(tool, patient_id, "value-that-does-not-exist-anywhere", repository)


def test_unknown_return_field_is_rejected() -> None:
    tool = ToolDefinition(
        id="bad_tool",
        name="bad_tool",
        description="Invalid field test.",
        returns={"observations": ["not_a_real_field"]},
    )
    with pytest.raises(ToolConfigurationError):
        validate_toolset(Toolset(tools=[tool]), repository)


def test_fixable_validation_messages_are_specific() -> None:
    assert _user_fixable_toolset_error({"tools": []}) == (
        "Add at least one tool before finalizing the toolset."
    )
    duplicate = default_toolset().model_dump()
    duplicate["tools"][1]["name"] = duplicate["tools"][0]["name"]
    assert "unique" in _user_fixable_toolset_error(duplicate)
    no_fields = default_toolset().model_dump()
    first_entity = next(iter(no_fields["tools"][0]["returns"]))
    no_fields["tools"][0]["returns"][first_entity] = []
    assert "return field" in _user_fixable_toolset_error(no_fields)


def test_openai_schema_has_one_strict_argument() -> None:
    patient_id = repository.patient_ids()[0]
    tool = default_toolset().tools[0]
    schema = compile_openai_tool(tool, patient_id, repository)
    assert schema["strict"] is True
    assert schema["parameters"]["properties"]["patient_id"]["enum"] == [patient_id]
    assert schema["parameters"]["additionalProperties"] is False


def test_code_reference_options_have_human_readable_labels() -> None:
    patient_id = positive_patient_id()
    tool = ToolDefinition(
        id="observation_by_code",
        name="observation_by_code",
        description="Returns observations matching a code.",
        key=ToolKey(field="code"),
        returns={"observations": ["description", "value"]},
    )
    options = argument_reference_options(tool, patient_id, repository)
    assert options
    assert all(option["value"] in option["label"] for option in options)
    assert any("Hemoglobin A1c" in option["label"] for option in options)


def test_non_patient_argument_vocabulary_is_cohort_wide_and_stable() -> None:
    patient_ids = repository.patient_ids()
    tool = ToolDefinition(
        id="device_by_description",
        name="device_by_description",
        description="Returns devices matching a description.",
        key=ToolKey(field="description"),
        returns={"devices": ["description", "startDate"]},
    )
    first_options = argument_reference_options(tool, patient_ids[0], repository)
    last_options = argument_reference_options(tool, patient_ids[-1], repository)
    assert first_options
    assert first_options == last_options

    # At least one cohort-valid query should legitimately return no records for
    # a patient, rather than disappearing from that patient's vocabulary.
    empty_result_found = False
    for option in first_options:
        for patient_id in patient_ids:
            result = execute_tool(tool, patient_id, option["value"], repository)
            if result["audit"]["records_returned"] == 0:
                empty_result_found = True
                break
        if empty_result_found:
            break
    assert empty_result_found


def test_compiled_non_patient_enum_is_identical_across_patients() -> None:
    patient_ids = repository.patient_ids()
    tool = ToolDefinition(
        id="observation_by_code",
        name="observation_by_code",
        description="Returns observations matching a code.",
        key=ToolKey(field="code"),
        returns={"observations": ["description", "value"]},
    )
    first_enum = compile_openai_tool(tool, patient_ids[0], repository)["parameters"]["properties"]["code"]["enum"]
    last_enum = compile_openai_tool(tool, patient_ids[-1], repository)["parameters"]["properties"]["code"]["enum"]
    assert first_enum
    assert first_enum == last_enum


def test_tool_design_api_round_trip() -> None:
    async def round_trip() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            defaults = await client.get("/api/tool-design/defaults")
            assert defaults.status_code == 200
            patient_id = (await client.get("/api/patients")).json()[0]["patient_id"]
            tool = defaults.json()["tools"][0]
            preview = await client.post(
                "/api/tool-design/preview",
                json={"tool": tool, "assigned_patient_id": patient_id, "argument": patient_id},
            )
            assert preview.status_code == 200
            assert preview.json()["audit"]["assigned_patient_id"] == patient_id
            references = await client.post(
                "/api/tool-design/references",
                json={"tool": tool, "assigned_patient_id": patient_id},
            )
            assert references.status_code == 200
            assert references.json()["options"][0]["value"] == patient_id

    asyncio.run(round_trip())


def test_task_design_api_round_trip() -> None:
    async def round_trip() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            task = (await client.get("/api/task-design/defaults")).json()
            tools = (await client.get("/api/tool-design/defaults")).json()
            task["ideal_workflow"] = [
                {"tool_id": tools["tools"][0]["id"]}
            ]
            response = await client.post(
                "/api/task-design/validate",
                json={"task": task, "toolset": tools},
            )
            assert response.status_code == 200
            assert response.json()["task"]["allowed_outcomes"] == ["present", "absent"]

    asyncio.run(round_trip())


def test_patient_reader_exposes_distinct_original_and_agent_views() -> None:
    async def read_views() -> None:
        patient_id = positive_patient_id()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            original = await client.get(f"/api/patients/{patient_id}/original-view")
            agent = await client.get(f"/api/patients/{patient_id}/agent-view")
            assert original.status_code == 200
            assert agent.status_code == 200
            assert any(str(item.get("code")) == "44054006" for item in original.json()["conditions"])
            assert all(str(item.get("code")) != "44054006" for item in agent.json()["conditions"])

    asyncio.run(read_views())

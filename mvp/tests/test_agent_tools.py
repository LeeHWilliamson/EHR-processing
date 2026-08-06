from mvp.agents.agent_tools import CLAUDE_TOOLS, OPENAI_TOOLS, TOOL_MAP


EXPECTED_TOOL_NAMES = {
    "get_patient",
    "get_encounters",
    "get_medications",
    "get_observations",
    "get_allergies",
    "get_conditions",
    "get_immunizations",
    "get_devices",
    "get_procedures",
    "get_careplans",
}


def test_all_tool_collections_have_the_same_tools():
    assert set(TOOL_MAP) == EXPECTED_TOOL_NAMES
    assert {tool["name"] for tool in OPENAI_TOOLS} == EXPECTED_TOOL_NAMES
    assert {tool["name"] for tool in CLAUDE_TOOLS} == EXPECTED_TOOL_NAMES


def test_provider_tool_schemas_require_patient_id():
    for tool in OPENAI_TOOLS:
        assert tool["parameters"]["required"] == ["patient_id"]

    for tool in CLAUDE_TOOLS:
        assert tool["input_schema"]["required"] == ["patient_id"]

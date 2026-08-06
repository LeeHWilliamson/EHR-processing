"""Shared tool definitions for the supported AI providers."""

from ..api import api_client


_TOOL_SPECS = (
    ("get_patient", "Retrieve demographic information for a patient.", api_client.get_patient),
    ("get_encounters", "Retrieve all encounters associated with a patient.", api_client.get_encounters),
    ("get_medications", "Retrieve all medications associated with a patient.", api_client.get_medications),
    ("get_observations", "Retrieve all observations associated with a patient.", api_client.get_observations),
    ("get_allergies", "Retrieve all allergies associated with a patient.", api_client.get_allergies),
    ("get_conditions", "Retrieve all conditions associated with a patient.", api_client.get_conditions),
    ("get_immunizations", "Retrieve all immunizations associated with a patient.", api_client.get_immunizations),
    ("get_devices", "Retrieve all devices associated with a patient.", api_client.get_devices),
    ("get_procedures", "Retrieve all procedures associated with a patient.", api_client.get_procedures),
    ("get_careplans", "Retrieve all care plans associated with a patient.", api_client.get_careplans),
)


def _patient_id_schema():
    return {
        "type": "object",
        "properties": {
            "patient_id": {
                "type": "string",
                "description": "A patient's unique identifier.",
            }
        },
        "required": ["patient_id"],
    }


TOOL_MAP = {name: function for name, _, function in _TOOL_SPECS}

OPENAI_TOOLS = [
    {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": _patient_id_schema(),
    }
    for name, description, _ in _TOOL_SPECS
]

CLAUDE_TOOLS = [
    {
        "name": name,
        "description": description,
        "input_schema": _patient_id_schema(),
    }
    for name, description, _ in _TOOL_SPECS
]

"""Default patient-ID toolset for the guided tutorial."""

from __future__ import annotations

from webapp.tool_design.models import ToolDefinition, ToolKey, Toolset


DEFAULT_FIELDS = {
    "allergies": ["description", "reaction", "severity", "startDate", "endDate"],
    "careplans": ["description", "reasonDescription", "startDate", "endDate"],
    "conditions": ["description", "startDate", "endDate"],
    "devices": ["description", "startDate"],
    "encounters": ["type", "description", "reason", "startDate", "endDate"],
    "imaging_studies": ["date", "bodysite", "modality"],
    "immunizations": ["description", "date"],
    "medications": ["description", "reason", "startDate", "endDate"],
    "observations": ["description", "value", "units", "date"],
    "procedures": ["description", "reason", "date"],
}


def default_toolset() -> Toolset:
    tools = []
    for entity, fields in DEFAULT_FIELDS.items():
        label = entity.replace("_", " ")
        tools.append(
            ToolDefinition(
                id=f"get_{entity}",
                name=f"get_patient_{entity}",
                description=f"Returns selected {label} records for the assigned patient.",
                key=ToolKey(field="patient_id", operator="equals"),
                returns={entity: fields},
            )
        )
    return Toolset(tools=tools)


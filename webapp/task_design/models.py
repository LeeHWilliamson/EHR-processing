from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkflowStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_id: str = Field(min_length=1, max_length=64)


class DiagnosticTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    task_type: Literal["diagnose_condition"] = "diagnose_condition"
    condition: Literal["diabetes"] = "diabetes"
    ideal_workflow: list[WorkflowStep] = Field(default_factory=list, max_length=20)
    system_instructions: str = Field(min_length=1, max_length=2000)
    user_instructions: str = Field(min_length=1, max_length=2000)
    allowed_outcomes: tuple[Literal["present"], Literal["absent"]] = ("present", "absent")

    @field_validator("name", "description", "system_instructions", "user_instructions")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

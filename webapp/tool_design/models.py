from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ToolKey(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str = "patient_id"
    operator: Literal["equals"] = "equals"


class ToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    description: str = Field(min_length=1, max_length=500)
    key: ToolKey = Field(default_factory=ToolKey)
    returns: dict[str, list[str]]

    @field_validator("id", "name", "description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def require_return_fields(self) -> "ToolDefinition":
        if not self.returns:
            raise ValueError("A tool must return at least one entity")
        if any(not fields for fields in self.returns.values()):
            raise ValueError("Every returned entity must include at least one field")
        return self


class Toolset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tools: list[ToolDefinition] = Field(min_length=1, max_length=15)

    @model_validator(mode="after")
    def unique_identifiers(self) -> "Toolset":
        ids = [tool.id for tool in self.tools]
        names = [tool.name for tool in self.tools]
        if len(ids) != len(set(ids)):
            raise ValueError("Tool IDs must be unique")
        if len(names) != len(set(names)):
            raise ValueError("Tool names must be unique")
        return self


class ToolExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: ToolDefinition
    assigned_patient_id: str
    argument: str


class ToolReferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: ToolDefinition
    assigned_patient_id: str

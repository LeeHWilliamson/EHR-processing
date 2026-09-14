from pydantic import BaseModel, ConfigDict

from webapp.noise.models import NoiseConfiguration
from webapp.task_design.models import DiagnosticTask
from webapp.tool_design.models import Toolset


class AgentRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    toolset: Toolset
    task: DiagnosticTask
    noise: NoiseConfiguration

from webapp.task_design.models import DiagnosticTask
from webapp.tool_design.models import Toolset


class TaskConfigurationError(ValueError):
    pass

#ensure the tools included in task actually exist
def validate_task(task: DiagnosticTask, toolset: Toolset) -> DiagnosticTask:
    tools_by_id = {tool.id: tool for tool in toolset.tools}
    for step_number, step in enumerate(task.ideal_workflow, start=1):
        tool = tools_by_id.get(step.tool_id)
        if tool is None:
            raise TaskConfigurationError(
                f"Workflow step {step_number} references a tool that is no longer available."
            )
    return task

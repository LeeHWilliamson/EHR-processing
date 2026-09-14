from webapp.task_design.models import DiagnosticTask


def default_task() -> DiagnosticTask:
    return DiagnosticTask(
        name="Diagnose Type II Diabetes",
        description="Determine whether the assigned patient's clinical record supports a diagnosis of Type II diabetes.",
        system_instructions=(
            "You are a clinical reasoning agent. Use the available patient tools to review the record, "
            "then classify Type II diabetes as present or absent. Base your conclusion only on retrieved evidence."
        ),
        user_instructions=(
            "Evaluate the assigned patient for Type II diabetes. Return exactly one diagnosis outcome: "
            "present or absent, followed by a concise explanation of the evidence you used."
        ),
    )

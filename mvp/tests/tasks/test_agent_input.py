'''
In this file, we test that agents are getting properly formatted input
'''
from mvp.agents.openai_agent import parse_task as parse_openai_task
from mvp.agents.claude_agent import parse_task as parse_claude_task
import json
from pathlib import Path


def load_test_task():
    test_task_path = Path(__file__).parent / "test_task.json"
    with open(test_task_path, "r") as task_file:
        task_dict = json.load(task_file)
    return task_dict["test_task"]

def test_openai_gets_correct_input():
    task_dict = load_test_task()
    processed_prompt = parse_openai_task(task_dict["prompt"], "TEST_ID_IGNORE")

def test_anthropic_gets_correct_input():
    task_dict = load_test_task()
    original_prompt = json.loads(json.dumps(task_dict["prompt"]))

    system, messages = parse_claude_task(task_dict["prompt"], "TEST_ID_IGNORE")

    assert system == (
        "This is the first system prompt and the first prompt overall.\n\n"
        "this is the second system prompt and the 4th and final prompt overall. "
        "There should be 2 system prompts and 2 user prompts"
    )
    assert messages == [
        {
            "role": "user",
            "content": (
                "This is the first user prompt and the second prompt overall."
                "\n\nPatient ID: TEST_ID_IGNORE"
            ),
        },
        {
            "role": "user",
            "content": "This is the second user prompt and the third prompt overall",
        },
    ]
    assert task_dict["prompt"] == original_prompt

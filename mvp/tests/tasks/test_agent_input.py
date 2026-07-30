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

def test_openai_gets_correct_input():
    task_dict = load_test_task()
    processed_prompt = parse_openai_task(task_dict["prompt"], "TEST_ID_IGNORE")

def test_anthropic_gets_correct_input():
    task_dict = load_test_task()
    processed_prompt = parse_claude_task(task_dict["prompt"], "TEST_ID_IGNORE")
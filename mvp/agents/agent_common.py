'''
This module will serve as the orchestrator for the agents, it will handle calling agents, intializing task reports, 
processing agent output, exposing tools, and possibly more.
'''
from .. import api_client
from .claude_agent import run_workflow as run_claude_agent
from .openai_agent import run_workflow as run_brobot_agent
import json
from datetime import datetime, timezone
from uuid import uuid4
import copy

AGENTS = {
    "open_ai" : run_brobot_agent,
    "claude" : run_claude_agent
}

def initialize_agent_report(task = "list_current_meds", agent = "agent_brobot", patient_id = None, schema: str = None):
    now = datetime.now(timezone.utc)
    AGENT_REPORT_SCHEMA = {
        "run_id": (
            f"{task}-" 
            f"{now:%Y%m%dT%H%M%S.%fZ}-" 
            f"{uuid4().hex[:4]}"
            ),
        "task": task,
        "schema": schema,
        "agent": agent,
        "provider" : "OpenAI",
        "model": "gpt-5",
        "patient_id": patient_id,
        "datetime": now.isoformat(),
        "tools_workflow": [],
        "workflow_metrics": {},
        "api_calls_made": 0,
        "total_tokens_used": 0,
        "total_rows_retrieved": 0,
        "raw_response": None,
        "patient_gt": None, 
        "output_metrics": {}
    }

    analytics_report = copy.deepcopy(AGENT_REPORT_SCHEMA)
    return analytics_report

def collect_agent_analytics(response):
    pass

def run_agent(task, curr_agent, patient_id, schema):
    api_client.set_schema(schema)
    #primitive approach for loading info specific to current task
    #all tasks are stored in a json, load the entire dict with key = current_task
    try:
        with open("mvp/tasks.json", "r") as file:
            tasks = json.load(file)
            current_task = tasks[task].copy()
    except:
        return RuntimeError
    
    analytics = initialize_agent_report(task = task, agent = curr_agent, patient_id = patient_id, schema = schema)
    #agent calls return analytics dict and raw response text
    return AGENTS[curr_agent](patient_id, current_task, analytics)

if __name__ == "__main__":
    analytics = run_agent("medication_retrieval_v1", "open_ai", "pat_f0ebb769-b341-2c5c-04dd-f4400ac8af26", "normalized_v1")
    
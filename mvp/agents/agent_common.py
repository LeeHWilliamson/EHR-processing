'''
This module will serve as the orchestrator for the agents, it will handle calling agents, intializing task reports, 
processing agent output, exposing tools, and possibly more.
'''
from .. import api_client
import json
from datetime import datetime, timezone
from uuid import uuid4
import copy


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

if __name__ == "__main__":
    pass
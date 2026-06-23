'''
This script compares the workflow followed by the agent to the ideal workflow lined out in the tasks's JSON
input : dictionary output by agent workflow
output : bool representing whether agent sequence exactly matched ideal sequence, list of ommitted steps, list of added steps
'''

import json
from pathlib import Path
def analyze_workflow(agent_analytics_dict):
    current_task = agent_analytics_dict["task"]
    workflow_sequence_match = False
    ommitted_steps = set()
    added_steps = set()
    with open("mvp/tasks.json", "r") as file:
        tasks_dict = json.load(file)
    #we definitely want to know if the exact order and tools used matched between agent output and ideal output
    #for that we need to compare the actual lists
    if tasks_dict[current_task]["ideal_workflow"] == agent_analytics_dict["tools_workflow"]:
        workflow_sequence_match = True
    
    #for MVP, just use simple set operations for other workflow metrics
    expected_tools = set(tasks_dict[current_task]["ideal_workflow"])
    actual_tools = set(agent_analytics_dict["tools_workflow"])
    
    #& == intersection I'm guessing
    correct_steps = expected_tools & actual_tools 
    added_steps = actual_tools - expected_tools
    ommitted_steps = expected_tools - actual_tools

    precision = len(correct_steps)/len(actual_tools) if actual_tools else 0
    recall = len(correct_steps)/len(expected_tools) if expected_tools else 0

    return {
        "workflow_sequence_match" : workflow_sequence_match,
        "workflow_precision" : precision,
        "workflow_recall" : recall,
        "added_steps" : list(added_steps),
        "ommitted_steps" : list(ommitted_steps)
    }
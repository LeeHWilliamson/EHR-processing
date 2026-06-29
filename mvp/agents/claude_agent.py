'''
We are going to set our AI agent to the task of assembling patient records by using the OpenAI API
This script will
- Define wrappers for accessing our API endpoints (these wrappers are often called 'tools' for the agent)
- Call our agent with those tool definitions
- Receive tool call requests from the agent, and log these requests
- Execute the corresponding API endpoint
- Send result to our agent
- Receive final answer from the agent

Our task for the agent will be to return all medications that a patient is currently taking in structured JSON format
'''
# import api_client
import json
from anthropic import Anthropic
import os
import copy
from datetime import datetime, timezone
from uuid import uuid4
from dotenv import load_dotenv #lets use utilize a .env file for dependency injection (in this case, our OpenAI API key)

load_dotenv()

client = Anthropic(
    api_key=os.getenv("ANTHROPIC_KEY")
)

'''
EXAMPLE MESSAGE
'''
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello, world"}],
)
print(message.content)

with open("claude_output.txt", "w") as file:
        file.write(message.model_dump_json(indent=2))

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

'''
~~~~~~TOOLS~~~~~~~~~~~
Currently OpenAI format, look up required format for claude
'''
TOOLS = [
    {
        "type": "function",
        "name": "get_patient",
        "description": "Retrieve demographic information for a patient.",
        "parameters": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "A patient's unique identifier."
                }
            },
            "required": ["patient_id"]
        }
        
    },
    {
        "type": "function",
        "name": "get_medications",
        "description": "Retrieve all medication information associated with a single patient.",
        "parameters": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "A patient's unique identifier."
                }
            },
            "required": ["patient_id"]
        }
    }
]

'''
TOOL MAP
Currently OpenAI format, adapt for claude
'''
TOOL_MAP = {
    "get_patient": api_client.get_patient,
    "get_medications": api_client.get_medications,
}

'''
RUNNING THE AGENT
Currently just copy-paste from openAI script

Input args will likely be exactly the same (this function will likely end up getting move to agent_common), but will need to be preprocessed
into acceptable format

we will use client.messages.create() for Anthropic, model and tools parameter will likely be the same. input + previous_response_id will be encompassed
in the messages field, which we will need to manage to contain the entire conversation history for the current session.

Will likely need to add input to .system field as we cannot send system instructions via input
'''
def run_agent(input_items, patient = None, previous_response_id=None):
    #we assemble the full user-side prompt by simply appending the relevant patient ID
    if "content" in input_items[-1]:
        input_items[-1]["content"] = input_items[-1]["content"] + patient
    #we pass name of model we want, a ResponseInputParam, a list of function definitions, and a str
    #the ResponseInputParam is structured as a list of dicts, see tasks.json prompts for examples
    #the previous response id is so the agent can carry context forward
    return client.responses.create(
        model="gpt-5",
        input=input_items,
        tools=TOOLS,
        previous_response_id=previous_response_id,
    )
'''
Schema setting, task loading, report initialization will likely be moved to agent_common
'''
def run_workflow(patient_id : str, task : str, schema: str):
    api_client.set_schema(schema)
    #primitive approach for loading info specific to current task
    #all tasks are stored in a json, load the entire dict with key = current_task
    try:
        with open("mvp/tasks.json", "r") as file:
            tasks = json.load(file)
            current_task = tasks[task].copy()
    except:
        return RuntimeError
    analytics = initialize_agent_report(task = task, agent = "agent_brobot", patient_id = patient_id, schema = schema)
    '''
    We will need to write a helper for parsing the task prompt into format expect by Anthropic
    '''
    # initial_prompt = parse_task(current_task["prompt"], agent)

    '''
    The input will no longer be a single prompt, it will be the entire conversation history that we build as we go
    '''
    response = run_agent(current_task["prompt"], patient = patient_id)

    with open("agent_output.txt", "w") as file:
        file.write(response.model_dump_json(indent=2))

        while True:
            analytics["total_tokens_used"] += response.usage.total_tokens
            tool_outputs = []

            for item in response.output:
                if item.type == "function_call":
                    tool_name = item.name
                    arguments = json.loads(item.arguments)

                    print(f"Calling tool: {tool_name} for schema: {schema}")
                    print(arguments)

                    result = TOOL_MAP[tool_name](**arguments)

                    analytics["tools_workflow"].append(tool_name)
                    analytics["api_calls_made"] += 1
                    analytics["total_rows_retrieved"] += len(result)

                    tool_outputs.append({
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result),
                    })

            if not tool_outputs:
                break

            file.write("\n\n~~~~~TOOL OUTPUTS~~~~~\n")
            file.write(json.dumps(tool_outputs, indent=2))
            

            response = run_agent(
                input_items=tool_outputs,
                previous_response_id=response.id,
            )

            file.write("\n\n~~~~~NEXT RESPONSE~~~~~\n")
            file.write(response.model_dump_json(indent=2))
            # analytics["raw_response"] = response.output_text

        print("Final response:")
        print(response.output_text)
        print(analytics)

        file.write("\n\n~~~~~FINAL RESULT~~~~~\n")
        file.write(response.output_text)
        analytics["raw_response"] = response.output_text
        return analytics

if __name__ == "__main__":
    analytics_dict, response_text = run_workflow(patient_id="pat_4b66ed71-3922-62ba-b7fd-c2ca18c7cb60")
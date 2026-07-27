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
from .. import api_client
import json
from openai import OpenAI
import os
import copy
from datetime import datetime, timezone
from uuid import uuid4
from dotenv import load_dotenv #lets use utilize a .env file for dependency injection (in this case, our OpenAI API key)

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


'''
~~~~~~TOOLS~~~~~~~~~~~
Now we construct a list of tools for those wrappers we just wrote. These tools are simply descriptions of the functions in our program that the 
agent is allowed to use, formatted as JSON. Think of it as a guide we give our agent for navigating our database
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
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_immunizations",
    #     }
    # }
]

'''
Ok, so we've written the functions our agent is allowed to use, and we've written out the instructions for our agent on how to use those tools.
Our agent uses a tool by calling TOOL_MAP["name_of_tool_we_gave_it"]. Here, we write a little dictionary so our script knows which functions
to call when our agent does that :)
'''
TOOL_MAP = {
    "get_patient": api_client.get_patient,
    "get_medications": api_client.get_medications,
}

def parse_task(prompt, patient_id):
    prompt[1]["content"] = prompt[1]["content"] + patient_id
    return prompt

def run_agent(input_items, task, patient = None, previous_response_id=None):
    #we assemble the full user-side prompt by simply appending the relevant patient ID
    #the patient ID is added once by parse_task before the initial API call
    #we pass name of model we want, a ResponseInputParam, a list of function definitions, and a str
    #the ResponseInputParam is structured as a list of dicts, see tasks.json prompts for examples
    #the previous response id is so the agent can carry context forward

    #FIRST WE NEED TO LIMIT THE AVAILABLE TOOLS TO THOSE LISTED IN TASK DESCRIPTION
    available_tools = []
    for tool in TOOLS:
        if tool["name"] in task["allowed_endpoints"]:
            available_tools.append(tool)
    return client.responses.create(
        model="gpt-5",
        input=input_items,
        tools=available_tools,
        previous_response_id=previous_response_id,
    )

def run_workflow(patient_id : str, current_task, analytics):
    #"prompt" is a list of promp dicts {"role":sr, "content":str} formatted as expected by OpenAI agent
    prompt = parse_task(current_task["prompt"], patient_id)
    response = run_agent(prompt, current_task)

    with open("agent_output.txt", "a") as file:
        file.write(response.model_dump_json(indent=2))

        while True:
            analytics["total_tokens_used"] += response.usage.total_tokens
            tool_outputs = []

            for item in response.output:
                if item.type == "function_call":
                    tool_name = item.name
                    arguments = json.loads(item.arguments)

                    print(f"Calling tool: {tool_name}")
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
    with open("mvp/tasks.json", "r") as file:
                tasks = json.load(file)
                current_task = tasks["medication_retrieval_v1"].copy()
    DEBUG_REPORT = {
            "run_id": (
                f"{"medication_retrieval_v1"}-" 
                f"{uuid4().hex[:4]}"
                ),
            "task": "medication_retrieval_v1",
            "schema": "none",
            "agent": "openai",
            "provider" : "openai",
            "model": "openai",
            "patient_id": "pat_4b66ed71-3922-62ba-b7fd-c2ca18c7cb60",
            "tools_workflow": [],
            "workflow_metrics": {},
            "api_calls_made": 0,
            "total_tokens_used": 0,
            "total_rows_retrieved": 0,
            "raw_response": None,
            "patient_gt": None, 
            "output_metrics": {}
        }
    analytics_dict, response_text = run_workflow(patient_id="pat_4b66ed71-3922-62ba-b7fd-c2ca18c7cb60", current_task = current_task, analytics=DEBUG_REPORT )

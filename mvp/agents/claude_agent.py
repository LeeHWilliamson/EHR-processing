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
~~~~~~TOOLS~~~~~~~~~~~
Anthropic format
'''
TOOLS = [
    {
        "name": "get_patient",
        "description": "Retrieve demographic information for a patient.",
        "input_schema": {
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
        "name": "get_medications",
        "description": "Retrieve all medication information associated with a single patient.",
        "input_schema": {
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
'''
TOOL_MAP = {
    "get_patient": api_client.get_patient,
    "get_medications": api_client.get_medications,
}

#Convert task prompt into system instruction + message format expected by Anthropic
#we are only using this for the initial prompt, so no need for assistant messages
#current task format is designed for OpenAI use, so consists of system and user items
#anthropic needs system instructions as separate arg
#all else can just be sent in messages are
def parse_task(prompt):
    system_instructions = ""
    messages = []
    for prompt_item in prompt:
        if prompt_item["role"] == "system":
            system_instructions = prompt_item["content"]
        else:
            messages.append({"role" : "user" , "content" : prompt_item["content"]})
    return system_instructions, messages

'''
RUNNING THE AGENT
Currently just copy-paste from openAI script

Input args will likely be exactly the same (this function will likely end up getting move to agent_common), but will need to be preprocessed
into acceptable format

we will use client.messages.create() for Anthropic, model and tools parameter will likely be the same. input + previous_response_id will be encompassed
in the messages field, which we will need to manage to contain the entire conversation history for the current session.

Will likely need to add input to .system field as we cannot send system instructions via input
'''

def run_agent(system_instructions, input_messsages, patient = None):
    #we assemble the full user-side prompt by simply appending the relevant patient ID
    #anthropic message format will be list of all comms so far, so FIRST item is our task
    if "content" in input_messsages[0]:
        input_messsages[-1]["content"] = input_messsages[-1]["content"] + patient
    return client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        tools=TOOLS,
        tool_choice = {"type" : "auto"},
        system = system_instructions,
        messages = input_messsages
    )
'''
Schema setting, task loading, report initialization will likely be moved to agent_common
'''
def run_workflow(patient_id : str, task, analytics):

    
    '''
    We will need to write a helper for parsing the task prompt into format expect by Anthropic
    '''
    print(type(task))
    print(task)
    system_instructions, initial_prompt = parse_task(task["prompt"])
    messages = initial_prompt
    '''
    The input will no longer be a single prompt, it will be the entire conversation history that we build as we go
    INITIAL RUN: above prompt
    '''
    response = run_agent(system_instructions, initial_prompt, patient = patient_id)

    with open("claude_output.txt", "w") as file:
        file.write(response.model_dump_json(indent=2))

        while True:
            messages.append( {"role" : "user", "content" : "the following messages are the results of all your tool calls thus far"})
            analytics["total_tokens_used"] += response.usage.input_tokens+ response.usage.output_tokens
            tool_outputs = []

            for item in response.content:
                if item.type == "tool_use":
                    tool_name = item.name
                    print(type(item.input))
                    arguments = item.input

                    print(f"Calling tool: {tool_name}")
                    print(arguments)

                    result = TOOL_MAP[tool_name](**arguments)

                    analytics["tools_workflow"].append(tool_name)
                    analytics["api_calls_made"] += 1
                    analytics["total_rows_retrieved"] += len(result)

                    tool_outputs.append({
                        "type": "function_call_output",
                        "call_id": item.id,
                        "output": json.dumps(result),
                    })
                    result_str = str(result)
                    messages.append({"role" : "user", "content" : f"tool called: {tool_name}, result: {result_str}"})

            if not tool_outputs:
                break

            file.write("\n\n~~~~~TOOL OUTPUTS~~~~~\n")
            file.write(json.dumps(tool_outputs, indent=2))
            print("the message being sent is...", messages)
            response = run_agent(
                system_instructions,
                messages,
                patient_id,
            )

            file.write("\n\n~~~~~NEXT RESPONSE~~~~~\n")
            file.write(response.model_dump_json(indent=2))
            # analytics["raw_response"] = response.output_text

        final_response_text = response.content[-1].text
        print("Final response:")
        print(final_response_text)
        print(analytics)

        file.write("\n\n~~~~~FINAL RESULT~~~~~\n")
        file.write(final_response_text)
        analytics["raw_response"] = final_response_text
        return analytics

if __name__ == "__main__":
    analytics_dict= run_workflow(patient_id="pat_2f72b840-3c69-f42b-78a3-039283ff5384", task = "medication_retrieval_v1")
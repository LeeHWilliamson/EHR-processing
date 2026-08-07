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
import json
from anthropic import Anthropic
import os
from uuid import uuid4
from dotenv import load_dotenv #lets use utilize a .env file for dependency injection (in this case, our OpenAI API key)
from .agent_tools import CLAUDE_TOOLS as TOOLS, TOOL_MAP

load_dotenv()

client = Anthropic(
    api_key=os.getenv("ANTHROPIC_KEY")
)


#Convert task prompt into system instruction + message format expected by Anthropic
#we are only using this for the initial prompt, so no need for assistant messages
#current task format is designed for OpenAI use, so consists of system and user items
#anthropic needs system instructions as separate arg
#all else can just be sent in messages are
def parse_task(prompt, patient_id):
    """Convert a task prompt to Anthropic's system/messages arguments.

    A task may contain more than one system instruction. Anthropic expects those
    instructions outside ``messages``, so preserve all of them in their original
    order. The patient ID is part of the first user instruction and is appended
    while building a new message list so the reusable task definition is not
    mutated.
    """
    system_items = []
    messages = []
    patient_id_added = False

    for prompt_item in prompt:
        role = prompt_item["role"]
        content = prompt_item["content"]

        if role == "system":
            system_items.append(content)
        elif role == "user":
            if not patient_id_added:
                content = f"{content}\n\nPatient ID: {patient_id}"
                patient_id_added = True
            messages.append({"role": "user", "content": content})
        else:
            raise ValueError(f"Unsupported role in task prompt: {role!r}")

    if not patient_id_added:
        raise ValueError("Task prompt must contain at least one user message")

    system_instructions = "\n\n".join(system_items)
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

def run_agent(system_instructions, task, input_messages, patient = None):
    #we assemble the full user-side prompt by simply appending the relevant patient ID
    #anthropic message format will be list of all comms so far, so FIRST item is our task

    available_tools = []
    for tool in TOOLS:
        if tool["name"] in task["allowed_endpoints"]:
            available_tools.append(tool)
            
    return client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        tools=available_tools,
        tool_choice = {"type" : "auto"},
        system = system_instructions,
        messages = input_messages
    )
'''
Schema setting, task loading, report initialization will likely be moved to agent_common
'''
def run_workflow(patient_id : str, current_task, analytics):
    '''
    We will need to write a helper for parsing the task prompt into format expect by Anthropic
    '''
    print(type(current_task))
    print(current_task)
    system_instructions, initial_prompt = parse_task(
        current_task["prompt"], patient_id
    )
    messages = initial_prompt
    '''
    The input will no longer be a single prompt, it will be the entire conversation history that we build as we go
    INITIAL RUN: above prompt
    '''
    response = run_agent(system_instructions, task=current_task, input_messages=initial_prompt, patient = patient_id)

    with open("claude_output.txt", "a") as file:
        file.write(response.model_dump_json(indent=2))

        while True:
            analytics["total_tokens_used"] += response.usage.input_tokens+response.usage.output_tokens

            #Anthropic tells us why generation stopped. A tool result should only be
            #sent when the assistant actually stopped to request one.
            if response.stop_reason != "tool_use":
                break

            #Keep Claude's complete assistant turn in the conversation. This preserves
            #the tool_use block (and any thinking/signature blocks) that the following
            #tool_result blocks refer to.
            messages.append({"role" : "assistant", "content" : response.content})
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
                        "type": "tool_result",
                        "tool_use_id": item.id,
                        "content": json.dumps(result),
                    })

            if not tool_outputs:
                raise RuntimeError("Claude stopped for tool use without returning a tool_use block")

            #Anthropic expects every tool result together in the user message directly
            #after the assistant message containing the matching tool_use blocks.
            messages.append({"role" : "user", "content" : tool_outputs})

            file.write("\n\n~~~~~TOOL OUTPUTS~~~~~\n")
            file.write(json.dumps(tool_outputs, indent=2))
            print("the message being sent is...", messages)
            response = run_agent(
                system_instructions=system_instructions,
                task=current_task,
                input_messages=messages,
                patient=patient_id,
            )

            file.write("\n\n~~~~~NEXT RESPONSE~~~~~\n")
            file.write(response.model_dump_json(indent=2))
            # analytics["raw_response"] = response.output_text

        #A response can contain non-text blocks, so assemble the final answer only
        #from its text blocks instead of assuming the final block always has .text.
        final_response_text = "\n".join(
            item.text
            for item in response.content
            if item.type == "text"
        )
        print("Final response:")
        print(final_response_text)
        print(analytics)

        file.write("\n\n~~~~~FINAL RESULT~~~~~\n")
        file.write(final_response_text)
        analytics["raw_response"] = final_response_text
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
                "agent": "claude",
                "provider" : "claude",
                "model": "claude",
                "patient_id": "pat_2f72b840-3c69-f42b-78a3-039283ff5384",
                "tools_workflow": [],
                "workflow_metrics": {},
                "api_calls_made": 0,
                "total_tokens_used": 0,
                "total_rows_retrieved": 0,
                "raw_response": None,
                "patient_gt": None, 
                "output_metrics": {}
            }
    
    analytics_dict= run_workflow(patient_id="pat_2f72b840-3c69-f42b-78a3-039283ff5384", current_task=current_task, analytics=DEBUG_REPORT)

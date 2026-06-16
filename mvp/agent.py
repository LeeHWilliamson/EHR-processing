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
import api_client
import json
from openai import OpenAI
import os
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

def run_agent(input_items, previous_response_id=None):
    return client.responses.create(
        model="gpt-5",
        input=input_items,
        tools=TOOLS,
        previous_response_id=previous_response_id,
    )


if __name__ == "__main__":
    initial_messages = [
        {
            "role": "system",
            "content": (
                "You are an AI assistant with access to a synthetic Electronic Health Record API. "
                "Use the provided functions whenever you need patient information."
            )
        },
        {
            "role": "user",
            "content": (
                "List the names of all medications that "
                "pat_4b66ed71-3922-62ba-b7fd-c2ca18c7cb60 is currently taking."
            )
        }
    ]

    response = run_agent(initial_messages)

    with open("agent_output.txt", "w") as file:
        file.write(response.model_dump_json(indent=2))

        while True:
            tool_outputs = []

            for item in response.output:
                if item.type == "function_call":
                    tool_name = item.name
                    arguments = json.loads(item.arguments)

                    print(f"Calling tool: {tool_name}")
                    print(arguments)

                    result = TOOL_MAP[tool_name](**arguments)

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

        print("Final response:")
        print(response.output_text)

        file.write("\n\n~~~~~FINAL RESULT~~~~~\n")
        file.write(response.output_text)
            

    
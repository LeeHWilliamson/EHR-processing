#Synth-EHR Guided Tutorial
This markdown file provides a step-by-step summary of the tutorial application. I will outline the steps we take, and why we take them. 

## 1. The patient population
### Narrative
At this stage I will explain that, before we can generate patient records, we need to generate patients. We use the Synthea application developed by the Mitre Corporation to generate realistic, but not real, patients. I will explain that we have pre-generated 10 synthetic patients that can be seen below. Three of whom have developed Type II diabetes.

### User sees
10 patient tiles, each tile displays the patients name, date of birth, and gender. 

### User can
If the user mouses over a tile, they can also see the number of active conditions, active careplans, current medications, and allergies the patient has. Clicking on a patient allows one to view an abridged version of the patient JSON.

### System does
System loads the patient tiles and supports mouse-over and clicking

## 2. Design patient tools
### Narrative
I will explain that, typically, AI agents are not provided direct access to a medical database. They access it via a defined set of tools. An AI agent is only as good as the tools it has for accessing a database. Here you can define the tools you would like to provide your agent for accessing patient data. Each tool needs 4 things.
- A name
- A description of what the tools does
- Specifications regarding what data the tool can access
- a 'key' that the agent uses when calling a tool. 
I will have an example toolset defined for the user

### User sees
4 columns, labeled 'Tool Name', 'Description', 'Return', 'By'
They will see 10 rows corresponding to GET functions for each patient entity in the patient JSONS. So the first row might have the following values. "Get Patient Careplans", "Returns all information associated with all careplans recorded in the patients health record", "medications" (and blocks below medications corresponding to the fields the user wants to include), "patient id". Columns can be edited for any row. There will be a + sign button in each return field for the user to add additional entities (AND), and a 'remove' button at the end of each row for the user to remove a tool. Finally, an 'add' button at the very bottom of the table for the user to add more tools as desired.

### User can
Edit existing values for each tool, use the + sign in a row's 'Return' field to add additional entities. Click blocks corresponding to fields beneath each entity to filter what data gets returned. Remove tools, add tools.

### System 
displays the described interface, and generates tools as described when task is run

### Agent
will have access to each tool and complete lists of references of valid arguments.

## 3. Design task
### Narrative
I explain that the design of an agent task is integral to agent success. A task is where we provide the actual instructions for the agent, we need to explain what the agent is doing, and what information we want it to return. I will explain the difference between system and user instructions. I will explain that, for evaluation purposes, a task should also outline an ideal workflow for carrying out the task and some way of measuring the task's success. I provide an example task name and instructions for the user.

### User sees
User sees 5 sections laid out vertically. First is "Task Name" which contains a text box for naming the task. Second is "System Instructions" which provides a textbox for providing system instructions. Third is a similar section for "User Instructions." Fourth is labeled "Objective" and contains 2 dropdown menus labeled "Goal" and "Target." The former is populated by "Diagnose Condition" and its menu contains no other options. The latter contains "diabetes" and its menu contains all conditions that exist among the 10 patients. Final section is labeled "Ideal Workflow (Optional)" contains a dropdown menu with no value selected with a + sign button below it. 

### User can
Edit any of the freetext fields. Manipulate the dropdown menus. 

### System 
will create and carry out a task JSON corresponding to user settings


### Agent
Agent will have access to prompts associated with task. Agent will receive additional system instructions specifying how to structure returned data to simplify scoring.

## 4. Define noise
### Narrative
I will explain that injecting noise is the final step for translating a patient to their electronic health record representation.

### User sees
A section labeled "Noise Sources." And 2 listed noise sources. The first will have a dropdown menu with 1 value "Jitter Observations", beneath that we will have a another dropdown labeled "By" with only 1 value "description" and another dropdown right below that which contains only 1 value 'Glucose [Mass/volume] in Serum or Plasma'. The second noise source will have a dropdown menu with 1 value "censor condition" and another dropdown labeled "condition" with 1 value "prediabetes". There will be a button at the top of this section labeled "disable noise." 

### User can
Opt to disable noise. 

### System
Make a copy of each patient's JSON, implement pre-defined algorithms for injecting noise, and create or update a run-specific JSON file that outlines the edits that happened to each patient's file. The original value, edit that occurred, and resulting value.
If user opts to disable noise, no noise JSON file will be created.

### Agent 
Will only interact with edited JSONS

## 5. Task verification
Here we algorithmically trace the generation process for the patients that actually have diabetes, and count the number of entity entries (medications, encounters, etc) that exist on the path that took them from birth -> diabetes. If a patient does not have diabetes, then that count should be 0. We return the count in a little text notification. We then carry out the user's ideal workflow (if specified) on the unedited Patient JSON, and return the number of relevant entity entries returned (relevant == those found in the algorithmic sweep) and total entity entries returned. We then repeat the process, but on the noise-injected JSON. We then directly index the edited (noise-injected patient JSON) for all of the entity entries found by our first algorithmic pass, and give a count of how many we found.

### User sees
A button labeled "verify task." A tile corresponding to each patient. The tiles' shapes resemble the patient tiles we used earlier. Mousing over the tiles shows the user the stats described above. A tile will be outlined in orange if the user's ideal workflow returned signficantly fewer relevant entity entries, in the unedited patient JSON OR the noise-injected JSON, than we found tracing the module tree. A tile will have a red exclamation point if indexing the noise-injected JSON returned significantly fewer entries than we found tracing the module tree.

### User Can
Mouse over tiles to see the stats described above. Click the tile to see a report of what entities were missed by each validation check. Tweak previous settings and validate task again.

### System does
Carries out validation checks for patients with diabetes

## 6. Agent runs task
### User sees
User sees a button labeled "run task." Clicking it passes the tools, argument references, and task instructions to the Agent. Who then attempts the task for each patient. Once task has been completed, the user then sees 10 tiles, resembling those we've seen earlier, representing the patients. Mousing over the patients reveals the following metrics
- Workflow adherence (if applicable)
- Total token usage
- Final diagnosis (Diabetic or not)
- Number of relevant entity entries found / possible entries found in noise-injected JSON
- Total number of entity entries returned

### User can
Run their task, look at the results. Tweak previous settings, run task again.

### System does
System facilitates tool calls by AI agent, and returns summary results

### Agent
Simply carries out the defined task on noise-injected JSONs using the given tools.


## 7. Final Summary Dashboard
### User sees
A header labeled "Agent Performance". Beneath that is a filter slider with options "Condition Positive Patients, Condition Negative Patients, All Patients." Beneath that are 3 sections, "Workflow", "Accuracy", "Cost". 
Workflow will have a graph with nodes for each user-defined tool. Their will be a filter with the following options "Adherence", "Tool Call Frequency", "Mistaken Tool Call Frequency." The "Adherence" filter highlights the sequence of tool calls taken by the agent. The "ideal workflow" path will be lined out in green. Any other path taken for any patient run will be purple. The "tool call frequency" filter provides a heat map of the tool nodes, the heat color corresponds to the relative number of times a tool was called. The "mistaken tool call" frequency map will work similarly. Green represents tools called about the correct number of times. Cooler colors represent tools called less than expected (as defined by the number of times that tool shows up in the ideal workflow defined in the task). Hotter colors represent tools called more frequently than expected. 
The "Accuracy" section compares agent results to the algorithmic sweep. It gives a ratio of patients correctly diagnosed / total patients. It gives Average number of relevant entity entries found / Average number of relevant entity entries present. Both metrics are represented by a blue and magenta bar where the blue represents correct diagnoses / entity entries found, and magenta represents incorrect diagnoses / entity entries missed.
The "Cost" section will summarize the token usage and time taken by the agent. It will give average tokens used per tool call, average per patient, and variance between patients. It will do the same for time taken. It will visualize pie charts that represent what share of total/average tokens were used by each patient and each tool. It will do the same for time taken. This pie chart subsection will have a filter slider for "average" vs "total" that affects the pie chart visualizations.

### User can
Manipulate filters. Download the report data. 

### System does
Carries out algorithms required to summarize and render the data. 
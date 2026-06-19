'''
This script will format the output text of the agent, and compare the accuracy of the result to the patient GT
input: patient GT and agent output text
output: accuracy metric as float, list of meds that were missed by agent, list of meds that were hallucinated by agent
'''

def parse_agent_output(agent_output = None):
    #agent output is given as a single string with "\n"s to separate entries, and each entry has a "- " as well
    temp_str = ""
    for character in agent_output:
        if character == "-":
            continue
        temp_str = temp_str + character
    #the agent_output is given as a single string
    #each entry is followed by a newline characters, so we can use that to separate them into a list of strings
    parsed_output = temp_str.split("\n")
    for index in range(len(parsed_output)):
        parsed_output[index] = parsed_output[index].strip()
    return parsed_output

def calc_accuracy(med_gt_list = None, agent_output = None):
    if med_gt_list is None or agent_output is None:
        return "please pass required arguments"
    parsed_output_list = parse_agent_output(agent_output)
    #now both the GT and agent returned meds are in list form
    #for now we will assume there are no duplicate meds
    med_gt_set = set(med_gt_list)
    parsed_output_set = set(parsed_output_list)
    #make list to hold any meds that are in GT that were not included in agent output
    missed_meds = []
    #and list to hold any meds that are NOT in GT but were added in agent output
    hallucinated_meds = []
    correct_meds = 0
    for medication in parsed_output_set:
        if medication in med_gt_set:
            correct_meds += 1
        else:
            hallucinated_meds.append(medication)
    for medication in med_gt_set:
        if medication not in parsed_output_set:
            missed_meds.append(medication)
    accuracy = correct_meds/len(parsed_output_list)
    return accuracy, hallucinated_meds, missed_meds
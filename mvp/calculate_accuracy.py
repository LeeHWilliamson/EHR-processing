'''
This script will format the output text of the agent, and compare the accuracy of the result to the patient GT
input: patient GT and agent output text
output: accuracy metric as float, list of meds that were missed by agent, list of meds that were hallucinated by agent
'''

def parse_agent_output(agent_output = None):
    #agent output is given as a single string with "\n"s to separate entries
    #each entry is followed by a newline character, so we can use that to separate them into a list of strings
    parsed_output = agent_output.split("\n")
    for index in range(len(parsed_output)):
        parsed_output[index] = parsed_output[index].strip()
    return parsed_output

'''
We want all data to be strs right now for simpler comparison and to deal with totally left-field agent responses
We also want our data to be ordered so we can compare item by item
'''
def process_lists(med_gt_list = None, agent_output = None):
    #patient GT data will often be numeric, so we need to convert to str
    med_gt_strs = [str(med) for med in med_gt_list]
    #agent output is always a str so no need to convert that

    #we can create a dict of item : frequency for simpler comparisons
    gt_dict = {}
    agent_output_dict = {}
    for med in med_gt_strs:
        if med not in gt_dict:
            gt_dict[med] = 1
        else:
            gt_dict[med] += 1
    for med in agent_output:
        if med not in agent_output_dict:
            agent_output_dict[med] = 1
        else:
            agent_output_dict += 1
    return gt_dict, agent_output_dict



def calc_metrics(med_gt_list = None, agent_output = None):
    if med_gt_list is None or agent_output is None:
        return "please pass required arguments"
    #break up str
    parsed_output_list = parse_agent_output(agent_output)
    #convert all data to hashable structure
    gt_dict, agent_output_dict = process_lists(med_gt_list = med_gt_list, agent_output= parsed_output_list)
    #make list to hold any meds that are in GT that were not included in agent output
    missed_meds = {}
    #and list to hold any meds that are NOT in GT but were added in agent output
    hallucinated_meds = {}
    hallucinated_med_count = 0 #total number of false positives for calculating accuracy
    missed_med_count = 0 #total number of false negatives for calculating precision
    total_agent_meds = 0 #total number of positives for calculating accuracy
    total_gt_meds = 0 #Correct number of positives for calculating accuracy
    metrics = {} #finally, a dict for holding whatever metrics we calculated for this task
    for medication in agent_output_dict:
        total_agent_meds += agent_output_dict[medication]
        #if this med found by agent does exist in GT, double check their occurrences match
        if agent_output_dict[medication] in gt_dict:
            #if agent_output has more isntances of this med than GT, those are hallucinations
            hallucinations = agent_output_dict[medication]-gt_dict[medication]
            if hallucinations > 0:
                hallucinated_meds[medication] = hallucinations
            #if GT has more instances of this med than agent_output, those are missed meds
            missed = gt_dict[medication]-agent_output_dict[medication]
            missed_med_count += max(0, missed)
            if missed > 0:
                missed_meds[medication] = missed
            missed_med_count += max(0, gt_dict[medication]-agent_output_dict[medication])
        #if this med does NOT exist in GT, than all occurrences are hallucinations
        else:
            hallucinated_med_count += agent_output_dict[medication]
    for medication in gt_dict:
        total_gt_meds += gt_dict[medication]
        #we have already found meds that occur in both dicts, but at different frequencies
        #now we just needs meds that occur in GT but not the agent_output
        if medication not in agent_output_dict:
            missed_meds[medication] = gt_dict[medication]
            missed_med_count += gt_dict[medication]
    #now lets calculate accuracy of our agent
    metrics["precision"] = (total_agent_meds-hallucinated_med_count) / (total_agent_meds) #true positives / total positives
    metrics["recall"] = (total_agent_meds-hallucinated_med_count) / (total_gt_meds) #true positives / all classification items
    return metrics, hallucinated_meds, missed_meds
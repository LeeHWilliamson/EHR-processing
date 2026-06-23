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
            agent_output_dict[med] += 1
    return gt_dict, agent_output_dict


def calc_metrics(med_gt_list, agent_output):
    if med_gt_list is None or agent_output is None:
        return "please pass required arguments"
    #cast gt items to str, remove whitespaces and \n
    expected = [str(item).strip() for item in med_gt_list]
    #if line.strip() will result in a Truthy str, then output it
    #.splitlines splits strs along newline chars, smarter than .split("\n")
    actual = [
        line.strip()
        for line in agent_output.splitlines()
        if line.strip()
    ]

    gt_counts = {}
    actual_counts = {}

    #get frequencies of all items in gt and response
    for item in expected:
        gt_counts[item] = gt_counts.get(item, 0) + 1

    for item in actual:
        actual_counts[item] = actual_counts.get(item, 0) + 1

    #union
    all_items = gt_counts.keys() | actual_counts.keys()

    #if gt frequency < response frequency, some items were hallucinated by agent
    #if gt frequency > response frequency, some items were missed by agent
    true_positives = sum(
        min(gt_counts.get(item, 0), actual_counts.get(item, 0))
        for item in all_items
    )

    #use list comprehension to get hallucinations by item
    hallucinated = {
        item: actual_counts[item] - gt_counts.get(item, 0)
        for item in actual_counts
        if actual_counts[item] > gt_counts.get(item, 0)
    }
    #use list comprehension to get missed by item
    missed = {
        item: gt_counts[item] - actual_counts.get(item, 0)
        for item in gt_counts
        if gt_counts[item] > actual_counts.get(item, 0)
    }

    #if there is a gt record for comparison, calculate precision
    #if there is no gt record, but there is an agent_reponse, well that precision is 0
    precision = (
        true_positives / len(actual)
        if actual
        else 1.0 if not expected else 0.0
    )

    recall = (
        true_positives / len(expected)
        if expected
        else 1.0 if not actual else 0.0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "hallucinated_items" : hallucinated,
        "missed_items" : missed
    }
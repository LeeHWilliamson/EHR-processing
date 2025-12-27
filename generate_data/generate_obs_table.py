doc_template = 'schemas/document_instance.json'
'''
template and degrading mode will be randomly selected from what is available
'''
def select_template(type = None):
    pass

def select_degrade_mode():
    pass

def generate_observation_table(patient):
    template = select_template("observations")
    degrade_mode = select_degrade_mode()
    expected_obs = select_obs(patient, template)

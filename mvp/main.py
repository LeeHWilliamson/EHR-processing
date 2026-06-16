# from generate_data.load_patient_gt import run_end_to_end
import api_endpoints
if __name__ == '__main__': 
    print("starting")
    #generate patients
    # patient_paths = run_end_to_end(input_directory=r'synthea/output/csv', output_directory=r'synthea/output/json')
    #populate SQLite DB
    #For each patient...
        #run agent, return analytics_dict and response_text
        #get patient GT
        #compare GT to response_text to calc accuracy and get list of mistakes, update analytics_dict
        #output analytics as json
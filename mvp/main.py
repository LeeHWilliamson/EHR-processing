from generate_data.load_patient_gt import run_end_to_end

if __name__ == '__main__': 
    patient_paths = run_end_to_end(input_directory=r'synthea/output/csv', output_directory=r'synthea/output/json')
    
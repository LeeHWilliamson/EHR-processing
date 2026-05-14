# Synth-EHR

## Purpose
A synthetic data generation pipeline that creates canonical patient health records, scatters patient information across PDFs, images, tables, and text documents, and uses AI tools to recreate the original records. Providing metrics for comparing recreation speed and accuracy

## Motivation
Modern AI tools show great promise in enhancing medical workflows by unifying fragmented patient data into coherent medical records. Deploying AI tools in a medical context, however, requires an exhaustive evaluation of the tool's risks of hallucination, compliance violation, and data leakage. Such an evaluation is uniquely challenging in the medical field. Assessing an AI tool's accuracy requires a dataset that is deeply fragmented (discharge summaries, insurance documents, lab resullts) but also accessible and with an objective gorund truth. Furthermore, this data must be contained in a secure environment where compliance and data-privacy issues can be observed with limited liability. 

There are tools available that assist in generating quality synthetic patient data, but this data is typically output directly to CSVs, spreadsheets, and database maangement systems, and thus does not accurately recreate the context that most patient data actually exists in; fragmented collections of images, tables, and PDFs scattered across files. This tool seeks to build on an existing patient data generation tool (Synthea) by outputing the generated data in a format that matches real-world medical systems.

## Features
-Generation of patient data via Synthea
-Creation of ground truth databases for patient health records, and generated documents
-Output of patient health records to procedurally-generated PDFs, images, tables, and text documents.
-Random degradation of generated documents via effects such as blur, image downsampling, typos, information ommission and more*
-OCR/AI pipeline for recreating patient health records from generated documents
-Dashboard for assessing data generation, and data recreation speed and accuracy

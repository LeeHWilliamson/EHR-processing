### Patient Provenance
The patient provenance JSONs are what hold the ground truth in the original generated patients. This ground truth is assembled by tracing the states visited in the metabolic-syndrome path and unioning these states with those that serve as input to these states and states that, according to real world evidence, should affect diabetes testing and diagnosis.

Entries in these 3 lists overlap to some degree

Casual_records contain the normalized clinical records that are output by the traced states in  metabolic module during patient generation

Decision_input_records include normalized records output by states whose output is read by diabetes causal states. This list is not assembled at runtime

diagnostic_evidence_records these are all patient records that according to the literature should affect diabetes diagnosis. They are taken from the output patient, and thus may include evidence that is relevant, but occurred after the initial diagnosis.


### Fix
Patient demographic info patient[patient] is not currently accessible by agents
make sure errors actually give feedback instead of passing

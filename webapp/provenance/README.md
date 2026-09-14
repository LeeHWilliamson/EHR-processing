# Diabetes provenance prototype

This prototype builds the guided tutorial's answer key from two representations
of the same ten synthetic patients:

- `json/`: native Synthea JSON with module execution history
- `normalized_json/`: the simplified EHR records exposed through tutorial tools

Run it from the repository root:

```bash
python -m webapp.provenance.build_diabetes_manifest
```

The command writes one JSON manifest per patient and a consolidated `review.md`
under `webapp/patients/current_run/full_patients/provenance/`.

## Output sets

- `causal_records`: normalized records created by states on the executed Synthea
  metabolic-syndrome path through the diagnosis event.
- `decision_input_records`: normalized records representing values read by the
  inspected Synthea modules. This implementation is diabetes-specific and is
  not yet a general transitive dependency tracer.
- `diagnostic_evidence_records`: records selected by the explicit, versioned
  diabetes rubric. Each item is classified as diagnostic, risk context, or an
  interpretation caveat.
- `leakage_records`: records whose code or text explicitly discloses diabetes.
  These are candidates for mandatory censorship before an agent run.
- `decision_evidence_overlap`: records present in both the decision-input and
  clinical-evidence sets.

The rubric is stored in `diabetes_evidence_rules.json`; it should be reviewed as
product policy rather than treated as a clinical standard. Diagnostic criteria
were based on the American Diabetes Association and NIDDK summaries:

- https://diabetes.org/about-diabetes/diagnosis
- https://www.niddk.nih.gov/health-information/diabetes/overview/tests-diagnosis

## Important semantics

The ground-truth label is not produced by the clinical rubric. A patient is
positive only when the pristine normalized record contains Synthea's exact Type
II diabetes code (`44054006`) or display.

Causal and decision-input records are cut off at the original diagnosis event.
Clinical evidence and leakage are evaluated across the complete record because
the tutorial asks the agent about the patient's current record after explicit
labels are censored.

Repeated clinical measurements are deliberately bounded by the rubric's
selection rules so a long-lived patient does not dominate evidence-coverage
metrics merely by having more annual wellness visits.

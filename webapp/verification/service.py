from __future__ import annotations

from collections import Counter
from typing import Any

from webapp.noise.models import NoiseConfiguration
from webapp.records.repository import PatientRepository


EVIDENCE_KEYS = ("causal_records", "decision_input_records", "diagnostic_evidence_records")


def _record_index(patient: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for entity, source in patient.items():
        records = source if isinstance(source, list) else [source] if isinstance(source, dict) else []
        for record in records:
            record_id = record.get("id") if isinstance(record, dict) else None
            if record_id is not None:
                indexed[(entity, str(record_id))] = record
    return indexed


def _expected_records(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    expected: dict[tuple[str, str], dict[str, Any]] = {}
    for source_name in EVIDENCE_KEYS:
        for record in manifest.get(source_name, []):
            record_id = record.get("id")
            if record_id is None:
                continue
            key = (record["entity"], str(record_id))
            if key not in expected:
                expected[key] = {
                    "entity": record["entity"],
                    "record_id": str(record_id),
                    "description": record.get("description"),
                    "date": record.get("date"),
                    "classifications": [],
                }
            classification = record.get("classification") or source_name.removesuffix("_records")
            if classification not in expected[key]["classifications"]:
                expected[key]["classifications"].append(classification)
    return sorted(expected.values(), key=lambda item: (item["entity"], item["date"] or "", item["record_id"]))


def verify_patient(
    patient_id: str,
    configuration: NoiseConfiguration,
    repository: PatientRepository,
) -> dict[str, Any]:
    pristine = repository.load_pristine(patient_id)
    baseline = repository.load_agent_visible(patient_id)
    noisy, noise_edits = repository.load_noisy_agent_visible(patient_id, configuration)
    manifest = repository.load_manifest(patient_id)
    pristine_index = _record_index(pristine)
    baseline_index = _record_index(baseline)
    noisy_index = _record_index(noisy)
    noise_by_record = {
        (edit["entity"], str(edit["record_id"])): edit
        for edit in noise_edits
        if edit.get("record_id") is not None
    }

    records = []
    for expected in _expected_records(manifest):
        key = (expected["entity"], expected["record_id"])
        original = pristine_index.get(key)
        baseline_record = baseline_index.get(key)
        noisy_record = noisy_index.get(key)
        if baseline_record is None:
            status = "baseline_censored"
        elif noisy_record is None:
            status = "missing_after_noise"
        elif noisy_record != baseline_record:
            status = "modified_by_noise"
        elif original is not None and baseline_record != original:
            status = "modified_by_baseline"
        else:
            status = "unchanged"
        records.append({
            **expected,
            "status": status,
            "noise_edit": noise_by_record.get(key),
        })

    counts = Counter(record["status"] for record in records)
    expected_count = len(records)
    baseline_accessible = expected_count - counts["baseline_censored"]
    noise_accessible = baseline_accessible - counts["missing_after_noise"]
    if expected_count == 0:
        status = "neutral"
    elif counts["missing_after_noise"]:
        status = "red"
    elif counts["modified_by_noise"]:
        status = "amber"
    else:
        status = "green"
    summary = next(item for item in repository.summaries() if item["patient_id"] == patient_id)
    return {
        "patient_id": patient_id,
        "patient_name": f'{summary["first_name"]} {summary["last_name"]}',
        "has_type_2_diabetes": bool(manifest.get("has_type_2_diabetes")),
        "status": status,
        "counts": {
            "expected": expected_count,
            "unchanged": counts["unchanged"],
            "modified_by_baseline": counts["modified_by_baseline"],
            "baseline_censored": counts["baseline_censored"],
            "baseline_accessible": baseline_accessible,
            "modified_by_noise": counts["modified_by_noise"],
            "missing_after_noise": counts["missing_after_noise"],
            "accessible_after_noise": noise_accessible,
        },
        "records": records,
    }


def verify_cohort(configuration: NoiseConfiguration, repository: PatientRepository) -> dict[str, Any]:
    patients = [verify_patient(patient_id, configuration, repository) for patient_id in repository.patient_ids()]
    return {
        "noise_enabled": configuration.enabled,
        "patients": patients,
        "summary": {
            "patients_verified": len(patients),
            "green": sum(patient["status"] == "green" for patient in patients),
            "amber": sum(patient["status"] == "amber" for patient in patients),
            "red": sum(patient["status"] == "red" for patient in patients),
            "neutral": sum(patient["status"] == "neutral" for patient in patients),
        },
    }

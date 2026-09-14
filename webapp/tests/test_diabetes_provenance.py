from webapp.provenance.build_diabetes_manifest import (
    DIABETES_CODE,
    NativeEntry,
    candidate_score,
    has_diabetes,
    iso_date,
)
from webapp.provenance.diabetes_evidence import build_hybrid_classification


def test_diabetes_label_uses_exact_code() -> None:
    patient = {
        "conditions": [
            {"code": 714628002, "description": "Prediabetes (finding)"},
            {"code": int(DIABETES_CODE), "description": "localized label"},
        ]
    }
    assert has_diabetes(patient)


def test_prediabetes_alone_is_negative() -> None:
    patient = {"conditions": [{"code": 714628002, "description": "Prediabetes (finding)"}]}
    assert not has_diabetes(patient)


def test_native_match_prefers_encounter_code_description_and_date() -> None:
    native = NativeEntry(
        entity="observations",
        encounter_uuid="encounter-1",
        encounter_name="Wellness",
        state_name="Record_HA1C",
        start=1_725_000_000_000,
        uuid="observation-1",
        code="4548-4",
        description="Hemoglobin A1c/Hemoglobin.total in Blood",
    )
    normalized = {
        "encounter": "encounter-1",
        "code": "4548-4",
        "description": "Hemoglobin A1c/Hemoglobin.total in Blood",
        "date": iso_date(native.start),
    }
    assert candidate_score(native, normalized) == 18


def test_hybrid_classifier_separates_evidence_and_leakage() -> None:
    patient = {
        "patient": {
            "id": "pat-1",
            "birthdate": "1970-01-01",
            "race": "white",
        },
        "observations": [
            {
                "id": "a1c-1",
                "code": "4548-4",
                "description": "Hemoglobin A1c/Hemoglobin.total in Blood",
                "value": "7.1",
                "units": "%",
                "date": "2025-01-01",
                "encounter": "enc-1",
            },
            {
                "id": "weight-1",
                "code": "29463-7",
                "description": "Body Weight",
                "value": "95.0",
                "units": "kg",
                "date": "2025-01-01",
                "encounter": "enc-1",
            },
        ],
        "conditions": [
            {
                "id": "condition-1",
                "code": DIABETES_CODE,
                "description": "Diabetes mellitus type 2 (disorder)",
                "startDate": "2025-01-02",
                "encounter": "enc-1",
            }
        ],
    }
    result = build_hybrid_classification(patient, "2025-01-02")
    decision_ids = {record["id"] for record in result["decision_input_records"]}
    evidence_ids = {record["id"] for record in result["diagnostic_evidence_records"]}
    leakage_ids = {record["id"] for record in result["leakage_records"]}

    assert "a1c-1" in decision_ids
    assert {"a1c-1", "weight-1"}.issubset(evidence_ids)
    assert "condition-1" in leakage_ids
    assert result["decision_evidence_overlap"] == [{"entity": "observations", "id": "a1c-1"}]


def test_prediabetes_is_not_baseline_target_leakage() -> None:
    patient = {
        "patient": {"id": "pat-1", "birthdate": "1970-01-01", "race": "white"},
        "conditions": [
            {
                "id": "prediabetes-1",
                "code": "714628002",
                "description": "Prediabetes (finding)",
                "startDate": "2025-01-01",
            }
        ],
    }
    result = build_hybrid_classification(patient, None)
    assert result["leakage_records"] == []


def test_post_diagnosis_records_remain_available_as_current_evidence() -> None:
    patient = {
        "patient": {"id": "pat-1", "birthdate": "1970-01-01", "race": "white"},
        "observations": [
            {
                "id": "late-a1c",
                "code": "4548-4",
                "description": "Hemoglobin A1c/Hemoglobin.total in Blood",
                "date": "2025-02-01",
            }
        ],
    }
    result = build_hybrid_classification(patient, "2025-01-01")
    assert any(record["id"] == "late-a1c" for record in result["diagnostic_evidence_records"])


def test_clinical_evidence_limits_repeated_measurements_to_latest_values() -> None:
    patient = {
        "patient": {"id": "pat-1", "birthdate": "1970-01-01", "race": "white"},
        "observations": [
            {
                "id": f"weight-{year}",
                "code": "29463-7",
                "description": "Body Weight",
                "date": f"{year}-01-01",
            }
            for year in range(2010, 2020)
        ],
    }
    result = build_hybrid_classification(patient, None)
    weights = [
        record for record in result["diagnostic_evidence_records"]
        if record["code"] == "29463-7"
    ]
    assert [record["id"] for record in weights] == ["weight-2017", "weight-2018", "weight-2019"]

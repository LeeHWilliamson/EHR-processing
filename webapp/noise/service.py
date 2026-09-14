from __future__ import annotations

import copy
import hashlib
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from webapp.noise.models import NoiseConfiguration


GLUCOSE_DESCRIPTION = "Glucose [Mass/volume] in Serum or Plasma"
PREDIABETES_CODE = "714628002"
PREDIABETES_DESCRIPTION = "Prediabetes (finding)"
JITTER_PERCENT = 10


def noise_sources() -> list[dict[str, Any]]:
    return [
        {
            "id": "jitter_glucose_observations",
            "operation": "Jitter Observations",
            "by": "description",
            "target": GLUCOSE_DESCRIPTION,
            "amount": f"±{JITTER_PERCENT}%",
        },
        {
            "id": "censor_prediabetes",
            "operation": "Censor Condition",
            "by": "condition",
            "target": "Prediabetes",
        },
    ]


def _jittered_value(patient_id: str, record: dict[str, Any]) -> str | int | float | None:
    original = record.get("value")
    try:
        numeric = Decimal(str(original))
    except (InvalidOperation, TypeError, ValueError):
        return None
    identity = f"{patient_id}:{record.get('id')}:{record.get('date')}".encode()
    bucket = int.from_bytes(hashlib.sha256(identity).digest()[:4], "big") % 2001
    fraction = Decimal(bucket - 1000) / Decimal(10000)
    jittered = (numeric * (Decimal(1) + fraction)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    if isinstance(original, str):
        return format(jittered, "f")
    if isinstance(original, int):
        return int(jittered.to_integral_value(rounding=ROUND_HALF_UP))
    return float(jittered)


def apply_noise(
    patient: dict[str, Any],
    patient_id: str,
    configuration: NoiseConfiguration,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    noisy = copy.deepcopy(patient)
    if not configuration.enabled:
        return noisy, []

    edits: list[dict[str, Any]] = []
    for observation in noisy.get("observations", []):
        if observation.get("description") != GLUCOSE_DESCRIPTION:
            continue
        original = observation.get("value")
        result = _jittered_value(patient_id, observation)
        if result is None:
            continue
        observation["value"] = result
        edits.append({
            "operation": "jitter_observation",
            "entity": "observations",
            "record_id": observation.get("id"),
            "field": "value",
            "original_value": original,
            "resulting_value": result,
        })

    kept_conditions = []
    for condition in noisy.get("conditions", []):
        is_prediabetes = (
            str(condition.get("code")) == PREDIABETES_CODE
            or condition.get("description") == PREDIABETES_DESCRIPTION
        )
        if is_prediabetes:
            edits.append({
                "operation": "censor_condition",
                "entity": "conditions",
                "record_id": condition.get("id"),
                "original_value": copy.deepcopy(condition),
                "resulting_value": None,
            })
        else:
            kept_conditions.append(condition)
    noisy["conditions"] = kept_conditions
    return noisy, edits


def summarize_noise_impact(records: list[tuple[str, dict[str, Any]]], configuration: NoiseConfiguration) -> dict[str, int]:
    jittered = 0
    censored = 0
    affected_patients = 0
    for patient_id, patient in records:
        _, edits = apply_noise(patient, patient_id, configuration)
        if edits:
            affected_patients += 1
        jittered += sum(edit["operation"] == "jitter_observation" for edit in edits)
        censored += sum(edit["operation"] == "censor_condition" for edit in edits)
    return {
        "patients_affected": affected_patients,
        "observations_jittered": jittered,
        "conditions_censored": censored,
    }

import asyncio

import httpx

from webapp.app.endpoints import app
from webapp.noise.models import NoiseConfiguration
from webapp.noise.service import GLUCOSE_DESCRIPTION, PREDIABETES_CODE, apply_noise
from webapp.records.repository import PatientRepository


repository = PatientRepository()


def test_noise_is_deterministic_and_does_not_mutate_source() -> None:
    patient_id = "pat_d51799f2-25b2-4bab-11b5-d618b6e4e782"
    source = repository.load_agent_visible(patient_id)
    original_glucose = [
        item["value"] for item in source["observations"]
        if item.get("description") == GLUCOSE_DESCRIPTION
    ]

    first, first_edits = apply_noise(source, patient_id, NoiseConfiguration(enabled=True))
    second, second_edits = apply_noise(source, patient_id, NoiseConfiguration(enabled=True))

    resulting_glucose = [
        item["value"] for item in first["observations"]
        if item.get("description") == GLUCOSE_DESCRIPTION
    ]
    assert first == second
    assert first_edits == second_edits
    assert resulting_glucose != original_glucose
    assert [
        item["value"] for item in source["observations"]
        if item.get("description") == GLUCOSE_DESCRIPTION
    ] == original_glucose
    assert all(str(item.get("code")) != PREDIABETES_CODE for item in first["conditions"])


def test_disabling_noise_returns_unchanged_copy_and_no_audit() -> None:
    patient_id = repository.patient_ids()[0]
    source = repository.load_agent_visible(patient_id)
    result, edits = apply_noise(source, patient_id, NoiseConfiguration(enabled=False))
    assert result == source
    assert result is not source
    assert edits == []


def test_noise_api_reports_cohort_impact_and_disabled_state() -> None:
    async def validate() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            defaults = await client.get("/api/noise/defaults")
            assert defaults.status_code == 200
            assert len(defaults.json()["sources"]) == 2

            enabled = await client.post("/api/noise/validate", json={"enabled": True})
            assert enabled.status_code == 200
            assert enabled.json()["impact"]["observations_jittered"] > 0
            assert enabled.json()["impact"]["conditions_censored"] > 0

            disabled = await client.post("/api/noise/validate", json={"enabled": False})
            assert disabled.status_code == 200
            assert disabled.json()["sources"] == []
            assert disabled.json()["impact"] == {
                "patients_affected": 0,
                "observations_jittered": 0,
                "conditions_censored": 0,
            }

    asyncio.run(validate())

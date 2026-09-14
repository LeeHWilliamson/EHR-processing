import asyncio

import httpx

from webapp.app.endpoints import app
from webapp.noise.models import NoiseConfiguration
from webapp.records.repository import PatientRepository
from webapp.verification.service import verify_cohort, verify_patient


repository = PatientRepository()


def test_disabled_noise_preserves_every_baseline_accessible_expected_record() -> None:
    result = verify_cohort(NoiseConfiguration(enabled=False), repository)
    assert result["summary"]["patients_verified"] == 10
    assert result["summary"]["red"] == 0
    assert result["summary"]["amber"] == 0
    assert all(patient["counts"]["missing_after_noise"] == 0 for patient in result["patients"])
    assert all(patient["counts"]["modified_by_noise"] == 0 for patient in result["patients"])


def test_enabled_noise_attributes_noise_and_baseline_changes_separately() -> None:
    patient_id = "pat_d51799f2-25b2-4bab-11b5-d618b6e4e782"
    result = verify_patient(patient_id, NoiseConfiguration(enabled=True), repository)
    assert result["counts"]["modified_by_noise"] > 0
    assert result["counts"]["missing_after_noise"] > 0
    assert result["counts"]["baseline_censored"] > 0
    assert any(
        record["status"] == "modified_by_noise"
        and record["noise_edit"]["operation"] == "jitter_observation"
        for record in result["records"]
    )
    assert any(
        record["status"] == "missing_after_noise"
        and record["noise_edit"]["operation"] == "censor_condition"
        for record in result["records"]
    )


def test_verification_api_returns_patient_drill_down_reports() -> None:
    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/verification/run", json={"enabled": True})
            assert response.status_code == 200
            payload = response.json()
            assert len(payload["patients"]) == 10
            assert payload["summary"]["patients_verified"] == 10
            assert all("records" in patient for patient in payload["patients"])

    asyncio.run(run())

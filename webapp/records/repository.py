"""Read immutable tutorial fixtures and derive the agent-visible record."""

from __future__ import annotations

import copy
import json
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Any


WEBAPP_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = WEBAPP_DIR / "patients" / "current_run" / "full_patients"
REDACTED = "[REDACTED: target leakage]"


class PatientNotFoundError(KeyError):
    pass


class PatientRepository:
    def __init__(self, data_dir: Path = DEFAULT_DATA_DIR) -> None:
        self.data_dir = data_dir
        self.normalized_dir = data_dir / "normalized_json"
        self.provenance_dir = data_dir / "provenance"

    @staticmethod
    def canonical_id(value: str) -> str:
        return value if value.startswith("pat_") else f"pat_{value}"

    @cached_property
    def index(self) -> dict[str, Path]:
        index: dict[str, Path] = {}
        for path in sorted(self.normalized_dir.glob("*.json")):
            with path.open(encoding="utf-8") as handle:
                patient_id = json.load(handle)["patient"]["id"]
            index[patient_id] = path
        return index

    def patient_ids(self) -> list[str]:
        return sorted(self.index)

    @cached_property
    def cohort_groups(self) -> dict[str, dict[str, Any]]:
        path = self.data_dir / "cohort.json"
        if not path.is_file():
            return {}
        with path.open(encoding="utf-8") as handle:
            return json.load(handle).get("groups", {})

    def cohort_group_for(self, patient_id: str) -> str | None:
        canonical = self.canonical_id(patient_id)
        return next(
            (
                group_name
                for group_name, group in self.cohort_groups.items()
                if canonical in group.get("patient_ids", [])
            ),
            None,
        )

    @lru_cache(maxsize=10)
    def _load_pristine_cached(self, canonical: str) -> dict[str, Any]:
        path = self.index.get(canonical)
        if path is None:
            raise PatientNotFoundError(canonical)
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def load_pristine(self, patient_id: str) -> dict[str, Any]:
        return copy.deepcopy(self._load_pristine_cached(self.canonical_id(patient_id)))

    @lru_cache(maxsize=10)
    def _load_manifest_cached(self, canonical: str) -> dict[str, Any]:
        path = self.provenance_dir / f"{canonical.removeprefix('pat_')}.json"
        if not path.is_file():
            return {"leakage_records": []}
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def load_manifest(self, patient_id: str) -> dict[str, Any]:
        return copy.deepcopy(self._load_manifest_cached(self.canonical_id(patient_id)))

    @staticmethod
    def _record_by_id(patient: dict[str, Any], entity: str, record_id: str | None) -> dict[str, Any] | None:
        records = patient.get(entity, [])
        if not isinstance(records, list):
            return None
        return next((record for record in records if record.get("id") == record_id), None)

    @lru_cache(maxsize=10)
    def _load_agent_visible_cached(self, canonical: str) -> dict[str, Any]:
        patient = self.load_pristine(canonical)
        manifest = self.load_manifest(canonical)
        removals: dict[str, set[str | None]] = {}
        for leakage in manifest.get("leakage_records", []):
            entity = leakage["entity"]
            record_id = leakage.get("id")
            if leakage.get("action") == "remove_record":
                removals.setdefault(entity, set()).add(record_id)
                continue
            record = self._record_by_id(patient, entity, record_id)
            if record is not None:
                for field in leakage.get("matching_fields", []):
                    if field in record:
                        record[field] = REDACTED
        for entity, ids in removals.items():
            patient[entity] = [record for record in patient.get(entity, []) if record.get("id") not in ids]
        return patient

    def load_agent_visible(self, patient_id: str) -> dict[str, Any]:
        return copy.deepcopy(self._load_agent_visible_cached(self.canonical_id(patient_id)))

    def load_noisy_agent_visible(self, patient_id: str, configuration: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        from webapp.noise.service import apply_noise

        canonical = self.canonical_id(patient_id)
        return apply_noise(self.load_agent_visible(canonical), canonical, configuration)

    def summaries(self) -> list[dict[str, Any]]:
        summaries = []
        for patient_id in self.patient_ids():
            record = self.load_pristine(patient_id)
            patient = record["patient"]
            summaries.append(
                {
                    "patient_id": patient_id,
                    "first_name": patient["firstName"],
                    "last_name": patient["lastName"],
                    "date_of_birth": patient["birthdate"],
                    "gender": patient["gender"],
                    "cohort_group": self.cohort_group_for(patient_id),
                    "counts": {
                        entity: sum(
                            1
                            for item in values
                            if isinstance(item, dict) and item.get("endDate") is None
                        )
                        for entity, values in record.items()
                        if isinstance(values, list) and entity != "metadata"
                    },
                }
            )
        return summaries

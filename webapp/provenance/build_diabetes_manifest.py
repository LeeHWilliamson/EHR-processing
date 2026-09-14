"""Build reviewable diabetes ground-truth manifests from Synthea exports.

The native Synthea JSON export retains two things that the normalized records do
not: module execution history and the module-state name that created most record
entries.  This script uses those fields to identify clinical entries emitted by
the metabolic-syndrome modules on or before the Type II diabetes diagnosis.

It intentionally emits an empty relevant-entry set for condition-negative
patients.  That mirrors the tutorial's definition of the task: explain the path
to a confirmed Type II diabetes diagnosis, rather than assess general diabetes
risk or prediabetes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DIABETES_CODE = "44054006"
DIABETES_DISPLAY = "Diabetes mellitus type 2 (disorder)"
PROVENANCE_MODULES = (
    "Metabolic Syndrome Disease Progression Module",
    "Metabolic Syndrome Standards of Care Module",
)

NATIVE_COLLECTIONS = {
    "allergies": "allergies",
    "careplans": "careplans",
    "conditions": "conditions",
    "devices": "devices",
    "imagingStudies": "imaging_studies",
    "immunizations": "immunizations",
    "medications": "medications",
    "observations": "observations",
    "procedures": "procedures",
}

DATE_FIELDS = {
    "allergies": "startDate",
    "careplans": "startDate",
    "conditions": "startDate",
    "devices": "startDate",
    "imaging_studies": "date",
    "immunizations": "date",
    "medications": "startDate",
    "observations": "date",
    "procedures": "date",
}

DESCRIPTION_FIELDS = {
    "allergies": "description",
    "careplans": "description",
    "conditions": "description",
    "devices": "description",
    "imaging_studies": "bodysite",
    "immunizations": "description",
    "medications": "description",
    "observations": "description",
    "procedures": "description",
}


@dataclass(frozen=True)
class NativeEntry:
    entity: str
    encounter_uuid: str
    encounter_name: str | None
    state_name: str | None
    start: int | None
    uuid: str | None
    code: str | None
    description: str | None


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def iso_date(timestamp_ms: int | None) -> str | None:
    if timestamp_ms is None:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).date().isoformat()


def first_code(entry: dict[str, Any]) -> tuple[str | None, str | None]:
    for code in entry.get("codes", []):
        if isinstance(code, dict):
            return str(code.get("code")) if code.get("code") is not None else None, code.get("display")
    return None, None


def patient_uuid(normalized: dict[str, Any]) -> str:
    value = normalized["patient"]["id"]
    return value.removeprefix("pat_")


def find_native_file(native_dir: Path, patient_id: str) -> Path:
    matches = sorted(native_dir.glob(f"*_{patient_id}.json"))
    if len(matches) != 1:
        raise ValueError(f"Expected one native JSON for {patient_id}, found {len(matches)}")
    return matches[0]


def has_diabetes(normalized: dict[str, Any]) -> bool:
    return any(
        str(condition.get("code")) == DIABETES_CODE
        or condition.get("description") == DIABETES_DISPLAY
        for condition in normalized.get("conditions", [])
    )


def diagnosis_date(normalized: dict[str, Any]) -> str | None:
    dates = [
        condition.get("startDate")
        for condition in normalized.get("conditions", [])
        if str(condition.get("code")) == DIABETES_CODE
        or condition.get("description") == DIABETES_DISPLAY
    ]
    return min((date for date in dates if date), default=None)


def history_events(native: dict[str, Any], cutoff_ms: int) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    attributes = native.get("attributes", {})
    for module in PROVENANCE_MODULES:
        history = attributes.get(module, [])
        for event in history if isinstance(history, list) else []:
            entered = event.get("entered")
            if isinstance(entered, int) and entered <= cutoff_ms:
                events.append(
                    {
                        "module": module,
                        "state_name": event.get("state_name"),
                        "entered_ms": entered,
                        "entered_date": iso_date(entered),
                        "exited_ms": event.get("exited"),
                    }
                )
    return sorted(events, key=lambda item: (item["entered_ms"], item["module"], item["state_name"] or ""))


def diabetes_cutoff(native: dict[str, Any]) -> int | None:
    stage = native.get("attributes", {}).get("diabetes_stage")
    if not isinstance(stage, dict):
        return None
    code, display = first_code(stage)
    if code == DIABETES_CODE or display == DIABETES_DISPLAY:
        return stage.get("start")
    return None


def flatten_native_entries(native: dict[str, Any]) -> Iterable[NativeEntry]:
    for encounter in native.get("record", {}).get("encounters", []):
        encounter_uuid = encounter.get("uuid")
        for native_key, entity in NATIVE_COLLECTIONS.items():
            for entry in encounter.get(native_key, []):
                code, display = first_code(entry)
                yield NativeEntry(
                    entity=entity,
                    encounter_uuid=encounter_uuid,
                    encounter_name=encounter.get("name"),
                    state_name=entry.get("name"),
                    start=entry.get("start"),
                    uuid=entry.get("uuid"),
                    code=code,
                    description=display,
                )


def normalized_code(record: dict[str, Any]) -> str | None:
    value = record.get("code")
    if value is None:
        return None
    text = str(value)
    return text[:-2] if text.endswith(".0") else text


def candidate_score(native: NativeEntry, normalized: dict[str, Any]) -> int:
    score = 0
    normalized_encounter = str(normalized.get("encounter", "")).removeprefix("enc_")
    if native.encounter_uuid and normalized_encounter == native.encounter_uuid:
        score += 8
    if native.code and normalized_code(normalized) == native.code:
        score += 4
    description_field = DESCRIPTION_FIELDS[native.entity]
    if native.description and normalized.get(description_field) == native.description:
        score += 4
    date_field = DATE_FIELDS[native.entity]
    if iso_date(native.start) and str(normalized.get(date_field, ""))[:10] == iso_date(native.start):
        score += 2
    return score


def match_normalized_entry(
    native: NativeEntry,
    normalized: dict[str, Any],
    claimed: set[tuple[str, int]],
) -> tuple[dict[str, Any] | None, str, int, int]:
    candidates = []
    for index, record in enumerate(normalized.get(native.entity, [])):
        if (native.entity, index) in claimed:
            continue
        score = candidate_score(native, record)
        if score:
            candidates.append((score, index, record))
    if not candidates:
        return None, "unmatched", 0, 0
    candidates.sort(key=lambda item: item[0], reverse=True)
    best_score = candidates[0][0]
    best = [candidate for candidate in candidates if candidate[0] == best_score]
    if best_score < 10:
        return None, "low_confidence", best_score, len(best)
    if len(best) > 1:
        return None, "ambiguous", best_score, len(best)
    _, index, record = best[0]
    claimed.add((native.entity, index))
    return record, "matched", best_score, 1


def relevant_native_entries(native: dict[str, Any], events: list[dict[str, Any]], cutoff_ms: int) -> list[NativeEntry]:
    visited = {(event["state_name"], event["entered_ms"]) for event in events}
    return [
        entry
        for entry in flatten_native_entries(native)
        if entry.state_name
        and entry.start is not None
        and entry.start <= cutoff_ms
        and (entry.state_name, entry.start) in visited
    ]


def encounter_record(normalized: dict[str, Any], encounter_uuid: str) -> dict[str, Any] | None:
    expected = f"enc_{encounter_uuid}"
    return next((record for record in normalized.get("encounters", []) if record.get("id") == expected), None)


def summarize_record(entity: str, record: dict[str, Any]) -> dict[str, Any]:
    description_field = DESCRIPTION_FIELDS.get(entity, "description")
    date_field = DATE_FIELDS.get(entity, "startDate")
    return {
        "entity": entity,
        "id": record.get("id"),
        "date": record.get(date_field),
        "description": record.get(description_field),
        "code": normalized_code(record),
        "encounter": record.get("encounter"),
    }


def build_patient_manifest(native_path: Path, normalized_path: Path) -> dict[str, Any]:
    from .diabetes_evidence import build_hybrid_classification

    native = load_json(native_path)
    normalized = load_json(normalized_path)
    patient_id = patient_uuid(normalized)
    positive = has_diabetes(normalized)
    cutoff_ms = diabetes_cutoff(native) if positive else None

    if positive and cutoff_ms is None:
        return {
            "patient_id": patient_id,
            "name": f'{normalized["patient"]["firstName"]} {normalized["patient"]["lastName"]}',
            "has_type_2_diabetes": True,
            "status": "error",
            "errors": ["Normalized record is positive but native diabetes diagnosis stage was not found."],
        }

    events = history_events(native, cutoff_ms) if cutoff_ms is not None else []
    native_entries = relevant_native_entries(native, events, cutoff_ms) if cutoff_ms is not None else []
    claimed: set[tuple[str, int]] = set()
    relevant_records: list[dict[str, Any]] = []
    mappings: list[dict[str, Any]] = []
    encounter_ids: set[str] = set()

    for native_entry in native_entries:
        record, status, score, candidate_count = match_normalized_entry(native_entry, normalized, claimed)
        mapping = {
            "entity": native_entry.entity,
            "state_name": native_entry.state_name,
            "entered_ms": native_entry.start,
            "date": iso_date(native_entry.start),
            "native_uuid": native_entry.uuid,
            "encounter_uuid": native_entry.encounter_uuid,
            "description": native_entry.description,
            "code": native_entry.code,
            "status": status,
            "match_score": score,
            "top_candidate_count": candidate_count,
            "normalized_id": record.get("id") if record else None,
        }
        mappings.append(mapping)
        if record:
            relevant_records.append(summarize_record(native_entry.entity, record))
            encounter_ids.add(native_entry.encounter_uuid)

    for encounter_id in sorted(encounter_ids):
        record = encounter_record(normalized, encounter_id)
        if record:
            relevant_records.append(
                {
                    "entity": "encounters",
                    "id": record.get("id"),
                    "date": record.get("startDate"),
                    "description": record.get("description"),
                    "code": normalized_code(record),
                    "encounter": None,
                }
            )

    mapping_counts = Counter(mapping["status"] for mapping in mappings)
    hybrid = build_hybrid_classification(normalized, diagnosis_date(normalized) if positive else None)
    return {
        "patient_id": patient_id,
        "name": f'{normalized["patient"]["firstName"]} {normalized["patient"]["lastName"]}',
        "has_type_2_diabetes": positive,
        "diagnosis": {
            "code": DIABETES_CODE,
            "display": DIABETES_DISPLAY,
            "date": diagnosis_date(normalized),
            "native_timestamp_ms": cutoff_ms,
        } if positive else None,
        "status": "review_required" if any(key != "matched" for key in mapping_counts) else "ready",
        "module_history": events,
        "clinical_entry_mappings": mappings,
        "causal_records": sorted(
            relevant_records,
            key=lambda record: (record.get("date") or "", record["entity"], record.get("description") or ""),
        ),
        # Deprecated compatibility alias for the first prototype.
        "relevant_records": sorted(
            relevant_records,
            key=lambda record: (record.get("date") or "", record["entity"], record.get("description") or ""),
        ),
        **hybrid,
        "counts": {
            "module_transitions": len(events),
            "native_clinical_entries": len(native_entries),
            "matched_clinical_entries": mapping_counts["matched"],
            "relevant_normalized_records": len(relevant_records),
            "mapping_statuses": dict(sorted(mapping_counts.items())),
            "relevant_records_by_entity": dict(sorted(Counter(r["entity"] for r in relevant_records).items())),
            "decision_input_records": len(hybrid["decision_input_records"]),
            "diagnostic_evidence_records": len(hybrid["diagnostic_evidence_records"]),
            "leakage_records": len(hybrid["leakage_records"]),
            "decision_evidence_overlap": len(hybrid["decision_evidence_overlap"]),
        },
        "source": {
            "native_json": native_path.name,
            "normalized_json": normalized_path.name,
            "native_sha256": hashlib.sha256(native_path.read_bytes()).hexdigest(),
            "normalized_sha256": hashlib.sha256(normalized_path.read_bytes()).hexdigest(),
        },
    }


def markdown_report(manifests: list[dict[str, Any]]) -> str:
    positives = sum(manifest["has_type_2_diabetes"] for manifest in manifests)
    ready = sum(manifest.get("status") == "ready" for manifest in manifests)
    lines = [
        "# Diabetes provenance review",
        "",
        "This report combines native Synthea provenance with an explicit, diabetes-specific clinical evidence rubric.",
        "It is an answer-key prototype for human review, not a clinical diagnostic standard.",
        "",
        "## Cohort summary",
        "",
        f"- Patients: {len(manifests)}",
        f"- Type II diabetes positive: {positives}",
        f"- Type II diabetes negative: {len(manifests) - positives}",
        f"- Manifests with all native clinical entries mapped: {ready}/{len(manifests)}",
        "",
        "| Patient | Label | Diagnosis date | Causal | Decision inputs | Clinical evidence | Overlap | Leakage | Status |",
        "|---|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for manifest in manifests:
        diagnosis = manifest.get("diagnosis") or {}
        counts = manifest.get("counts", {})
        lines.append(
            f'| {manifest["name"]} | {"positive" if manifest["has_type_2_diabetes"] else "negative"} '
            f'| {diagnosis.get("date") or "—"} | {counts.get("relevant_normalized_records", 0)} '
            f'| {counts.get("decision_input_records", 0)} | {counts.get("diagnostic_evidence_records", 0)} '
            f'| {counts.get("decision_evidence_overlap", 0)} | {counts.get("leakage_records", 0)} '
            f'| {manifest.get("status", "error")} |'
        )

    lines.extend([
        "",
        "## Interpretation rules",
        "",
        f"- A positive label requires condition code `{DIABETES_CODE}` or the exact display `{DIABETES_DISPLAY}` in the pristine normalized record.",
        "- Negative patients have zero causal records by task definition, but can have decision-input and clinical-evidence records.",
        "- For positive patients, module transitions come from the disease-progression and standards-of-care histories through the diagnosis timestamp.",
        "- A causal clinical entry is one whose native state name and timestamp match a visited module state.",
        "- The encounter containing each matched entry is also included because an agent may need to retrieve it to navigate the record.",
        "- Decision inputs are records corresponding to values read by the inspected Synthea modules; clinical evidence comes from the versioned diabetes rubric.",
        "- Leakage records explicitly disclose the target diagnosis and should be censored before an agent run.",
        "- Every native-to-normalized match is recorded in the per-patient JSON manifest for review.",
        "",
        "## Patient details",
        "",
    ])
    for manifest in manifests:
        lines.extend([
            f'### {manifest["name"]}',
            "",
            f'- Patient ID: `{manifest["patient_id"]}`',
            f'- Ground truth: **{"Type II diabetes positive" if manifest["has_type_2_diabetes"] else "Type II diabetes negative"}**',
            f'- Status: `{manifest.get("status", "error")}`',
        ])
        counts = manifest["counts"]
        lines.extend([
            f'- Diagnosis date: {(manifest.get("diagnosis") or {}).get("date") or "—"}',
            f'- Mapping statuses: `{json.dumps(counts["mapping_statuses"], sort_keys=True)}`',
            f'- Causal records by entity: `{json.dumps(counts["relevant_records_by_entity"], sort_keys=True)}`',
            f'- Decision inputs: {counts["decision_input_records"]}',
            f'- Clinical evidence: {counts["diagnostic_evidence_records"]}',
            f'- Decision/evidence overlap: {counts["decision_evidence_overlap"]}',
            f'- Leakage records: {counts["leakage_records"]}',
            "",
            "#### Causal records",
            "",
        ])
        if manifest["clinical_entry_mappings"]:
            lines.extend(["| Date | Entity | Synthea state | Description | Mapping |", "|---|---|---|---|---|"])
            for mapping in manifest["clinical_entry_mappings"]:
                description = (mapping.get("description") or "—").replace("|", "\\|")
                lines.append(
                    f'| {mapping.get("date") or "—"} | {mapping["entity"]} '
                    f'| `{mapping.get("state_name") or "—"}` | {description} | {mapping["status"]} |'
                )
        else:
            lines.append("None by task definition.")
        for title, key in (
            ("Decision-input records", "decision_input_records"),
            ("Clinical evidence records", "diagnostic_evidence_records"),
            ("Target-leakage records", "leakage_records"),
        ):
            lines.extend(["", f"#### {title}", "", "| Date | Entity | Class | Description | Value | Rule |", "|---|---|---|---|---|---|"])
            records = manifest[key]
            if not records:
                lines.append("| — | — | — | None | — | — |")
            for record in records:
                description = str(record.get("description") or "—").replace("|", "\\|")
                value = str(record.get("value") if record.get("value") is not None else "—").replace("|", "\\|")
                lines.append(
                    f'| {record.get("date") or "—"} | {record["entity"]} | {record["classification"]} '
                    f'| {description} | {value} | `{record["rule_id"]}` |'
                )
        lines.append("")
    return "\n".join(lines) + "\n"


def build_all(data_dir: Path, output_dir: Path) -> list[dict[str, Any]]:
    native_dir = data_dir / "json"
    normalized_dir = data_dir / "normalized_json"
    normalized_paths = sorted(normalized_dir.glob("*.json"))
    if not normalized_paths:
        raise ValueError(f"No normalized patient JSON files found in {normalized_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    manifests = []
    for normalized_path in normalized_paths:
        normalized = load_json(normalized_path)
        patient_id = patient_uuid(normalized)
        native_path = find_native_file(native_dir, patient_id)
        manifest = build_patient_manifest(native_path, normalized_path)
        manifests.append(manifest)
        destination = output_dir / f"{patient_id}.json"
        destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    (output_dir / "review.md").write_text(markdown_report(manifests), encoding="utf-8")
    return manifests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("webapp/patients/current_run/full_patients"),
        help="Directory containing json/ and normalized_json/",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("webapp/patients/current_run/full_patients/provenance"),
        help="Destination for per-patient manifests and review.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifests = build_all(args.data_dir, args.output_dir)
    positives = sum(manifest["has_type_2_diabetes"] for manifest in manifests)
    review_required = sum(manifest.get("status") != "ready" for manifest in manifests)
    print(f"Built {len(manifests)} manifests ({positives} positive, {review_required} requiring review)")
    print(args.output_dir / "review.md")


if __name__ == "__main__":
    main()

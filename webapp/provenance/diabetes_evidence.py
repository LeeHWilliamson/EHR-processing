"""Transparent, diabetes-specific evidence and leakage classification."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .build_diabetes_manifest import DATE_FIELDS, DESCRIPTION_FIELDS, normalized_code


RULES_PATH = Path(__file__).with_name("diabetes_evidence_rules.json")


def load_rules(path: Path = RULES_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def record_date(entity: str, record: dict[str, Any]) -> str | None:
    field = DATE_FIELDS.get(entity)
    if field:
        value = record.get(field)
        return str(value)[:10] if value else None
    return None


def before_or_on(record_date_value: str | None, cutoff_date: str | None) -> bool:
    return cutoff_date is None or record_date_value is None or record_date_value <= cutoff_date


def record_text(record: dict[str, Any], fields: list[str]) -> str:
    return " ".join(str(record.get(field) or "") for field in fields).lower()


def rule_matches(entity: str, record: dict[str, Any], rule: dict[str, Any]) -> bool:
    if rule.get("entity") and rule["entity"] != entity:
        return False
    if rule.get("entities") and entity not in rule["entities"]:
        return False
    if rule.get("codes") and normalized_code(record) not in set(rule["codes"]):
        return False
    fragments = rule.get("description_contains_any")
    if fragments:
        description = str(record.get(DESCRIPTION_FIELDS.get(entity, "description")) or "").lower()
        if not any(fragment.lower() in description for fragment in fragments):
            return False
    fragments = rule.get("contains_any")
    if fragments:
        text = record_text(record, rule.get("fields", ["description"]))
        if not any(fragment.lower() in text for fragment in fragments):
            return False
    patterns = rule.get("regex_any")
    if patterns:
        text = record_text(record, rule.get("fields", ["description"]))
        if not any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            return False
    return True


def classified_record(
    entity: str,
    record: dict[str, Any],
    rule: dict[str, Any],
    classification: str,
) -> dict[str, Any]:
    description_field = DESCRIPTION_FIELDS.get(entity, "description")
    result = {
        "entity": entity,
        "id": record.get("id"),
        "date": record_date(entity, record),
        "description": record.get(description_field),
        "code": normalized_code(record),
        "value": record.get("value"),
        "units": record.get("units"),
        "encounter": record.get("encounter"),
        "classification": classification,
        "rule_id": rule["id"],
        "rationale": rule["rationale"],
    }
    if classification == "target_leakage":
        patterns = rule.get("regex_any", [])
        matching_fields = [
            field for field in rule.get("fields", [])
            if any(re.search(pattern, str(record.get(field) or ""), flags=re.IGNORECASE) for pattern in patterns)
        ]
        result["action"] = rule.get("action", "review")
        result["matching_fields"] = matching_fields
    return result


def apply_selection(records: list[dict[str, Any]], rule: dict[str, Any]) -> list[dict[str, Any]]:
    selection = rule.get("selection", {})
    selected = records
    if selection.get("active_only"):
        selected = [record for record in selected if record.get("_end_date") is None]

    group_field = None
    limit = None
    if selection.get("latest_per_code"):
        group_field = "code"
        limit = selection["latest_per_code"]
    elif selection.get("latest_per_description"):
        group_field = "description"
        limit = selection["latest_per_description"]
    if group_field and limit:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for record in selected:
            grouped.setdefault(str(record.get(group_field)), []).append(record)
        selected = []
        for group in grouped.values():
            group.sort(key=lambda item: item.get("date") or "", reverse=True)
            selected.extend(group[:limit])
    for record in selected:
        record.pop("_end_date", None)
    return selected


def classify_records(
    normalized: dict[str, Any],
    rules: list[dict[str, Any]],
    classification_key: str,
    cutoff_date: str | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None, str]] = set()
    for rule in rules:
        entities = [rule["entity"]] if rule.get("entity") else rule.get("entities", [])
        rule_results: list[dict[str, Any]] = []
        for entity in entities:
            for record in normalized.get(entity, []):
                if not before_or_on(record_date(entity, record), cutoff_date):
                    continue
                if not rule_matches(entity, record, rule):
                    continue
                key = (entity, record.get("id"), rule["id"])
                if key not in seen:
                    classified = classified_record(entity, record, rule, rule.get("class", classification_key))
                    classified["_end_date"] = record.get("endDate")
                    rule_results.append(classified)
                    seen.add(key)
        results.extend(apply_selection(rule_results, rule))
    return sorted(results, key=lambda item: (item.get("date") or "", item["entity"], item.get("description") or ""))


def decision_input_records(
    normalized: dict[str, Any],
    cutoff_date: str | None,
    rules: dict[str, Any],
) -> list[dict[str, Any]]:
    records = classify_records(normalized, rules["decision_inputs"], "decision_input", cutoff_date)
    patient = normalized["patient"]
    # The disease-progression module explicitly evaluates age and race. Veteran
    # status also affects a branch, but it is not retained by the normalized schema.
    demographics = [
        {
            "entity": "patient",
            "id": patient.get("id"),
            "date": patient.get("birthdate"),
            "description": "Date of birth",
            "code": None,
            "value": patient.get("birthdate"),
            "units": None,
            "encounter": None,
            "classification": "decision_input",
            "rule_id": "synthea-age-input",
            "rationale": "The Synthea disease-progression module uses age guards and age-based delays.",
        },
        {
            "entity": "patient",
            "id": patient.get("id"),
            "date": None,
            "description": "Race",
            "code": None,
            "value": patient.get("race"),
            "units": None,
            "encounter": None,
            "classification": "decision_input",
            "rule_id": "synthea-race-input",
            "rationale": "The Synthea disease-progression module uses race in its prevalence transition.",
        },
    ]
    return demographics + records


def merge_leakage(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str | None], dict[str, Any]] = {}
    for record in records:
        key = (record["entity"], record.get("id"))
        if key not in merged:
            item = dict(record)
            item["rule_ids"] = [item.pop("rule_id")]
            merged[key] = item
            continue
        item = merged[key]
        item["rule_ids"].append(record["rule_id"])
        item["matching_fields"] = sorted(set(item.get("matching_fields", [])) | set(record.get("matching_fields", [])))
        if record.get("action") == "remove_record":
            item["action"] = "remove_record"
            item["rationale"] = record["rationale"]
    for item in merged.values():
        item["rule_id"] = ", ".join(item.pop("rule_ids"))
    return sorted(merged.values(), key=lambda item: (item.get("date") or "", item["entity"], item.get("description") or ""))


def build_hybrid_classification(normalized: dict[str, Any], cutoff_date: str | None) -> dict[str, Any]:
    rules = load_rules()
    decision = decision_input_records(normalized, cutoff_date, rules)
    # Clinical evidence answers what the agent can use at the end of the record,
    # including monitoring data after the original diagnosis. The Synthea causal
    # and decision-input traces retain the diagnosis cutoff separately.
    evidence = classify_records(normalized, rules["clinical_evidence"], "clinical_evidence", None)
    leakage = merge_leakage(classify_records(normalized, rules["leakage"], "target_leakage", None))
    decision_ids = {(item["entity"], item["id"]) for item in decision}
    evidence_ids = {(item["entity"], item["id"]) for item in evidence}
    overlap = sorted(
        decision_ids & evidence_ids,
        key=lambda item: (item[0], item[1] or ""),
    )
    return {
        "decision_input_records": decision,
        "diagnostic_evidence_records": evidence,
        "leakage_records": leakage,
        "decision_evidence_overlap": [
            {"entity": entity, "id": record_id} for entity, record_id in overlap
        ],
        "limitations": [
            "Decision-input rules cover the inspected metabolic-syndrome modules but do not yet perform a general transitive source-code dependency trace.",
            "Veteran status is read by Synthea but is absent from the normalized patient schema.",
            "Clinical evidence rules are diabetes-specific and require human review.",
            "Glucose records do not reliably state whether the patient was fasting, so fasting-plasma-glucose criteria cannot be inferred from value alone.",
        ],
        "rules": {
            "version": rules["version"],
            "scope": rules["scope"],
            "source": RULES_PATH.name,
        },
    }

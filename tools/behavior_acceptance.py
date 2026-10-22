"""Structural authority and original-case checks, never inferred business approval."""

from __future__ import annotations

from typing import Any

from target_validation_support import is_unresolved_value, is_placeholder
from repair_classification import classify_repairs


BUSINESS_RISKS = frozenset({"business-rule", "business-policy", "business-logic"})


def resolved(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not is_placeholder(value) and not is_unresolved_value(value)


def behavior_failures(model: dict[str, Any], *, completion: bool = False) -> list[str]:
    review = model.get("behavior_review")
    if not isinstance(review, dict):
        return ["behavior_review must record applicability and authority"]
    failures = []
    risks = model.get("risk_classes", [])
    business = isinstance(risks, list) and any(isinstance(risk, str) and risk in BUSINESS_RISKS for risk in risks)
    if not resolved(review.get("reason")):
        failures.append("behavior_review requires a concrete applicability reason")
    required = review.get("required") is True
    if business and not required:
        failures.append("business-rule changes require a behavior review")
    deltas = review.get("deltas")
    if not isinstance(deltas, list):
        return failures + ["behavior_review.deltas must be an array"]
    if required and not deltas:
        failures.append("required behavior review needs per-fact behavior deltas")
    if not required and deltas:
        failures.append("behavior deltas cannot be hidden behind a non-required review")
    facts = {item.get("id") for item in model.get("changed_facts", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
    seen = set()
    for delta in deltas:
        if not isinstance(delta, dict):
            failures.append("behavior delta must be an object")
            continue
        fact = delta.get("fact_id")
        if not isinstance(fact, str) or fact not in facts or fact in seen:
            failures.append("behavior delta must uniquely bind a changed fact")
        else:
            seen.add(fact)
        if delta.get("authority_status") == "approved":
            if delta.get("authority_kind") not in ("canonical-source", "owner-decision"):
                failures.append("an inference, plan, implementation or test cannot supply business approval")
            for field in ("authority_ref", "decision_owner", "before", "after", "scope"):
                if not resolved(delta.get(field)):
                    failures.append(f"approved behavior delta requires resolved {field}")
            if not delta.get("evidence_refs"):
                failures.append("approved behavior delta requires authority evidence")
        elif completion:
            failures.append(f"behavior authority remains unresolved for {fact!r}")
    if business and facts - seen:
        failures.append("business review omits changed facts: " + ", ".join(sorted(facts - seen)))
    failures.extend(original_case_failures(model, completion=completion))
    failures.extend(classify_repairs(model, completion=completion).failures)
    return failures


def original_case_failures(model: dict[str, Any], *, completion: bool) -> list[str]:
    case = model.get("original_case")
    incident = model.get("incident")
    repair = isinstance(incident, dict) and incident.get("mode") != "none"
    if case is None:
        return ["incident repair must retain its source-derived original case"] if repair else []
    if not isinstance(case, dict):
        return ["original_case must be an object or null"]
    failures = []
    for field in ("source_ref", "actor", "input", "expected_outcome"):
        if not resolved(case.get(field)):
            failures.append(f"original_case requires resolved {field}")
    status = case.get("status")
    if status in ("verified-fixed", "superseded-by-owner-decision") and not case.get("evidence_refs"):
        failures.append("original-case acceptance requires observable or owner-decision evidence")
    supersession = case.get("supersession")
    if status == "superseded-by-owner-decision":
        if not isinstance(supersession, dict) or any(not resolved(supersession.get(field)) for field in ("source_ref", "decision_owner", "reason")):
            failures.append("superseded original case requires an explicit scoped owner decision")
    elif supersession is not None:
        failures.append("supersession cannot relabel an unchanged original-case expectation")
    if completion and status not in ("verified-fixed", "superseded-by-owner-decision"):
        failures.append("original complaint is not accepted: " + str(status))
    return failures

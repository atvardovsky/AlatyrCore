"""One restoration classifier shared by model validation and repair routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from target_adapter_validation.values import is_resolved_string


@dataclass(frozen=True)
class RepairClassification:
    incident_required: bool
    failures: tuple[str, ...]


def classify_repairs(model: dict[str, Any], *, completion: bool = False) -> RepairClassification:
    incident = model.get("incident")
    incident = incident if isinstance(incident, dict) else {}
    systemic = incident.get("mode") == "systemic-repair" or incident.get("trigger") in ("escaped-defect", "failed-required-gate", "recurring-correction")
    uncertain = model.get("primary_strategy_id") == "hypothesis-driven" or systemic
    failures = []
    if model.get("schema_version") != 6:
        return RepairClassification(uncertain, ())
    review = model.get("behavior_review")
    deltas = review.get("deltas", []) if isinstance(review, dict) else []
    if not isinstance(deltas, list):
        return RepairClassification(uncertain, ("behavior deltas must be an array",))
    collections = {}
    for field in ("invariants", "proof_obligations"):
        items = model.get(field)
        if not isinstance(items, list) or any(not isinstance(item, dict) or not isinstance(item.get("id"), str) for item in items):
            failures.append(f"repair {field} must be an array of identified objects")
            collections[field] = {}
        else:
            collections[field] = {item["id"]: item for item in items}
    invariants, proofs = collections["invariants"], collections["proof_obligations"]
    for delta in deltas:
        if not isinstance(delta, dict):
            continue
        repair = delta.get("repair")
        if delta.get("effect") != "restore":
            if repair is not None:
                failures.append("repair classification is only valid for a restoring delta")
            continue
        if not isinstance(repair, dict):
            failures.append(f"restoring fact {delta.get('fact_id')!r} requires explicit repair classification")
            continue
        kind = repair.get("kind")
        if not isinstance(kind, str) or kind not in {"settled-correction", "incident-repair", "reviewed-non-defect"}:
            failures.append("repair kind must be settled-correction, incident-repair or reviewed-non-defect")
            continue
        allowed = {"kind", "source_refs", "invariant_ids", "proof_obligation_ids", "reason"}
        if set(repair) != allowed or not is_resolved_string(repair.get("reason")):
            failures.append("repair classification needs its exact fields and a concrete reason")
        lists = {}
        for field in ("source_refs", "invariant_ids", "proof_obligation_ids"):
            value = repair.get(field)
            if not isinstance(value, list) or not 1 <= len(value) <= 64 or not all(is_resolved_string(item) for item in value) or len(value) != len(set(value)):
                failures.append(f"repair {field} requires 1..64 unique resolved references")
            else:
                lists[field] = value
        for identifier in lists.get("invariant_ids", []):
            invariant = invariants.get(identifier)
            if invariant is None or invariant.get("status") not in ("required", "preserved") or not is_resolved_string(invariant.get("owner_ref")):
                failures.append(f"repair invariant {identifier!r} must resolve to an accepted required/preserved invariant owner")
        for identifier in lists.get("proof_obligation_ids", []):
            proof = proofs.get(identifier)
            if proof is None or proof.get("required") is not True:
                failures.append(f"repair proof {identifier!r} must resolve to a required obligation")
            elif completion and (proof.get("status") != "passed" or not proof.get("evidence_refs")):
                failures.append(f"repair proof {identifier!r} needs passed evidence at completion; waiver is not restoration proof")
        if kind == "incident-repair":
            uncertain = True
            if incident.get("mode") in (None, "none"):
                failures.append("incident repair cannot discard its incident identity and original case")
        elif systemic:
            failures.append("systemic incident requirements cannot be relabeled as a settled/non-defect restoration")
    return RepairClassification(uncertain, tuple(failures))

"""Outcome qualification inside the existing model, not an acceptance authority."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from target_validation_support import is_target_relative_path
from target_adapter_validation.values import is_resolved_string


CASE_FIELDS = ("id", "source_ref", "oracle", "expected_result", "rejected_substitute",
               "scope", "evidence_class", "proof_obligation_ids")
ORIGINAL_FIELDS = ("source_ref", "actor", "input", "expected_outcome")


def original_binding(model: dict) -> dict | None:
    original = model.get("original_case")
    return {key: original[key] for key in ORIGINAL_FIELDS} if isinstance(original, dict) else None


def captured_case(model: dict, case: dict) -> dict:
    proofs = {row["id"]: row["statement"] for row in model["proof_obligations"]}
    return {"original_case": original_binding(model),
        "case": {key: case[key] for key in CASE_FIELDS},
        "proofs": {key: proofs.get(key) for key in case["proof_obligation_ids"]}}


def case_binding(model: dict, case: dict) -> str:
    binding = {"model_id": model["model_id"], "operation_id": model["operation_id"],
        "repository_binding": model["repository_binding"], "task_binding": model["task_binding"],
        **captured_case(model, case)}
    return hashlib.sha256(json.dumps(binding, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def checks(model: dict) -> list[dict]:
    block = model.get("analysis_evidence")
    return block.get("outcome_checks", []) if isinstance(block, dict) else []


def supersession_binding_failures(model: dict) -> list[str]:
    original = model.get("original_case")
    if not checks(model) or not isinstance(original, dict) or original.get("status") != "superseded-by-owner-decision":
        return []
    decision = original.get("supersession")
    changes = decision.get("outcome_changes", []) if isinstance(decision, dict) else []
    ids = [row["case_id"] for row in changes]
    if not ids or len(ids) != len(set(ids)) or not set(ids).issubset({row["id"] for row in checks(model)}):
        return ["outcome supersession requires unique known case IDs and exact before/after digests"]
    paths = {row["path"] for row in model.get("analysis_evidence", {}).get("selected_context", [])}
    if decision["source_ref"] not in paths or decision["source_ref"] not in original["evidence_refs"]:
        return ["outcome supersession requires a digest-bound selected-context decision cited by the original case"]
    return []


def outcome_failures(model: dict, *, completion: bool = False, selected_id: str | None = None) -> list[str]:
    """Inputs are schema-validated; a supported declaration is not semantic proof."""
    rows = checks(model)
    if not rows:
        return []
    failures = supersession_binding_failures(model)
    if len({row["id"] for row in rows}) != len(rows):
        failures.append("outcome checks require unique IDs")
    proofs = {row["id"]: row for row in model["proof_obligations"]}
    original = model.get("original_case")
    for case in rows:
        identity = case["id"]
        if selected_id is not None and identity != selected_id:
            continue
        if any(not is_resolved_string(case[key]) for key in ("id", "source_ref", "expected_result", "rejected_substitute")):
            failures.append(f"outcome {identity} requires resolved source and expected/rejected results")
        if any(not is_resolved_string(case["scope"][key]) for key in ("actor", "system", "entrypoint", "conditions")):
            failures.append(f"outcome {identity} requires resolved scope bindings")
        ids = case["proof_obligation_ids"]
        if any(key not in proofs or proofs[key]["required"] is not True for key in ids):
            failures.append(f"outcome {identity} must bind known required proof obligations")
        if isinstance(original, dict) and case["source_ref"] != original["source_ref"]:
            failures.append(f"outcome {identity} must retain the original request source")
        for path in case["scope"]["surfaces"]:
            if not is_target_relative_path(path) or "\\" in path:
                failures.append(f"outcome {identity} requires exact target-relative surfaces")
        observation = case["observation"]
        qualified = []
        if observation is None:
            qualified.append("original outcome is unobserved")
        else:
            if not is_resolved_string(observation["actual_result"]):
                failures.append(f"outcome {identity} requires a resolved actual observation")
            if observation["case_sha256"] != case_binding(model, case):
                failures.append(f"outcome {identity} observation has a stale oracle/case binding")
            if set(observation["input_sha256"]) != set(observation["scope"]["surfaces"]):
                failures.append(f"outcome {identity} observation requires exact observed surface digests")
            if observation["scope"] != case["scope"]:
                qualified.append("observed actor/system/entrypoint/conditions/surfaces differ")
            if observation["evidence_class"] != case["evidence_class"]:
                qualified.append("component or synthetic evidence cannot replace the required evidence class")
            if observation["status"] != "supported":
                qualified.append("original outcome is contradicted or inconclusive")
            if observation["decisive_check_reached"] is not True:
                qualified.append("decisive outcome check was not reached")
            artifacts = {row["path"] for row in observation["artifacts"]}
            if case["oracle"]["path"] in artifacts:
                failures.append(f"outcome {identity} requires observation evidence distinct from its oracle")
            for key in ids:
                if key in proofs and proofs[key]["status"] == "passed" and not artifacts.intersection(proofs[key]["evidence_refs"]):
                    failures.append(f"outcome {identity} passed proof {key} must cite its observation artifact")
        if completion or any(proofs[key]["status"] == "passed" for key in ids if key in proofs):
            failures.extend(f"outcome {identity}: {message}" for message in qualified)
        if completion and any(key not in proofs or proofs[key]["status"] != "passed" for key in ids):
            failures.append(f"outcome {identity} requires passed, not waived, original-outcome proofs")
    return failures


def request_outcome_failures(brief: dict, model: dict) -> list[str]:
    """Declared request rows, not an implementation plan, own captured coverage."""
    rows = {row["id"]: row for row in checks(model)}
    failures = []
    for outcome in brief["outcomes"]:
        case = rows.get(outcome["id"])
        if case is None:
            failures.append(f"requested outcome {outcome['id']} has no captured outcome check")
        elif (case["source_ref"] != brief["source_ref"] or case["expected_result"] != outcome["statement"]
                or case["rejected_substitute"] != outcome["rejection_case"]
                or set(case["proof_obligation_ids"]) != set(outcome["proof_obligation_ids"])):
            failures.append(f"outcome {outcome['id']} differs from the source request's expectation, rejected substitute or proofs")
    return failures


def artifact_bindings(model: dict) -> list[tuple[str, str]]:
    result = []
    for case in checks(model):
        result.append((case["oracle"]["path"], case["oracle"]["sha256"]))
        observation = case["observation"]
        if observation is not None:
            result.extend(observation["input_sha256"].items())
            result.extend((row["path"], row["sha256"]) for row in observation["artifacts"])
    return result


def retained_bindings(model: dict) -> list[tuple[str, str]]:
    result = []
    for case in checks(model):
        result.append((case["oracle"]["path"], case["oracle"]["sha256"]))
        if case["observation"] is not None:
            result.extend((row["path"], row["sha256"]) for row in case["observation"]["artifacts"])
    original = model.get("original_case")
    decision = original.get("supersession") if isinstance(original, dict) else None
    if isinstance(decision, dict) and "outcome_changes" in decision:
        result.extend((row["path"], row["sha256"]) for row in model.get("analysis_evidence", {}).get("selected_context", [])
                      if row["path"] == decision["source_ref"])
    return result


def retention_failures(model: dict, is_ignored) -> list[str]:
    return supersession_binding_failures(model) + [f"outcome oracle/result must be retainable historical evidence, not ignored runtime: {path}"
            for path in sorted({path for path, _ in retained_bindings(model)}) if is_ignored(path) is not False]


def supersession_artifact_failures(model: dict, path: str, raw: bytes) -> list[str]:
    original = model.get("original_case")
    decision = original.get("supersession") if isinstance(original, dict) else None
    if not isinstance(decision, dict) or "outcome_changes" not in decision or path != decision["source_ref"]:
        return []
    from inspect_session_context import json_object
    try:
        document = json_object(raw, "outcome supersession decision")
    except (ValueError, RecursionError) as exc:
        return [f"outcome supersession decision requires structured scope: {exc}"]
    if document.get("outcome_changes") != decision["outcome_changes"] or document.get("decision_owner") != decision["decision_owner"]:
        return ["outcome supersession scope/owner differs from its bound decision artifact"]
    return []


def capture_failures(previous: dict, current: dict) -> list[str]:
    replacements = {row["id"]: row for row in checks(current)}
    failures = [f"captured outcome {row['id']} oracle/scope cannot be removed or rewritten; retain it in an explicitly reviewed successor"
            for row in checks(previous) if row["id"] not in replacements
            or captured_case(current, replacements[row["id"]]) != captured_case(previous, row)]
    if checks(previous) and original_binding(previous) != original_binding(current):
        failures.append("captured outcome original-case source/actor/input/expectation cannot be rewritten; use an explicitly reviewed successor")
    return failures


def revision_failures(previous: dict, current: dict) -> list[str]:
    failures = capture_failures(previous, current)
    old = previous.get("original_case")
    new = current.get("original_case")
    if (isinstance(old, dict) and old.get("supersession") is not None
            and old["supersession"] != (new.get("supersession") if isinstance(new, dict) else None)):
        failures.append("captured outcome supersession decision cannot be removed or rewritten; use a reviewed successor")
    return failures


def inherited_failures(previous: dict, current: dict) -> list[str]:
    """Same-incident successors retain captures; owner supersession is explicit."""
    failures = capture_failures(previous, current)
    if not failures:
        return []
    replacements = {row["id"]: row for row in checks(current)}
    if any(row["id"] not in replacements for row in checks(previous)):
        return failures
    original = current.get("original_case")
    decision = original.get("supersession") if isinstance(original, dict) else None
    if not isinstance(decision, dict) or original.get("status") != "superseded-by-owner-decision":
        return failures
    if (supersession_binding_failures(current)
            or not all(is_resolved_string(decision.get(key)) for key in ("decision_owner", "reason"))):
        return failures
    changes = decision.get("outcome_changes", [])
    by_id = {row["case_id"]: row for row in changes}
    for case in checks(previous):
        replacement = replacements[case["id"]]
        if captured_case(current, replacement) != captured_case(previous, case):
            expected = {"case_id": case["id"], "predecessor_sha256": case_binding(previous, case),
                        "replacement_sha256": case_binding(current, replacement)}
            if by_id.get(case["id"]) != expected:
                return failures
    return []


def active_checks(model: dict) -> list[dict[str, Any]]:
    result = []
    for row in checks(model):
        failures = outcome_failures(model, completion=True, selected_id=row["id"])
        result.append({"id": row["id"], "evidence_class": row["evidence_class"],
            "proof_obligation_ids": row["proof_obligation_ids"], "case_sha256": case_binding(model, row),
            "qualification": "record-consistent-not-semantic-proof" if not failures else "unverified",
            "diagnostics": failures[:3]})
    return result

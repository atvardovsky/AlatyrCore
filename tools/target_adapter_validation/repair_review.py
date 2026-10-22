"""Lazy, current-incident repair evidence through canonical testing validation."""

from __future__ import annotations

import json
import hashlib
from typing import Any

from repair_review import evidence_failures
from test_execution_contract import TestExecutionContract
from target_adapter_validation.testing_execution import validate_testing_execution
from target_validation_support import is_target_relative_path

POLICY = ".ai/project/testing/test-first-policy.json"
OBLIGATION = "repair-evidence-review"
MAX_RECORD_BYTES = 128 * 1024


def _bound_json(validator: Any, path: str, digest: str | None = None) -> dict[str, Any] | None:
    if not is_target_relative_path(path) or not validator.is_target_file(path):
        validator.error("TDD_EXECUTION_EVIDENCE", "repair evidence path is unavailable or outside the target", path)
        return None
    raw = validator.context.read_bytes_result(validator.target_path(path), max_bytes=MAX_RECORD_BYTES)
    if raw.value is None or digest is not None and hashlib.sha256(raw.value).hexdigest() != digest:
        validator.error("TDD_EXECUTION_EVIDENCE_STALE", "repair evidence digest is stale or the bounded record is unavailable", path)
        return None
    return validator.load_json_object(validator.target_path(path), "TDD_EXECUTION_EVIDENCE")


def validate_task_repair_review(validator: Any, task: dict[str, Any], model: dict[str, Any], *, completion: bool) -> None:
    incident = model.get("incident", {})
    obligations = [item for item in model.get("proof_obligations", []) if item.get("id") == OBLIGATION]
    uncertain = model.get("primary_strategy_id") == "hypothesis-driven" or incident.get("mode") == "systemic-repair" or incident.get("trigger") in {"escaped-defect", "failed-required-gate", "recurring-correction"}
    if not uncertain and not obligations:
        return
    if obligations and incident.get("mode") == "none":
        validator.error("TDD_EXECUTION_CONTRACT", "captured incident review cannot drop its incident identity", POLICY)
        return
    policy_path = validator.target_path(POLICY)
    policy = validator.load_json_object(policy_path, "TDD_EXECUTION_CONTRACT") if validator.is_target_file(POLICY) else None
    review = policy.get("repair_review") if isinstance(policy, dict) else None
    if review is not None and not isinstance(review, dict):
        validator.error("TDD_EXECUTION_CONTRACT", "repair_review must be a policy object", POLICY)
        return
    prior_required = False
    if validator.diff_ref:
        change = validator.git.change_set(validator.diff_ref)
        raw, available = validator.git.bounded_file_result_at_ref(change.base_revision, POLICY, 512 * 1024) if change else (None, False)
        if not available:
            validator.error("TDD_EXECUTION_CONTRACT", "repair-policy baseline is unavailable; requirement downgrade cannot be accepted", POLICY)
        try:
            previous = json.loads(raw) if raw else {}
            prior_required = isinstance(previous, dict) and isinstance(previous.get("repair_review"), dict) and previous["repair_review"].get("state") == "enabled"
        except (ValueError, UnicodeError, RecursionError):
            validator.error("TDD_EXECUTION_CONTRACT", "repair policy baseline is unreadable; requirement removal cannot be evaluated", POLICY)
    if review is None or not isinstance(review, dict) or review.get("state") != "enabled":
        if obligations or prior_required:
            validator.error("TDD_EXECUTION_CONTRACT", "captured repair-review requirement cannot be removed or deferred into successful acceptance", POLICY)
        return
    try:
        contract = TestExecutionContract()
    except (OSError, ValueError) as exc:
        validator.error("TDD_EXECUTION_SCHEMA", str(exc), POLICY)
        return
    failures = contract.policy_failures(policy)
    for failure in failures:
        validator.error("TDD_EXECUTION_CONTRACT", failure, POLICY)
    if failures:
        return
    if len(obligations) != 1 or obligations[0].get("required") is not True:
        validator.error("TDD_EXECUTION_CONTRACT", f"enabled incident review requires a retained required {OBLIGATION} proof obligation", POLICY)
    selected = [item for item in review["records"] if item["task_id"] == task["task_id"]]
    if len(selected) != 1:
        if completion:
            validator.error("TDD_EXECUTION_EVIDENCE", "incident acceptance requires exactly one selected task repair-review record", POLICY)
        return
    path = selected[0]["path"]
    raw = validator.context.read_bytes_result(validator.target_path(path), max_bytes=MAX_RECORD_BYTES)
    if raw.value is None:
        validator.error("TDD_EXECUTION_EVIDENCE", "selected repair review must be a bounded contained current record", path)
        return
    record = validator.load_json_object(validator.target_path(path), "TDD_EXECUTION_EVIDENCE")
    if record is None:
        return
    shape = contract.shape(record, "repair_evidence")
    if shape:
        for failure in shape:
            validator.error("TDD_EXECUTION_EVIDENCE", failure, path)
        return
    if record.get("policy_sha256") != validator.context.content_digest(policy_path):
        validator.error("TDD_EXECUTION_EVIDENCE_STALE", "repair review does not bind the canonical current policy", path)
    for field, expected in (("task_id", task["task_id"]), ("operation_id", task["operation_id"]), ("incident_family_id", incident.get("family_id"))):
        if record.get(field) != expected:
            validator.error("TDD_EXECUTION_EVIDENCE", f"repair review {field} differs from the selected task", path)
    original = model.get("original_case")
    if isinstance(original, dict) and record.get("original_case_ref") != original.get("source_ref"):
        validator.error("TDD_EXECUTION_EVIDENCE", "repair review must retain the source-derived original case", path)
    if (completion or record["claim"] == "incident-fixed") and (not isinstance(original, dict) or original.get("status") != "verified-fixed"):
        validator.error("TDD_EXECUTION_EVIDENCE", "incident-fixed review contradicts unverified or unresolved original-case acceptance", path)
    hypotheses = {item["id"]: item for item in model.get("hypotheses", [])}
    if any(item["id"] not in hypotheses for item in record["hypotheses"]):
        validator.error("TDD_EXECUTION_EVIDENCE", "repair hypothesis IDs must resolve in the canonical problem model", path)
    diagnosis = record["diagnosis"]
    if completion or record["claim"] == "incident-fixed":
        selected_hypothesis = hypotheses.get(diagnosis["hypothesis_id"]) if diagnosis is not None else None
        if selected_hypothesis is None or selected_hypothesis.get("status") != "supported" or diagnosis["run_ref"] not in selected_hypothesis.get("evidence_refs", []):
            validator.error("TDD_EXECUTION_EVIDENCE", "accepted diagnosis must match a supported model hypothesis and its discriminating evidence", path)
    # Reuse the registered run validator: existence or a copied status is insufficient.
    validate_testing_execution(validator.capability_validation_context(), policy)
    runs = {}
    current_refs = set(policy["execution_contract"]["evidence_records"])
    for ref in current_refs:
        value = _bound_json(validator, ref)
        if value is not None and not contract.shape(value, "evidence"):
            runs[ref] = value
    for attempt in record["attempts"]:
        ref = attempt["run_ref"]
        value = _bound_json(validator, ref, attempt["run_sha256"])
        snapshot = attempt["historical_policy"]
        if ref in current_refs:
            if snapshot is not None:
                validator.error("TDD_EXECUTION_EVIDENCE", "current qualification cannot be relabeled historical", ref)
            continue
        if snapshot is None:
            validator.error("TDD_EXECUTION_EVIDENCE", "historical failed runs require their digest-bound captured policy", ref)
            continue
        historical_policy = _bound_json(validator, snapshot["path"], snapshot["sha256"])
        if value is None or historical_policy is None:
            continue
        failures = contract.policy_failures(historical_policy) + contract.shape(value, "evidence")
        if not failures:
            command = next((item for item in historical_policy["commands"] if item["id"] == value["command_id"]), None)
            failures = ["historical command is absent from its captured policy"] if command is None else contract.evidence_failures(value, command, historical_policy["execution_contract"])
            if value["state"] != "failed" or value["policy_sha256"] != snapshot["sha256"]:
                failures.append("historical attempts retain failures only; old passes cannot establish current qualification")
            artifact = value["result_artifact"]
            if not failures and (artifact is None or validator.context.content_digest(validator.target_path(artifact["path"])) != artifact["sha256"]):
                failures.append("historical failed output is missing or changed")
        for failure in failures:
            validator.error("TDD_EXECUTION_EVIDENCE", failure, ref)
        if not failures:
            runs[ref] = value
    for failure in evidence_failures(record, review, runs, contract.repair_schema(), completion=completion, current_refs=current_refs):
        validator.error("TDD_EXECUTION_EVIDENCE", failure, path)
    if contract.view.finalize():
        validator.error("TDD_EXECUTION_SCHEMA", "repair schema changed during validation; rerun", POLICY)

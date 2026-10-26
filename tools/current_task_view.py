"""Selected bound task disposition, not a second task registry or acceptance gate."""

from __future__ import annotations

from typing import Any

from task_evidence_contract import task_model_header_failures, task_predecessor_failures
from task_readiness import execution_readiness
from target_adapter_validation.active_tasks import _bound_object, _schema_valid, _task_model_evidence

INDEX = ".ai/assistant/active-tasks.json"
POLICY = ".ai/project/testing/test-first-policy.json"


def incident_frontier(tasks: list[dict[str, Any]], selected: dict[str, Any]) -> dict[str, Any]:
    """Header-only navigation; never close tasks or load predecessor narratives."""
    family = ([selected] if selected["incident_family_id"] == "none" else
              [task for task in tasks if task["incident_family_id"] == selected["incident_family_id"]])
    family = sorted(family, key=lambda task: task["task_id"])
    active = {task["task_id"] for task in family if task["state"] == "active"}
    predecessors = {prior for task in family if task["state"] == "active" for prior in task["predecessor_task_ids"]}
    heads = sorted(active - predecessors)
    return {"incident_family_id": selected["incident_family_id"], "head_task_ids": heads,
            "selected_is_head": selected["task_id"] in heads, "multiple_heads": len(heads) > 1,
            "unclosed_predecessors": [{"task_id": task["task_id"], "model": task["problem_model"],
                "latest_failed_gate_id": task["latest_failed_gate_id"], "obligations": "not-loaded-not-discharged"}
                for task in family if task["task_id"] in active & predecessors],
            "authority": "none", "automatic_closure": False,
            "limitation": "Index-bound navigation, not validated predecessor outcomes. Concurrent heads require explicit task selection; timestamps and iteration numbers do not select an authority."}


def incident_outcome_view(model: dict[str, Any]) -> dict[str, Any] | None:
    """Project already validated model facts, never infer an outcome from test totals."""
    original = model.get("original_case")
    incident = model["incident"]
    if original is None and incident["mode"] == "none":
        return None
    status = original["status"] if isinstance(original, dict) else "unverified"
    return {
        "state": "original-case-unresolved" if status in {"unverified", "still-failing"} else "recorded-disposition-not-runtime-proof",
        "original_case": {key: original[key] for key in ("source_ref", "expected_outcome", "status")} if isinstance(original, dict) else None,
        "required_obligations": [{"id": row["id"], "status": row["status"]} for row in model["proof_obligations"] if row["required"]],
        "latest_failed_gate": incident["latest_failed_gate"],
        "rejected_hypothesis_ids": [row["id"] for row in model["hypotheses"] if row["status"] == "rejected"],
        "rejected_alternative_ids": [row["id"] for row in model["alternatives"] if row["status"] == "rejected"],
        "authority": "none", "evidence_verified": False,
        "limitation": "Bound model declarations, not fresh run verification. Component passes and navigation do not discharge the original outcome.",
    }


def current_task_view(validator: Any, task_id: str) -> dict[str, Any]:
    result = {"state": "unknown", "task_id": task_id, "authority": "none",
              "acceptance_granted": False, "historical_narratives_loaded": False,
              "diagnostics": [], "repair_evidence": {"state": "not-verified"}}
    view = validator.context
    raw = view.read_bytes_result(validator.target_path(INDEX), max_bytes=512 * 1024)
    index = validator.load_json_object(validator.target_path(INDEX), "ACTIVE_TASK_ARTIFACT") if raw.value is not None else None
    if not _schema_valid(validator, index, "active-task-index", INDEX):
        result["diagnostics"].append("active-task index is unavailable or invalid")
        return result
    ids = [task["task_id"] for task in index["tasks"]]
    matches = [task for task in index["tasks"] if task["task_id"] == task_id]
    if len(ids) != len(set(ids)) or len(matches) != 1:
        result["diagnostics"].append("select one unique registered task ID")
        return result
    lineage_failures = task_predecessor_failures(index["tasks"])
    headers = {task["task_id"]: task for task in index["tasks"]}
    lineage_failures.extend("predecessor headers cross incident families" for task in index["tasks"]
        for prior in task["predecessor_task_ids"] if prior in headers
        and headers[prior]["incident_family_id"] != task["incident_family_id"])
    if lineage_failures:
        result["diagnostics"].extend(lineage_failures[:8])
        return result
    task = matches[0]
    closure = None
    if task["state"] == "closed":
        closure = _bound_object(validator, task["completion_evidence"], "selected task closure")
        if closure is None or not _schema_valid(validator, closure, "task-closure", task["completion_evidence"]["path"]):
            result["diagnostics"].append("selected closure is unavailable, invalid or stale")
            return result
        if closure["task_id"] != task_id or closure["operation_id"] != task["operation_id"]:
            result["diagnostics"].append("selected closure identity differs from its registered task")
            return result
    model, binding, _ = _task_model_evidence(validator, task, closure)
    if not isinstance(model, dict):
        result["diagnostics"].append("selected bound model is unavailable")
        return result
    from analysis_strategy_contract import validate_problem_model
    from target_adapter_validation.analysis_strategies import load_problem_model_schema, _schema, PROBLEM_MODEL_SCHEMA
    schema = load_problem_model_schema(validator.schema_context)
    if closure is not None and model.get("schema_version") in (4, 5):
        schema = _schema(PROBLEM_MODEL_SCHEMA.with_name(f"alatyr-problem-model-v{model['schema_version']}.schema.json"), validator.schema_context)
    failures = validate_problem_model(model, schema)
    failures.extend(message for _, message in task_model_header_failures(task, model))
    if failures:
        result["diagnostics"].extend(failures[:8])
        return result
    if closure is not None:
        from target_adapter_validation.active_tasks import validate_task_closure
        path = task["completion_evidence"]["path"]
        existing = [item for item in validator.findings if item.level == "error" and item.path == path]
        if not existing:
            start = len(validator.findings)
            validate_task_closure(validator, closure, task)
            existing = [item for item in validator.findings[start:] if item.level == "error"]
        if existing:
            result["diagnostics"].extend(item.message for item in existing[:8])
            return result
    result.update(state="bound-recorded-disposition", task_state=task["state"], model=binding,
                  latest_failed_gate_id=task["latest_failed_gate_id"],
                  disposition_source=task["completion_evidence"] if closure else binding)
    outcome = incident_outcome_view(model)
    if outcome is not None:
        result["incident_outcome"] = outcome
        result["incident_frontier"] = incident_frontier(index["tasks"], task)
        result["obligation_cursor"] = {
            "model": binding,
            "unsettled_required": [{"id": row["id"], "status": row["status"]} for row in model["proof_obligations"]
                                   if row["required"] and row["status"] not in {"passed", "waived"}],
            "predecessor_obligations_discharged": False,
            "authority": "none", "evidence_verified": False,
        }
    if "execution_dependencies" in model:
        result["execution_readiness"] = execution_readiness(model)
    if closure:
        result["delivery"] = closure["delivery"]
        result["disposition_kind"] = "recorded-closure-not-current-runtime"
    else:
        result["disposition_kind"] = "active-model"
        if task_id not in getattr(validator, "repair_review_observations", {}):
            from target_adapter_validation.repair_review import validate_task_repair_review
            validate_task_repair_review(validator, task, model, completion=False)
    result["repair_evidence"] = getattr(validator, "repair_review_observations", {}).get(task_id, {"state": "not-verified"})
    policy_raw = view.read_bytes_result(validator.target_path(POLICY), max_bytes=512 * 1024)
    policy = validator.load_json_object(validator.target_path(POLICY), "TDD_EXECUTION_CONTRACT") if policy_raw.value is not None else None
    controls = {"policy": {"path": POLICY, "sha256": policy_raw.digest}, "adoption": "unknown",
                "installed_templates": {}, "available_in_source": "unknown",
                "exercised": "not-verified", "automatic_enablement": False}
    if isinstance(policy, dict):
        from test_execution_contract import TestExecutionContract
        if not TestExecutionContract().policy_failures(policy):
            review = policy.get("repair_review")
            controls["adoption"] = review["state"] if isinstance(review, dict) else "not-adopted"
            controls["schema_version"] = review["schema_version"] if isinstance(review, dict) else None
    for version, name in ((1, "repair-review.json"), (2, "repair-qualification.json")):
        controls["installed_templates"][str(version)] = validator.is_target_file(".ai/assistant/templates/" + name)
    if validator.framework_source is not None:
        controls["available_in_source"] = {str(version): (validator.framework_source / "templates/target/.ai/assistant/templates" / name).is_file()
                                           for version, name in ((1, "repair-review.json"), (2, "repair-qualification.json"))}
    if result["repair_evidence"]["state"] == "record-consistent":
        controls["exercised"] = "selected-record-consistent-not-effectiveness-proof"
    result["incident_controls"] = controls
    incident = model["incident"]
    original = model.get("original_case")
    if incident["mode"] != "none" or isinstance(original, dict) and original.get("status") in {"unverified", "still-failing"}:
        result["repair_preflight"] = {
            "state": "review-before-related-repair",
            "original_input": original.get("input") if isinstance(original, dict) else None,
            "expected_outcome": original.get("expected_outcome") if isinstance(original, dict) else None,
            "latest_failed_gate": incident["latest_failed_gate"],
            "control_adoption": controls["adoption"],
            "next_action": {"enabled": "review-bound-diagnostic-and-original-case",
                            "disabled": "respect-recorded-repair-control-decision",
                            "deferred": "respect-recorded-repair-control-decision",
                            "not-adopted": "request-explicit-repair-control-adoption-decision"}.get(controls["adoption"], "resolve-canonical-repair-control-policy"),
            "authorization_granted": False, "unrelated_work_blocked": False,
            "retention_review": "Before retaining an experimental production change, record its incident-level effect and retention or reversion reason in the existing repair review; a component pass alone is not recovery.",
            "escalation": "If related repairs do not resolve the original outcome, reassess the mechanism and owner boundaries before another local patch; preserve the failed case and frozen matrix.",
            "limitation": "Review the faithful initial state and discriminating observation before another related patch. Optional controls require target approval; this view neither qualifies repair nor grants execution permission.",
        }
    if view.finalize():
        return {"state": "unknown", "task_id": task_id, "authority": "none",
                "acceptance_granted": False, "historical_narratives_loaded": False,
                "diagnostics": ["selected inputs changed during lookup"],
                "repair_evidence": {"state": "not-verified"}}
    return result

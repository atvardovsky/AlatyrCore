"""Selected bound task disposition, not a second task registry or acceptance gate."""

from __future__ import annotations

from typing import Any

from task_evidence_contract import task_model_header_failures
from task_readiness import execution_readiness
from target_adapter_validation.active_tasks import _bound_object, _schema_valid, _task_model_evidence

INDEX = ".ai/assistant/active-tasks.json"
POLICY = ".ai/project/testing/test-first-policy.json"


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
    result.update(state="bound-recorded-disposition", task_state=task["state"], model=binding,
                  latest_failed_gate_id=task["latest_failed_gate_id"],
                  disposition_source=task["completion_evidence"] if closure else binding)
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
    if view.finalize():
        return {"state": "unknown", "task_id": task_id, "authority": "none",
                "acceptance_granted": False, "historical_narratives_loaded": False,
                "diagnostics": ["selected inputs changed during lookup"],
                "repair_evidence": {"state": "not-verified"}}
    return result

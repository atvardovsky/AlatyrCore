"""Early prerequisite inspection through existing canonical validators."""

from __future__ import annotations

from typing import Any

from architecture_review import review_frontier
from current_task_view import current_task_view
from target_adapter_validation.active_tasks import INDEX_PATH, _schema_valid, validate_active_tasks
from target_adapter_validation.model_evidence import bound_object


def initialization_readiness(validator: Any, task_id: str) -> dict:
    """Inspect once at large-task initialization, never execute project checks."""
    validator.current_task_id = task_id
    index = validator.load_json_object(validator.target_path(INDEX_PATH), "ACTIVE_TASK_ARTIFACT")
    header = None
    if _schema_valid(validator, index, "active-task-index", INDEX_PATH):
        matches = [row for row in index["tasks"] if row["task_id"] == task_id]
        if len(matches) == 1:
            header = matches[0]
        else:
            validator.error("INITIALIZATION_TASK", "initialization requires one exact registered task", INDEX_PATH)
    task = None
    architecture = {"state": "not-selected", "authority": "none"}
    if header is not None:
        if header["state"] != "active":
            validator.error("INITIALIZATION_TASK", "initialization cannot reopen a nonactive task", INDEX_PATH)
        validator.current_task_class = header["task_class"]
        if header["state"] == "active" and header["task_class"] != "small-task":
            task = current_task_view(validator, task_id)
            if task["state"] == "unknown":
                validator.error("INITIALIZATION_TASK", "selected task model is unavailable or inconsistent", INDEX_PATH)
        # Keep the existing bounded header/witness audit and historical rules.
        validate_active_tasks(validator, initializing=True)
        architecture = review_frontier(validator, header["canonical_owners"], header["changed_fact_ids"])
        for failure in architecture.get("failures", []):
            validator.error("INITIALIZATION_ARCHITECTURE", failure, ".ai/project/architecture/catalog.json")
    records = validator.discover_approval_archive_records()
    selected = validator.resolve_approval_records()
    validator.check_approval_record_shape([path for path in records if path not in selected], historical=True)
    validator.check_approval_record_shape(selected)
    validator.check_approval_hash_evidence(list(set(records) | set(selected)), compare_current_patch=False)
    if task is not None and task.get("model") is not None:
        model = bound_object(validator, task["model"], "initialization model")
        if isinstance(model, dict) and model.get("protected_change") is True and not selected:
            validator.error("INITIALIZATION_APPROVAL_REQUIRED", "protected work needs explicit current-operation approval evidence; no authority is inferred", INDEX_PATH)
    if header is not None:
        for path in selected:
            record = validator.load_json_object(path, "INITIALIZATION_APPROVAL")
            operation = record.get("operation") if isinstance(record, dict) else None
            if not isinstance(operation, dict) or operation.get("id") != header["operation_id"]:
                validator.error("INITIALIZATION_APPROVAL_IDENTITY", "selected approval belongs to a different or unknown operation", validator.rel(path))
    validator.check_change_packages()
    validator.finalize_inputs()
    errors = [row for row in validator.findings if row.level == "error"]
    return {"record_kind": "alatyr-initialization-readiness", "task_id": task_id,
            "state": "blocked" if errors else "prerequisites-consistent-not-acceptance",
            "current_task": task, "architecture": architecture,
            "checkout_context": validator.git.checkout_context(),
            "approval_records_checked": len(set(records) | set(selected)),
            "scope": "registered prerequisites, package evidence and approval metadata; no project execution or actual-diff authorization",
            "authorization_granted": False, "acceptance_eligible": False,
            "full_acceptance_required": True}

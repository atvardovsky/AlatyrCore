"""Exact, owner-reviewed loss dispositions; never substitute for task acceptance."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any

import jsonschema

from change_package_contract import historical_snapshot_task_is_distinct
from task_evidence_contract import task_predecessor_failures, task_schema
from target_adapter_validation.context import TargetFileState
from target_validation_support import is_target_relative_path

INDEX = ".ai/assistant/active-tasks.json"
LOSS_STATE = "historical-evidence-missing"
LIMIT = 512 * 1024


def _object(raw: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("evidence contains duplicate JSON keys")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError("evidence must be an object")
    return value


def _path(view, value):
    if (not isinstance(value, str) or not is_target_relative_path(value)
            or PurePosixPath(value).as_posix() != value
            or any(part in {".", "..", ""} for part in value.split("/"))):
        raise ValueError("evidence paths must be normalized target-relative paths")
    candidate = view.target
    for part in value.split("/"):
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError("evidence paths must not contain symbolic links")
    return candidate


def _bound(view, git, binding):
    if (not isinstance(binding, dict) or set(binding) != {"path", "sha256"}
            or not isinstance(binding["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", binding["sha256"]) is None):
        raise ValueError("evidence requires an exact path and SHA-256")
    path = _path(view, binding["path"])
    if not binding["path"].startswith(".ai/assistant/") or git.is_ignored(binding["path"]) is not False:
        raise ValueError("loss evidence must be retainable below .ai/assistant/")
    read = view.read_bytes_result(path, max_bytes=LIMIT)
    if read.value is None or hashlib.sha256(read.value).hexdigest() != binding["sha256"]:
        raise ValueError("bound loss evidence is missing, oversized, unsafe or changed")
    return _object(read.value)


def _validate(value, name):
    schema = task_schema(name)
    checked = jsonschema.Draft7Validator(schema.schema, format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER)
    errors = list(checked.iter_errors(value))
    if errors:
        raise ValueError(f"invalid {name}: {errors[0].message}")


def retained_loss_headers(git) -> list[dict]:
    """Absence is allowed; unavailable or invalid committed evidence is not."""
    if git.head_revision() is None:
        return []
    raw, available = git.bounded_file_result_at_ref("HEAD", INDEX, LIMIT)
    if not available:
        raise ValueError("committed task index is unavailable, unsafe or oversized")
    if raw is None:
        return []
    index = _object(raw)
    if not task_schema("active-task-index").is_valid(index):
        raise ValueError("committed task index is invalid; retention cannot be established")
    return [task for task in index["tasks"] if task["state"] == LOSS_STATE]


def load_loss_disposition(view, git, task: dict, tasks: list[dict]) -> dict:
    """Read bounded witnesses and an immutable original header, not missing models."""
    if task.get("state") != LOSS_STATE or task.get("completion_evidence") is not None:
        raise ValueError("only unclosed historical evidence-loss tasks can use this disposition")
    task_id = task["task_id"]
    if re.fullmatch(r"[A-Za-z0-9._-]+", task_id) is None or task_id in {".", ".."}:
        raise ValueError("task identity is not a safe retained-evidence token")
    binding = task.get("evidence_loss_disposition")
    loss = _bound(view, git, binding)
    if not binding["path"].startswith(f".ai/assistant/task-evidence/{task_id}/"):
        raise ValueError("loss disposition must belong to its task evidence directory")
    _validate(loss, "task-evidence-loss")
    if (loss["task_id"] != task_id or loss["operation_id"] != task["operation_id"]
            or loss["missing_model"] != task.get("problem_model")):
        raise ValueError("loss disposition must preserve the registered task and model identity")
    registration = loss["registration"]
    commit = registration["commit"]
    if git.resolve_ref(commit) != commit or git.is_ancestor(commit, "HEAD") is not True:
        raise ValueError("original registration must be an available ancestor commit")
    raw = git.bounded_file_at_ref(commit, INDEX, LIMIT)
    if raw is None or hashlib.sha256(raw).hexdigest() != registration["index_sha256"]:
        raise ValueError("original task index does not match the immutable registration")
    original_index = _object(raw)
    if not task_schema("active-task-index").is_valid(original_index):
        raise ValueError("original task index is invalid")
    originals = [row for row in original_index["tasks"] if row["task_id"] == task_id]
    current_header = {key: value for key, value in task.items() if key != "evidence_loss_disposition"}
    current_header["state"] = "active"
    if len(originals) != 1 or originals[0].get("state") != "active" or originals[0] != current_header:
        raise ValueError("historical classification cannot rewrite the original active task header")
    for model_binding in [task["problem_model"], *([task["analysis_handoff"]["model"]] if "analysis_handoff" in task else [])]:
        path = _path(view, model_binding["path"])
        if view.status(path).state != TargetFileState.MISSING:
            raise ValueError("registered model is present or unsafe; reconcile it instead of declaring loss")
    approval = _bound(view, git, loss["owner_approval"])
    if not loss["owner_approval"]["path"].startswith(".ai/assistant/task-evidence/"):
        raise ValueError("loss classification needs a retained task-evidence owner review; it is not an executable approval")
    _validate(approval, "evidence-loss-approval")
    if not approval["granted_by"].strip() or approval["granted_by"].casefold() in {"unknown", "none", "unverified"}:
        raise ValueError("owner review requires a resolved reviewer, not an unknown placeholder")
    approved_tasks = approval["tasks"]
    if len({row["task_id"] for row in approved_tasks}) != len(approved_tasks):
        raise ValueError("owner approval contains ambiguous task identities")
    expected = {"task_id": task_id, "operation_id": task["operation_id"],
                "problem_model": task["problem_model"], "registration": registration}
    if expected not in approved_tasks:
        raise ValueError("owner approval does not bind this exact registration and missing model")
    reviewed = datetime.fromisoformat(approval["reviewed_at"].replace("Z", "+00:00"))
    if reviewed.tzinfo is None or reviewed > datetime.now(timezone.utc):
        raise ValueError("owner review requires a non-future timezone-aware timestamp")
    search = _bound(view, git, loss["search_evidence"])
    if (search.get("record_kind") != "alatyr-evidence-search" or search.get("task_id") != task_id
            or search.get("expected_model") != task["problem_model"] or search.get("outcome") != "not-recovered"
            or type(search.get("inspected_artifacts")) is not int or search["inspected_artifacts"] < 1
            or not isinstance(search.get("locations"), list) or not search["locations"]
            or not all(isinstance(row, str) and row.strip() for row in search["locations"])
            or not isinstance(search.get("limitations"), str) or not search["limitations"].strip()):
        raise ValueError("bounded search evidence must retain exact model identity and its limitations")
    review = _bound(view, git, loss["dependency_review"])
    if (review.get("record_kind") != "alatyr-evidence-loss-dependency-review" or review.get("task_id") != task_id
            or review.get("registration") != registration or review.get("active_dependents") != []
            or not isinstance(review.get("reviewed_packages"), list)
            or not isinstance(review.get("limitation"), str) or not review["limitation"].strip()):
        raise ValueError("loss disposition needs an explicit dependency and package review")
    # Recheck the graph now: the review cannot waive a new transitive dependency.
    failures = task_predecessor_failures(tasks)
    if failures:
        raise ValueError("task dependency graph prevents historical loss disposition: " + failures[0])
    outcomes = loss["unresolved_outcomes"]
    if (len({row["fact_id"] for row in outcomes}) != len(outcomes)
            or {row["fact_id"] for row in outcomes} != set(task["changed_fact_ids"])
            or any(row["owner_ref"] not in task["canonical_owners"] for row in outcomes)):
        raise ValueError("every original changed fact needs an unresolved outcome with a registered owner")
    return loss


def validate_loss_disposition(validator: Any, task: dict, tasks: list[dict]) -> dict | None:
    try:
        return load_loss_disposition(validator.context, validator.git, task, tasks)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
        validator.error("TASK_EVIDENCE_LOSS", str(exc), INDEX)
        return None


def validate_package_loss(validator: Any, data: dict, source: str, status: str) -> bool:
    """Handle only explicit references; all other incident validation stays intact."""
    incident = data.get("incident_continuity", {})
    if "evidence_loss_disposition" not in incident:
        return False
    try:
        operation = data.get("operation")
        gate = incident.get("latest_failed_gate")
        if not isinstance(operation, dict) or not isinstance(gate, dict):
            raise ValueError("historical package requires object-shaped operation and latest_failed_gate")
        selected = {str(path.relative_to(validator.target)) for path in validator.change_packages}
        if status != "blocked" or source in selected:
            raise ValueError("evidence loss cannot replace a selected/current or unblocked package model")
        raw = validator.context.read_bytes_result(_path(validator.context, INDEX), max_bytes=LIMIT)
        index = _object(raw.value) if raw.value is not None else None
        if not task_schema("active-task-index").is_valid(index):
            raise ValueError("package evidence-loss reference requires a valid task index")
        model_binding = incident.get("problem_model")
        if not isinstance(model_binding, dict) or not isinstance(model_binding.get("path"), str):
            raise ValueError("historical loss requires the exact registered model binding")
        if (not historical_snapshot_task_is_distinct(raw.value, validator.current_task_id, data)
                or validator.target_path(model_binding["path"])
                in getattr(validator, "problem_models", [])):
            raise ValueError("historical loss cannot be borrowed by a current operation or selected model alias")
        matches = [task for task in index["tasks"] if task.get("evidence_loss_disposition") == incident["evidence_loss_disposition"]]
        if len(matches) != 1:
            raise ValueError("package evidence-loss reference must select one registered historical task")
        task = matches[0]
        if (validator.current_task_id == task["task_id"] or task["operation_id"] != operation.get("id")
                or task["problem_model"] != incident.get("problem_model")
                or task["incident_family_id"] != incident.get("family_id")
                or task["latest_failed_gate_id"] != gate.get("id")):
            raise ValueError("package loss reference differs from its exact historical task lineage")
        loss = load_loss_disposition(validator.context, validator.git, task, index["tasks"])
        review = _bound(validator.context, validator.git, loss["dependency_review"])
        if {"path": source, "status": "blocked"} not in review["reviewed_packages"]:
            raise ValueError("historical package was not included in the dependency review")
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
        validator.error("PACKAGE_INCIDENT_EVIDENCE_LOSS", str(exc), source)
        return True
    validator.warn("PACKAGE_INCIDENT_EVIDENCE_LOST", "reviewed historical model loss; package remains blocked and outcomes unverified", source)
    return True

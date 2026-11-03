"""Exact retained model bindings shared by task and incident consumers."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from change_package_contract import retained_incident_shape_failures, historical_snapshot_task_is_distinct
from target_adapter_validation.values import is_resolved_string
from target_validation_support import is_target_relative_path

INDEX_PATH = ".ai/assistant/active-tasks.json"
MAX_ARTIFACT_BYTES = 512 * 1024


def bound_object(validator: Any, binding: Any, label: str, *, details: dict | None = None) -> dict | None:
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
        validator.error("ACTIVE_TASK_BINDING", f"{label} requires path and SHA-256", INDEX_PATH, details=details)
        return None
    path, digest = binding["path"], binding["sha256"]
    try:
        safe = is_resolved_string(path) and "\\" not in path and is_target_relative_path(path) and validator.is_target_file(path)
    except (OSError, ValueError):
        safe = False
    if not safe:
        validator.error("ACTIVE_TASK_BINDING", f"{label} path is unavailable or unsafe: {path!r}", INDEX_PATH, details=details)
        return None
    artifact = validator.target_path(path)
    if any(part.is_symlink() for part in (artifact, *artifact.parents) if part != validator.target and validator.target in part.parents):
        validator.error("ACTIVE_TASK_BINDING", f"{label} must be a bounded regular file", path, details=details)
        return None
    content = validator.context.read_bytes_result(artifact, max_bytes=MAX_ARTIFACT_BYTES)
    if content.value is None or digest != hashlib.sha256(content.value).hexdigest():
        validator.error("ACTIVE_TASK_DIGEST", f"{label} SHA-256 does not match its artifact", path, details=details)
        return None
    return validator.load_json_object(artifact, "ACTIVE_TASK_ARTIFACT")


def retained_model_pair(validator: Any, binding: Any, witness: Any, task_id: Any) -> tuple[Any, Any]:
    if (not isinstance(witness, dict) or set(witness) != {"model", "projection", "retention_review"}
            or not is_resolved_string(witness.get("retention_review"))):
        validator.error("ACTIVE_TASK_WITNESS", "durable evidence requires explicit bindings and retention review", INDEX_PATH)
        return None, None
    if not isinstance(task_id, str) or re.fullmatch(r"[A-Za-z0-9._-]+", task_id) is None or task_id in (".", ".."):
        validator.error("ACTIVE_TASK_WITNESS", "retained task identities must be safe path tokens", INDEX_PATH)
        return None, None
    prefix = f".ai/assistant/task-evidence/{task_id}/"
    for name in ("model", "projection"):
        item = witness[name]
        if (not isinstance(item, dict) or not isinstance(item.get("path"), str)
                or not item["path"].startswith(prefix) or not is_target_relative_path(item["path"])
                or "\\" in item["path"] or validator.git.is_ignored(item["path"]) is not False):
            validator.error("ACTIVE_TASK_WITNESS", "durable witness must be retainable below .ai/assistant/task-evidence/", INDEX_PATH)
            return None, None
    if not isinstance(binding, dict) or witness["model"].get("sha256") != binding.get("sha256"):
        validator.error("ACTIVE_TASK_WITNESS", "durable model must preserve the registered runtime model digest", INDEX_PATH)
        return None, None
    result = tuple(bound_object(validator, witness[name], "durable " + name,
        details={"task_id": task_id, "evidence_binding": witness[name], "action": "recover-exact-evidence"})
        for name in ("model", "projection"))
    return result if all(isinstance(item, dict) for item in result) else (None, None)


def incident_model_location(validator: Any, data: dict, source: str, binding: dict) -> tuple[Any, Any]:
    """Return an explicit archived pair only for nonselected historical evidence."""
    retained = data["incident_continuity"].get("retained_evidence")
    runtime = validator.target_path(binding["path"])
    if "retained_evidence" not in data["incident_continuity"]:
        return runtime, None
    shape = retained_incident_shape_failures(retained)
    if shape:
        for message in shape:
            validator.error("PACKAGE_INCIDENT_RETAINED", message, source)
        return None, None
    task_id = retained["task_id"]
    witness = {key: value for key, value in retained.items() if key != "task_id"}
    model, projection = retained_model_pair(validator, binding, witness, task_id)
    if model is None or projection is None:
        return None, None
    tasks = model.get("task_binding", {}).get("task_ids") if isinstance(model.get("task_binding"), dict) else None
    if not isinstance(tasks, list) or task_id not in tasks:
        validator.error("PACKAGE_INCIDENT_RETAINED", "retained model does not bind its declared task identity", source)
        return None, None
    selected = (validator.target_path(source) in validator.change_packages
                or runtime in getattr(validator, "problem_models", [])
                or getattr(validator, "current_task_id", None) == task_id)
    current_task = getattr(validator, "current_task_id", None)
    if current_task is not None and not selected:
        headers = validator.context.read_bytes_result(validator.target_path(INDEX_PATH), max_bytes=MAX_ARTIFACT_BYTES)
        selected = not historical_snapshot_task_is_distinct(headers.value, current_task, data)
    if validator.is_target_file(runtime) and validator.context.content_digest(runtime) != binding["sha256"]:
        validator.error("PACKAGE_INCIDENT_MODEL_DIGEST", "runtime and retained incident evidence conflict", source)
        return None, None
    if selected:
        return runtime, None
    if data.get("evidence_classification") != "historical-record":
        validator.error("PACKAGE_INCIDENT_RETAINED", "retained incident evidence must explicitly remain historical", source)
        return None, None
    validator.info("PACKAGE_INCIDENT_RETAINED", "exact retained model selected; no execution, completion or authority is inferred", source)
    return validator.target_path(witness["model"]["path"]), validator.target_path(witness["projection"]["path"])

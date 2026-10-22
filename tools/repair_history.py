"""Bounded same-task history checks for previously captured repair obligations."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from target_validation_support import is_target_relative_path
from path_spec import logical_path
from task_evidence_contract import task_schema

INDEX = ".ai/assistant/active-tasks.json"


def captured_repair_required(validator: Any, task: dict[str, Any], *, completion: bool = False) -> bool:
    if not validator.diff_ref:
        if completion:
            validator.error("TDD_REPAIR_HISTORY", "selected-task completion requires an explicit comparison base; missing history cannot clear retained review requirements", INDEX)
        return False
    base_revision = validator.git.comparison_base(validator.diff_ref)
    if base_revision is None:
        validator.error("TDD_REPAIR_HISTORY", "current comparison base is unavailable; repair-history continuity is unresolved", INDEX)
        return False

    def read(path, digest=None):
        if not isinstance(path, str) or not is_target_relative_path(path):
            raise ValueError("unsafe prior repair witness")
        logical_path(path)
        if path != INDEX and (not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None):
            raise ValueError("prior repair witness requires a concrete SHA-256")
        raw, available = validator.git.bounded_file_result_at_ref(base_revision, path, 512 * 1024)
        if not available:
            raise ValueError(f"prior repair witness unavailable: {path}")
        if raw is None:
            return None
        data = raw.encode() if isinstance(raw, str) else raw
        if digest is not None and hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("prior repair witness digest mismatch")
        value = json.loads(data)
        if not isinstance(value, dict):
            raise ValueError("prior repair witness must be an object")
        return value

    try:
        index = read(INDEX)
        if index is None:
            return False
        if not task_schema("active-task-index").is_valid(index):
            raise ValueError("present prior task index is invalid; absence of a review requirement cannot be established")
        tasks = index.get("tasks")
        if not isinstance(tasks, list) or any(not isinstance(item, dict) for item in tasks):
            raise ValueError("prior task index requires an array of task headers")
        matches = [item for item in tasks if item.get("task_id") == task["task_id"]]
        if len(matches) > 1:
            raise ValueError("duplicate prior task identities")
        previous = matches[0] if matches else None
        if previous is None:
            return False
        if previous.get("incident_family_id") not in (None, "none", task.get("incident_family_id")):
            raise ValueError("same-task incident identity cannot be discarded or replaced")
        sticky = previous.get("repair_review_required")
        if sticky is not None and type(sticky) is not bool:
            raise ValueError("prior repair-review header must be boolean")
        if sticky is True:
            return True
        closure = previous.get("completion_evidence")
        if closure is None:
            if previous.get("incident_family_id") not in (None, "none") and sticky is None:
                raise ValueError("active incident history has no retained review disposition; reconcile it before completion")
            return False  # Ignored runtime history is guarded by the publication transaction.
        if not isinstance(closure, dict) or set(closure) != {"path", "sha256"}:
            raise ValueError("prior closure requires a path and SHA-256 binding")
        value = read(closure.get("path"), closure.get("sha256"))
        witness = value.get("analysis_witness") if isinstance(value, dict) else None
        binding = witness.get("model") if isinstance(witness, dict) else None
        if not isinstance(binding, dict):
            raise ValueError("captured closure has no verifiable repair-model witness")
        model = read(binding.get("path"), binding.get("sha256"))
        obligations = model.get("proof_obligations") if isinstance(model, dict) else None
        if not isinstance(obligations, list) or any(not isinstance(item, dict) for item in obligations):
            raise ValueError("captured repair obligations are unavailable")
        return any(item.get("id") == "repair-evidence-review" and item.get("required") is True for item in obligations)
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        validator.error("TDD_REPAIR_HISTORY", str(exc), INDEX)
        return False

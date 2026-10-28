"""Resolve one registered task question without delivering its entire model."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

from analysis_evidence import probe_binding, verify_artifacts
from analysis_strategy_contract import validate_problem_model
from task_evidence_contract import task_model_header_failures, task_predecessor_failures, task_schema
from target_validation_support import is_target_relative_path
from task_readiness import execution_readiness


INDEX = ".ai/assistant/active-tasks.json"
MAX_QUESTION_WORDS = 800
MAX_QUESTION_CHARACTERS = 8192


def _object(raw: bytes, label: str) -> dict:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError(f"{label} must be bounded valid JSON: {type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def resolve_context_question(binding: dict, read: Callable[[str, int], bytes]) -> tuple[dict, list[str]]:
    """Use canonical schemas and evidence checks; never infer permission or meaning."""
    index_raw = read(INDEX, 512 * 1024)
    index = _object(index_raw, "active-task index")
    error = next(task_schema("active-task-index").iter_errors(index), None)
    if error is not None:
        raise ValueError(f"active-task index: {error.message}")
    tasks = index["tasks"]
    if len({task["task_id"] for task in tasks}) != len(tasks):
        raise ValueError("active-task IDs must be unique")
    failures = task_predecessor_failures(tasks)
    headers = {task["task_id"]: task for task in tasks}
    if failures or any(headers[prior]["incident_family_id"] != task["incident_family_id"]
                       for task in tasks for prior in task["predecessor_task_ids"] if prior in headers):
        raise ValueError("active-task lineage is inconsistent")
    task = headers.get(binding["task_id"])
    if task is None or task["state"] != "active" or task["problem_model"] is None:
        raise ValueError("question must select one registered active task with a problem model")
    model_binding = task["problem_model"]
    path = model_binding["path"]
    if not is_target_relative_path(path) or "\\" in path:
        raise ValueError("question model must remain target-relative")
    raw = read(path, 65536)
    actual = hashlib.sha256(raw).hexdigest()
    if actual != model_binding["sha256"] or actual != binding["model_sha256"]:
        raise ValueError("question model binding is stale")
    model = _object(raw, "question model")
    schema_path = Path(__file__).resolve().parents[1] / "schemas/alatyr-problem-model.schema.json"
    failures = validate_problem_model(model, json.loads(schema_path.read_text(encoding="utf-8")))
    failures.extend(message for _, message in task_model_header_failures(task, model))
    if failures:
        raise ValueError("invalid question model: " + "; ".join(failures[:8]))
    failures = verify_artifacts(model, read)
    if failures:
        raise ValueError("stale question evidence: " + "; ".join(failures[:8]))
    identity = binding["obligation_id"]
    proofs = {row["id"]: row for row in model["proof_obligations"]}
    probes = [row for row in model.get("analysis_evidence", {}).get("probes", []) if row["obligation_id"] == identity]
    proof = proofs.get(identity)
    if proof is None or proof["status"] in {"passed", "waived"} or len(probes) != 1:
        raise ValueError("question must select one unresolved proof obligation with an operational probe")
    probe = probes[0]
    unknowns = {row["id"]: row for row in model["unknowns"]}
    paths = sorted(set(task["canonical_owners"] + probe["input_paths"]))
    if any(not is_target_relative_path(path) or "\\" in path for path in paths):
        raise ValueError("question inputs and canonical owners must remain target-relative")
    readiness = execution_readiness(model)
    eligibility = ("dependency-unconfigured" if readiness["state"] == "not-configured" else
                   "ready" if identity in readiness["ready"] else
                   "blocked" if identity in readiness["blocked"] else "waiting")
    question = {
        "task_id": task["task_id"], "operation_id": task["operation_id"],
        "model": model_binding, "obligation_id": identity, "question": proof["statement"],
        "uncertainties": [unknowns[key] for key in probe["unknown_ids"]],
        "method": probe["method"], "predictions": probe["predictions"],
        "probe_sha256": probe_binding(model, probe), "required_paths": paths,
        "eligibility": eligibility, "unsettled_prerequisites": readiness["unsettled_prerequisites"].get(identity, []),
        "selection_review_required": True, "retry_review_required": probe["result"] is not None,
        "active_projection_locator": model["active_projection"], "projection_content_verified": False,
        "index_sha256": hashlib.sha256(index_raw).hexdigest(),
        "authority": "none", "authorization_granted": False, "acceptance_granted": False,
        "actual_use": "not-observed",
        "limitation": "Question-bound routing, not evidence of comprehension, current authorization or a completed probe. Read retained owners before acting.",
    }
    rendered = json.dumps(question, indent=2, sort_keys=True, ensure_ascii=True)
    if len(rendered.split()) > MAX_QUESTION_WORDS or len(rendered) > MAX_QUESTION_CHARACTERS:
        raise ValueError("question view exceeds its bounded delivery limit; narrow or decompose the probe")
    return question, paths

"""Canonical compact projection shared by task routing and knowledge discovery."""

from __future__ import annotations

from typing import Any
import json
from functools import lru_cache
from pathlib import Path

import jsonschema

TASK_PROJECTION_FIELDS = (
    "operation_id", "canonical_owners", "changed_fact_ids", "incident_family_id",
    "predecessor_task_ids", "latest_failed_gate_id",
)


@lru_cache(maxsize=3)
def task_schema(name: str) -> jsonschema.Draft7Validator:
    if name not in {"active-task-index", "task-closure", "publication-receipt"}:
        raise ValueError(f"unsupported task schema: {name}")
    path = Path(__file__).resolve().parents[1] / f"schemas/alatyr-{name}.schema.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(value)
    return jsonschema.Draft7Validator(value)


def task_projection_mismatches(task: dict[str, Any], closure: dict[str, Any]) -> tuple[str, ...]:
    return tuple(field for field in TASK_PROJECTION_FIELDS if task.get(field) != closure.get(field))


def task_model_header_failures(task: dict[str, Any], model: dict[str, Any]) -> list[tuple[str, str]]:
    """Pure selected-header checks shared by publication and canonical validation."""
    failures = []
    obligations = model.get("proof_obligations", [])
    required_review = isinstance(obligations, list) and any(isinstance(item, dict) and item.get("id") == "repair-evidence-review" and item.get("required") is True for item in obligations)
    if "repair_review_required" in task and task["repair_review_required"] != required_review:
        failures.append(("ACTIVE_TASK_PROJECTION", "captured repair review cannot be removed or downgraded; sticky header differs from required model obligation"))
    if model.get("schema_version") in (6, 7) and required_review and task.get("repair_review_required") is not True:
        failures.append(("ACTIVE_TASK_PROJECTION", "schema-6/7 incident review requires a retained repair_review_required header"))
    if model.get("operation_id") != task.get("operation_id"):
        failures.append(("ACTIVE_TASK_MODEL_LINEAGE", "problem model operation differs from the registered operation"))
    binding = model.get("task_binding")
    if not isinstance(binding, dict) or task.get("task_id") not in binding.get("task_ids", []):
        failures.append(("ACTIVE_TASK_MODEL_LINEAGE", "problem model does not bind the registered task"))
    facts = model.get("changed_facts")
    fact_ids = {fact.get("id") for fact in facts if isinstance(fact, dict) and isinstance(fact.get("id"), str)} if isinstance(facts, list) else None
    if fact_ids is None or set(task.get("changed_fact_ids", [])) != fact_ids:
        failures.append(("ACTIVE_TASK_PROJECTION", "changed-fact header differs from problem model"))
    incident = model.get("incident")
    if isinstance(incident, dict):
        if task.get("incident_family_id") != incident.get("family_id"):
            failures.append(("ACTIVE_TASK_PROJECTION", "incident family differs from problem model"))
        gate = incident.get("latest_failed_gate")
        if isinstance(gate, dict) and gate.get("id") != task.get("latest_failed_gate_id"):
            failures.append(("ACTIVE_TASK_PROJECTION", "failed-gate header differs from problem model"))
    return failures


def task_predecessor_failures(tasks: list[dict[str, Any]]) -> list[str]:
    """Validate header graph shape after canonical active-index schema checks."""
    by_id = {task["task_id"]: task for task in tasks}
    failures = []
    for start in by_id:
        visited, pending = set(), [start]
        while pending:
            node = pending.pop()
            if node in visited:
                continue
            visited.add(node)
            for predecessor in by_id[node]["predecessor_task_ids"]:
                if predecessor == start or predecessor not in by_id:
                    failures.append(f"{start} has cyclic or unavailable predecessor {predecessor}")
                elif predecessor not in visited:
                    pending.append(predecessor)
    return failures

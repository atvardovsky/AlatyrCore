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

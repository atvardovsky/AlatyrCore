"""Typed read model for the source-owned installation context router."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class InstallerStage:
    stage_id: str
    required_context: tuple[str, ...]
    conditional_context: tuple[str, ...]
    depends_on: tuple[str, ...]
    required_evidence: tuple[str, ...]
    prohibited_actions: tuple[str, ...]


@dataclass(frozen=True)
class InstallerStagePlan:
    schema_version: int
    stages: tuple[InstallerStage, ...]
    source_digest: str

    def through(self, stage_id: str) -> tuple[InstallerStage, ...]:
        for index, stage in enumerate(self.stages):
            if stage.stage_id == stage_id:
                return self.stages[: index + 1]
        raise ValueError(f"unknown installer stage: {stage_id}")


def _strings(value: Any, *, field: str, required: bool = False) -> tuple[str, ...]:
    if value is None and not required:
        return ()
    if not isinstance(value, list) or (required and not value) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"installer stage {field} must be a string list")
    return tuple(value)


def load_installer_stage_plan(path: Path) -> InstallerStagePlan:
    """Load and close stage dependencies in declared routing order."""

    raw = path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("installer context router must contain an object")
    if data.get("schema_version") != 1:
        raise ValueError("installer context router schema_version must be 1")
    if data.get("router_kind") != "alatyr-installation-context-router":
        raise ValueError("installer context router kind is invalid")
    order = _strings(data.get("routing_order"), field="routing_order", required=True)
    entries = data.get("stages")
    if not isinstance(entries, dict) or set(entries) != set(order):
        raise ValueError("installer routing_order and stage IDs must match exactly")

    known: set[str] = set()
    stages: list[InstallerStage] = []
    for stage_id in order:
        entry = entries.get(stage_id)
        if not isinstance(entry, dict):
            raise ValueError(f"installer stage {stage_id} must contain an object")
        dependencies = _strings(entry.get("depends_on"), field=f"{stage_id}.depends_on")
        unknown = set(dependencies) - known
        if unknown:
            raise ValueError(
                f"installer stage {stage_id} depends on later or unknown stages: "
                f"{sorted(unknown)}"
            )
        stages.append(
            InstallerStage(
                stage_id=stage_id,
                required_context=_strings(
                    entry.get("required_context"),
                    field=f"{stage_id}.required_context",
                    required=True,
                ),
                conditional_context=_strings(
                    entry.get("conditional_context"),
                    field=f"{stage_id}.conditional_context",
                ),
                depends_on=dependencies,
                required_evidence=_strings(
                    entry.get("required_evidence"),
                    field=f"{stage_id}.required_evidence",
                ),
                prohibited_actions=_strings(
                    entry.get("prohibited_actions"),
                    field=f"{stage_id}.prohibited_actions",
                    required=True,
                ),
            )
        )
        known.add(stage_id)
    return InstallerStagePlan(
        schema_version=1,
        stages=tuple(stages),
        source_digest="sha256:" + hashlib.sha256(raw).hexdigest(),
    )


def stage_checkpoint_identity(
    plan: InstallerStagePlan,
    stage_id: str,
    *,
    source_root: Path,
) -> dict[str, Any]:
    """Bind a disposable stage checkpoint to the exact required source inputs."""

    stages = plan.through(stage_id)
    inputs: dict[str, str] = {}
    for stage in stages:
        for relpath in stage.required_context:
            path = source_root / relpath
            if not path.is_file():
                raise ValueError(f"installer stage context is missing: {relpath}")
            inputs[relpath] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "contract": "alatyr-installer-stage-checkpoint-v1",
        "router_digest": plan.source_digest,
        "completed_stage": stage_id,
        "required_input_digests": dict(sorted(inputs.items())),
        "authority": "optimization-only; never approval or semantic evidence",
    }

#!/usr/bin/env python3
"""Validate optional team-collaboration source and target-template contracts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
FRAMEWORK = ROOT / "framework" / "team-collaboration.md"
OPERATING_MODEL = TARGET / ".ai" / "project" / "team-operating-model.md"
PROJECT_CONTOUR = TARGET / ".ai" / "project" / "contour.md"
REGISTRY = TARGET / ".ai" / "assistant" / "team" / "work-registry.json"
CONTEXT_OVERLAY = TARGET / ".ai" / "assistant" / "team" / "context-overlay.json"
TASK_FLOW = TARGET / ".ai" / "assistant" / "flows" / "team-task-coordination.flow.md"
HANDOFF_FLOW = TARGET / ".ai" / "assistant" / "flows" / "team-handoff.flow.md"
DECISION_FLOW = TARGET / ".ai" / "assistant" / "flows" / "team-decision.flow.md"
REVIEW_FLOW = TARGET / ".ai" / "assistant" / "flows" / "team-review.flow.md"
GATE = TARGET / ".ai" / "assistant" / "gates" / "team-collaboration.md"
CHECKPOINT = TARGET / ".ai" / "assistant" / "templates" / "team-checkpoint.md"
HANDOFF = TARGET / ".ai" / "assistant" / "templates" / "team-handoff.md"
DECISION = TARGET / ".ai" / "assistant" / "templates" / "team-decision-record.md"
CATALOG = TARGET / ".ai" / "assistant" / "operation-catalog.json"
ROUTER = TARGET / ".ai" / "assistant" / "context-router.json"
MANIFEST = TARGET / ".ai" / "alatyr.yaml"
MODULE_PROFILE = TARGET / ".ai" / "assistant" / "module-profile.md"
MATURITY_PROFILE = TARGET / ".ai" / "assistant" / "maturity-profile.md"
HELP = TARGET / ".ai" / "assistant" / "help.md"
HELP_REFERENCE = TARGET / ".ai" / "assistant" / "help-reference.md"

TEAM_OPERATIONS = {
    "team-status",
    "team-task",
    "team-conflict-review",
    "team-handoff",
    "team-decision",
    "team-review",
    "team-merge-check",
}
READ_ONLY_OPERATIONS = {
    "team-status",
    "team-conflict-review",
    "team-review",
    "team-merge-check",
}
REGISTRY_METADATA = [
    "project",
    "module_state",
    "coordination_backend",
    "canonical_task_source",
    "synchronization_direction",
    "operating_model",
    "updated_at",
    "evidence_revision",
    "storage_policy",
    "retention_policy",
    "privacy_policy",
]
TASK_STRINGS = [
    "id",
    "goal",
    "priority",
    "priority_rationale",
    "priority_decided_by",
    "status",
    "owner_actor_id",
    "parent_request",
    "coordination_backend_ref",
    "branch_or_worktree",
    "base_revision",
    "evidence_revision",
    "review_state",
    "validation_state",
    "latest_checkpoint",
    "handoff_state",
    "next_action",
    "updated_at",
]
TASK_LISTS = [
    "non_goals",
    "reviewer_actor_ids",
    "allowed_actions",
    "context_profiles",
    "project_areas",
    "changed_fact_ids",
    "canonical_owner_refs",
    "expected_surfaces",
    "dependencies",
    "blockers",
    "related_task_ids",
    "approval_records",
    "review_evidence_refs",
    "decision_records",
    "residual_risks",
]


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AssertionError(f"missing {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(data, dict):
        raise AssertionError(f"{path.relative_to(ROOT)} must contain an object")
    return data


def require_text(path: Path, snippets: list[str], failures: list[str]) -> None:
    if not path.is_file():
        failures.append(f"missing {path.relative_to(ROOT)}")
        return
    text = path.read_text(encoding="utf-8")
    for snippet in snippets:
        if snippet not in text:
            failures.append(f"{path.relative_to(ROOT)} missing {snippet}")


def require_string(value: Any, label: str, failures: list[str]) -> None:
    if not isinstance(value, str) or not value:
        failures.append(f"{label} must be a non-empty string")


def require_string_list(value: Any, label: str, failures: list[str]) -> None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        failures.append(f"{label} must be a string list")


def main() -> int:
    failures: list[str] = []

    require_text(
        FRAMEWORK,
        [
            "ALATYR-TEAM-001",
            "## Ownership Split",
            "## Shared Work Registry",
            "## Priority",
            "## Claims And Concurrent Work",
            "## Checkpoints And Handoffs",
            "## Decisions And Discussions",
            "## Team Review And Merge Readiness",
            "## Installation And Update",
            "changed-fact IDs and canonical owner references",
            "not portable shell commands",
        ],
        failures,
    )
    require_text(
        OPERATING_MODEL,
        [
            "## Coordination Backend",
            "## Actors And Roles",
            "## Priority Policy",
            "## Review And Decision Policy",
            "## Concurrent Work Policy",
            "{TARGET_TASK_SOURCE_OF_TRUTH}",
            "{TARGET_TEAM_RECORD_PRIVACY_POLICY}",
        ],
        failures,
    )
    require_text(
        PROJECT_CONTOUR,
        [
            "target team actors and roles",
            ".ai/project/team-operating-model.md",
            "assistant work registry",
        ],
        failures,
    )
    require_text(
        MATURITY_PROFILE,
        [
            "### Task Area: `team-collaboration`",
            "task source, synchronization direction",
            "changed-fact overlap policy",
        ],
        failures,
    )
    require_text(
        TASK_FLOW,
        [
            "## Status",
            "## Start",
            "## Claim",
            "## Conflicts",
            "## Checkpoint",
            "## Release",
            "return the proposed registry/backend delta",
        ],
        failures,
    )
    require_text(
        HANDOFF_FLOW,
        ["## Steps", "acceptance", "repository revision", "target backend"],
        failures,
    )
    require_text(
        DECISION_FLOW,
        [
            "## Priority Rule",
            "authorized target decision owner",
            "canonical source",
            "With `read-only`",
        ],
        failures,
    )
    require_text(
        REVIEW_FLOW,
        ["## Team Review", "## Merge Check", "current head and base", "Merge readiness is evidence"],
        failures,
    )
    require_text(
        GATE,
        [
            "## Before Start Or Resume",
            "## Before Handoff",
            "## Before Review Or Merge Readiness",
            "Changed-fact IDs",
            "never grants approval",
        ],
        failures,
    )
    require_text(
        CHECKPOINT,
        ["Checkpoint ID:", "Repository revision:", "Minimum resume context:", "Exact next action:"],
        failures,
    )
    require_text(
        HANDOFF,
        ["Handoff ID:", "Source actor:", "Destination actor or role:", "State:", "Required context:"],
        failures,
    )
    require_text(
        DECISION,
        ["Decision ID:", "Decision owner:", "## Options", "Priority implications:", "Canonical destination:"],
        failures,
    )

    try:
        registry = load_json(REGISTRY)
        context_overlay = load_json(CONTEXT_OVERLAY)
        catalog = load_json(CATALOG)
        router = load_json(ROUTER)
    except AssertionError as exc:
        failures.append(str(exc))
        registry = {}
        context_overlay = {}
        catalog = {}
        router = {}

    if registry.get("schema_version") != 1:
        failures.append("team work registry schema_version must be 1")
    if registry.get("registry_kind") != "target-team-work-registry":
        failures.append("team work registry registry_kind is invalid")
    for field in REGISTRY_METADATA:
        require_string(registry.get(field), f"registry.{field}", failures)
    if registry.get("operating_model") != ".ai/project/team-operating-model.md":
        failures.append("registry operating_model must point to the target team model")
    tasks = registry.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        failures.append("registry.tasks must contain a placeholder task contract")
        tasks = []
    for index, task in enumerate(tasks):
        label = f"registry.tasks[{index}]"
        if not isinstance(task, dict):
            failures.append(f"{label} must be an object")
            continue
        for field in TASK_STRINGS:
            require_string(task.get(field), f"{label}.{field}", failures)
        for field in TASK_LISTS:
            require_string_list(task.get(field), f"{label}.{field}", failures)
        overlap = task.get("overlap")
        claim = task.get("claim")
        if not isinstance(overlap, dict):
            failures.append(f"{label}.overlap must be an object")
        else:
            for field in ["state", "checked_at", "checked_revision", "resolution"]:
                require_string(overlap.get(field), f"{label}.overlap.{field}", failures)
            for field in ["fact_ids", "contract_or_dependency_refs", "file_or_surface_refs"]:
                require_string_list(
                    overlap.get(field), f"{label}.overlap.{field}", failures
                )
        if not isinstance(claim, dict):
            failures.append(f"{label}.claim must be an object")
        else:
            for field in [
                "mode",
                "actor_id",
                "claimed_at",
                "expires_at",
                "base_revision",
                "state",
            ]:
                require_string(claim.get(field), f"{label}.claim.{field}", failures)

    operations = catalog.get("operations", [])
    operation_by_id = {
        item.get("id"): item for item in operations if isinstance(item, dict)
    }
    missing_operations = sorted(TEAM_OPERATIONS - set(operation_by_id))
    if missing_operations:
        failures.append(f"operation catalog missing team operations {missing_operations}")
    for operation_id in TEAM_OPERATIONS:
        operation = operation_by_id.get(operation_id, {})
        if operation.get("required_module") != "team-collaboration":
            failures.append(f"{operation_id} must require team-collaboration")
    for operation_id in READ_ONLY_OPERATIONS:
        if operation_by_id.get(operation_id, {}).get("allowed_actions") != ["read-only"]:
            failures.append(f"{operation_id} must be read-only")

    overlay_route = router.get("task_scale_overlays", {}).get("team-active")
    if not isinstance(overlay_route, dict):
        failures.append("context router missing team-active overlay")
    else:
        if overlay_route.get("descriptor") != (
            ".ai/assistant/team/context-overlay.json"
        ):
            failures.append("team-active must route to its lazy descriptor")
    if context_overlay.get("schema_version") != 1:
        failures.append("team-active context overlay schema_version must be 1")
    if context_overlay.get("overlay_kind") != "target-team-context-overlay":
        failures.append("team-active context overlay kind is invalid")
    if context_overlay.get("overlay_id") != "team-active":
        failures.append("team-active context overlay ID is invalid")
    candidates = set(context_overlay.get("operation_candidates", []))
    if candidates != TEAM_OPERATIONS:
        failures.append("team-active operation candidates must match team operations")
    required_context = set(context_overlay.get("required_context", []))
    for path in [
        ".ai/framework/team-collaboration.md",
        ".ai/project/team-operating-model.md",
        ".ai/assistant/team/work-registry.json",
        ".ai/assistant/gates/team-collaboration.md",
    ]:
        if path not in required_context:
            failures.append(f"team-active overlay missing {path}")
    if any(
        path in router.get("bootstrap_context", [])
        for path in [
            ".ai/framework/team-collaboration.md",
            ".ai/project/team-operating-model.md",
            ".ai/assistant/team/work-registry.json",
        ]
    ):
        failures.append("team collaboration files must stay outside bootstrap")

    manifest_text = MANIFEST.read_text(encoding="utf-8")
    for path in [
        ".ai/project/team-operating-model.md",
        ".ai/assistant/team/context-overlay.json",
        ".ai/assistant/team/work-registry.json",
        ".ai/assistant/gates/team-collaboration.md",
    ]:
        if path not in manifest_text:
            failures.append(f"manifest missing team path {path}")

    module_text = MODULE_PROFILE.read_text(encoding="utf-8")
    match = re.search(
        r"Module: `team-collaboration`(?P<body>.*?)(?=\nModule: `|\n## Evidence)",
        module_text,
        flags=re.DOTALL,
    )
    if not match:
        failures.append("module profile missing team-collaboration")
    else:
        body = match.group("body")
        for path in [
            ".ai/project/team-operating-model.md",
            ".ai/assistant/team/work-registry.json",
            ".ai/assistant/gates/team-collaboration.md",
        ]:
            if path not in body:
                failures.append(f"team module profile missing {path}")

    for path in [HELP_REFERENCE]:
        text = path.read_text(encoding="utf-8")
        for alias in [
            "Alatyr team status",
            "Alatyr claim",
            "Alatyr conflicts",
            "Alatyr handoff",
            "Alatyr decision",
            "Alatyr review",
            "Alatyr merge check",
            "Alatyr release",
        ]:
            if alias not in text:
                failures.append(f"{path.relative_to(ROOT)} missing alias {alias}")
    if "Alatyr team status" not in HELP.read_text(encoding="utf-8"):
        failures.append(f"{HELP.relative_to(ROOT)} missing alias Alatyr team status")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "OK: checked team collaboration rule, target records, lazy routing, "
        f"and {len(TEAM_OPERATIONS)} operations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

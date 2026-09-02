#!/usr/bin/env python3
"""Validate task-decomposition contracts in source templates."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
ASSISTANT = TARGET / ".ai" / "assistant"
FRAMEWORK_RULE = ROOT / "framework" / "task-decomposition.md"
ROUTER = ASSISTANT / "context-router.json"
POLICY = ASSISTANT / "task-decomposition.json"
PLAN_TEMPLATE = ASSISTANT / "templates" / "task-decomposition.md"
OPERATION_ROUTING = ASSISTANT / "flows" / "operation-routing.flow.md"
HELP = ASSISTANT / "help.md"
HELP_REFERENCE = ASSISTANT / "help-reference.md"
OPERATION_REQUEST = ASSISTANT / "templates" / "operation-request.md"
INSTALLED_REQUEST = ROOT / "installer" / "installed-operation-request-template.md"
COMPLETION_EVIDENCE = ASSISTANT / "templates" / "operation-completion-evidence.json"
DELEGATION_POLICY = ASSISTANT / "delegation-policy.json"
ROLE_CATALOG = ASSISTANT / "workers" / "role-catalog.json"
WORKER_ORCHESTRATION = ASSISTANT / "prompts" / "worker-orchestration.md"
WORKER_PLAN = ASSISTANT / "templates" / "worker-execution-plan.md"
TASK_PACKET = ASSISTANT / "templates" / "subagent-task-packet.md"
SMALL_TASK_EVIDENCE = ASSISTANT / "templates" / "small-task-evidence.md"
LARGE_TASK_FLOW = ASSISTANT / "flows" / "large-task-orchestration.flow.md"
LARGE_TASK_PACKET = ASSISTANT / "templates" / "large-task-operation-packet.md"

LEVEL_IDS = ["L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7"]
PRIMARY_ONLY_LEVELS = {"L0", "L6", "L7"}
WORKER_ELIGIBLE_LEVELS = {"L1", "L2", "L3", "L4", "L5"}
ROLE_IDS = {
    "explorer",
    "implementer",
    "test-runner",
    "documentation-worker",
    "reviewer",
    "fast-focused-worker",
}
LEVEL_FIELDS = {
    "id",
    "name",
    "use_when",
    "allowed_actions",
    "default_executor",
    "worker_roles",
    "delegation",
    "quality_gate",
}
QUALITY_GATES = {
    "one_level_per_task",
    "reject_dependency_cycles",
    "reject_overlapping_parallel_writes",
    "primary_owns_semantic_decisions",
    "primary_owns_final_convergence",
    "delegation_cannot_broaden_authorization",
    "escalate_on_new_relationship",
    "escalate_on_failed_validation",
    "escalation_loads_only_triggering_context",
}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def require_text(path: Path, values: list[str], failures: list[str]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        failures.append(str(exc))
        return
    normalized = text.casefold()
    for value in values:
        if value.casefold() not in normalized:
            failures.append(f"{path.relative_to(ROOT)} missing {value}")


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def validate_policy(policy: dict[str, Any], failures: list[str]) -> None:
    if policy.get("schema_version") != 1:
        failures.append("task-decomposition policy schema_version must be 1")
    if policy.get("policy_kind") != "target-task-decomposition-policy":
        failures.append("task-decomposition policy kind is invalid")
    if policy.get("portable_rule") != ".ai/framework/task-decomposition.md":
        failures.append("task-decomposition policy portable_rule is invalid")
    if policy.get("plan_template") != ".ai/assistant/templates/task-decomposition.md":
        failures.append("task-decomposition policy plan_template is invalid")
    if "non-trivial" not in str(policy.get("default_behavior", "")):
        failures.append("task-decomposition policy must route non-trivial work")

    levels = policy.get("levels")
    if not isinstance(levels, list):
        failures.append("task-decomposition policy levels must be a list")
        return
    level_ids = [
        level.get("id")
        for level in levels
        if isinstance(level, dict) and isinstance(level.get("id"), str)
    ]
    if level_ids != LEVEL_IDS:
        failures.append(f"task-decomposition levels must be {LEVEL_IDS}")
    for level in levels:
        if not isinstance(level, dict):
            failures.append("task-decomposition level must be an object")
            continue
        level_id = level.get("id")
        missing = sorted(LEVEL_FIELDS - set(level))
        if missing:
            failures.append(f"level {level_id} missing fields {missing}")
        roles = string_list(level.get("worker_roles"))
        unknown_roles = sorted(set(roles) - ROLE_IDS)
        if unknown_roles:
            failures.append(f"level {level_id} references unknown roles {unknown_roles}")
        if level_id in PRIMARY_ONLY_LEVELS and roles:
            failures.append(f"level {level_id} must remain primary-only")
        if level_id in {"L6", "L7"} and "not-allowed" not in str(
            level.get("delegation", "")
        ):
            failures.append(f"level {level_id} must not allow delegation")
        if level_id in PRIMARY_ONLY_LEVELS and level.get("default_executor") != "primary":
            failures.append(f"level {level_id} default executor must be primary")

    quality = policy.get("quality_gates")
    if not isinstance(quality, dict):
        failures.append("task-decomposition policy must define quality_gates")
    else:
        for gate in sorted(QUALITY_GATES):
            if quality.get(gate) is not True:
                failures.append(f"quality gate {gate} must be true")


def validate_router(router: dict[str, Any], failures: list[str]) -> None:
    decomposition = router.get("task_decomposition")
    if not isinstance(decomposition, dict):
        failures.append("context router missing task_decomposition")
        return
    expected = {
        "schema_version": 1,
        "policy": ".ai/assistant/task-decomposition.json",
        "plan_template": ".ai/assistant/templates/task-decomposition.md",
    }
    for key, value in expected.items():
        if decomposition.get(key) != value:
            failures.append(f"context router task_decomposition.{key} is invalid")
    for key in ["load_after", "use_when"]:
        if not string_list(decomposition.get(key)):
            failures.append(f"context router task_decomposition.{key} is empty")
    fields = router.get("context_receipt", {}).get("fields")
    if "task decomposition id and implementation levels" not in string_list(fields):
        failures.append("context receipt missing task decomposition evidence")


def validate_delegation(failures: list[str]) -> None:
    policy = load_object(DELEGATION_POLICY)
    if policy.get("decomposition_policy") != ".ai/assistant/task-decomposition.json":
        failures.append("delegation policy does not reference task decomposition")
    catalog = load_object(ROLE_CATALOG)
    if catalog.get("decomposition_policy") != ".ai/assistant/task-decomposition.json":
        failures.append("worker role catalog does not reference task decomposition")
    roles = catalog.get("roles")
    if not isinstance(roles, list):
        failures.append("worker role catalog roles must be a list")
        return
    for role in roles:
        if not isinstance(role, dict):
            failures.append("worker role must be an object")
            continue
        levels = string_list(role.get("implementation_levels"))
        if not levels:
            failures.append(f"worker role {role.get('id')} lacks implementation levels")
        unsupported = sorted(set(levels) - WORKER_ELIGIBLE_LEVELS)
        if unsupported:
            failures.append(
                f"worker role {role.get('id')} uses unsupported levels {unsupported}"
            )


def validate_completion_evidence(failures: list[str]) -> None:
    completion = load_object(COMPLETION_EVIDENCE)
    decomposition = completion.get("task_decomposition")
    if not isinstance(decomposition, dict):
        failures.append("operation completion evidence lacks task_decomposition")
        return
    for required in [
        "policy",
        "plan_id",
        "tasks",
        "primary_convergence",
        "delegation_used",
        "residual_risk",
    ]:
        if required not in decomposition:
            failures.append(f"operation completion task_decomposition missing {required}")


def main() -> int:
    failures: list[str] = []
    require_text(
        FRAMEWORK_RULE,
        [
            "# Task Decomposition",
            "ALATYR-DECOMPOSITION-001",
            "## Decomposition Sequence",
            "## Implementation Levels",
            "## Executor Selection",
            "## Quality Guard",
            "## Evidence",
            "## Rejection Criteria",
            "primary assistant",
            "local task for small work",
        ],
        failures,
    )
    require_text(
        PLAN_TEMPLATE,
        [
            "Implementation level:",
            "Executor decision:",
            "Selected worker role:",
            "Dependency cycles:",
            "## Primary Convergence",
        ],
        failures,
    )
    require_text(
        OPERATION_ROUTING,
        [
            ".ai/assistant/task-decomposition.json",
            ".ai/assistant/templates/task-decomposition.md",
            "decomposition plan",
            "implementation level",
        ],
        failures,
    )
    for path in [HELP, HELP_REFERENCE, OPERATION_REQUEST, INSTALLED_REQUEST]:
        require_text(
            path,
            [
                ".ai/assistant/task-decomposition.json",
                "implementation level",
            ],
            failures,
        )
    require_text(INSTALLED_REQUEST, ["ALATYR-DECOMPOSITION-001"], failures)
    for path in [
        WORKER_ORCHESTRATION,
        WORKER_PLAN,
        TASK_PACKET,
        SMALL_TASK_EVIDENCE,
        LARGE_TASK_FLOW,
        LARGE_TASK_PACKET,
    ]:
        require_text(path, ["Implementation level"], failures)

    try:
        validate_policy(load_object(POLICY), failures)
        validate_router(load_object(ROUTER), failures)
        validate_delegation(failures)
        validate_completion_evidence(failures)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: checked task decomposition rule, target routing, and worker levels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

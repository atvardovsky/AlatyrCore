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
POLICY = TARGET / ".ai" / "project" / "team-policy.json"
OPERATING_MODEL = TARGET / ".ai" / "project" / "team-operating-model.md"
REGISTRY = TARGET / ".ai" / "assistant" / "team" / "work-registry.json"
ACTIVE_INDEX = TARGET / ".ai" / "assistant" / "team" / "active-work-index.json"
BACKEND = TARGET / ".ai" / "assistant" / "team" / "backend-contract.json"
TASK_TEMPLATE = TARGET / ".ai" / "assistant" / "team" / "task-record-template.json"
CONTEXT_OVERLAY = TARGET / ".ai" / "assistant" / "team" / "context-overlay.json"
IDENTITY_FLOW = TARGET / ".ai" / "assistant" / "flows" / "team-identity.flow.md"
TASK_FLOW = TARGET / ".ai" / "assistant" / "flows" / "team-task-coordination.flow.md"
HANDOFF_FLOW = TARGET / ".ai" / "assistant" / "flows" / "team-handoff.flow.md"
DECISION_FLOW = TARGET / ".ai" / "assistant" / "flows" / "team-decision.flow.md"
REVIEW_FLOW = TARGET / ".ai" / "assistant" / "flows" / "team-review.flow.md"
GATE = TARGET / ".ai" / "assistant" / "gates" / "team-collaboration.md"
CHECKPOINT = TARGET / ".ai" / "assistant" / "templates" / "team-checkpoint.md"
HANDOFF = TARGET / ".ai" / "assistant" / "templates" / "team-handoff.md"
DECISION = TARGET / ".ai" / "assistant" / "templates" / "team-decision-record.md"
IDENTITY_EXAMPLE = TARGET / ".ai" / "assistant" / "templates" / "team-identity.example.json"
COLLABORATION_REVIEW = TARGET / ".ai" / "assistant" / "templates" / "team-collaboration-review.md"
SKILL = TARGET / ".ai" / "assistant" / "skills" / "team-collaboration" / "SKILL.md"
IGNORE = TARGET / ".ai" / ".gitignore"
CATALOG = TARGET / ".ai" / "assistant" / "operation-catalog.json"
ROUTER = TARGET / ".ai" / "assistant" / "context-router.json"
MANIFEST = TARGET / ".ai" / "alatyr.yaml"
MODULE_PROFILE = TARGET / ".ai" / "assistant" / "module-profile.md"
HELP = TARGET / ".ai" / "assistant" / "help.md"
HELP_REFERENCE = TARGET / ".ai" / "assistant" / "help-reference.md"

TEAM_OPERATIONS = {
    "team-identity",
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


def require_fields(
    data: dict[str, Any], fields: list[str], label: str, failures: list[str]
) -> None:
    for field in fields:
        if field not in data:
            failures.append(f"{label} missing {field}")


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
            "ignored local",
            "active-work index",
            "one record per task",
            "optimistic concurrency",
            "Local actor selection supports attribution",
            "backend contract",
            "schema-1 task entries",
            "not portable shell commands",
        ],
        failures,
    )
    require_text(
        OPERATING_MODEL,
        [
            ".ai/project/team-policy.json",
            "## Identity And Attribution",
            "## Coordination Backend",
            "## Concurrent Work",
            ".ai/local/team-identity.json",
            "not authentication",
        ],
        failures,
    )
    require_text(
        IDENTITY_FLOW,
        [
            "## Who Am I",
            "## Set Actor",
            "## Clear Actor",
            "enrollment proposal",
            "authentication",
        ],
        failures,
    )
    require_text(
        TASK_FLOW,
        [
            "active-work index",
            "observed record revision",
            "backend revision mismatch",
            "Regenerate the compact active-work index",
        ],
        failures,
    )
    require_text(
        HANDOFF_FLOW,
        ["task/backend revision", "atomically", "active-work index"],
        failures,
    )
    require_text(
        DECISION_FLOW,
        ["structured target policy", "observed task", "backend revision"],
        failures,
    )
    require_text(
        REVIEW_FLOW,
        ["implementer/reviewer separation", "task/backend record revisions"],
        failures,
    )
    require_text(
        GATE,
        [
            "## Before Any State-Changing Operation",
            "Current actor resolved",
            "Task writes never overwrite",
            "Global Git identity is never changed",
        ],
        failures,
    )
    require_text(SKILL, ["compact active-work index", "## Prohibited"], failures)
    require_text(CHECKPOINT, ["Task record revision:", "Backend revision:"], failures)
    require_text(HANDOFF, ["Task record revision:", "Assistant actor:"], failures)
    require_text(DECISION, ["Recorded by actor:", "Assistant actor:"], failures)
    require_text(
        COLLABORATION_REVIEW,
        ["## Aggregate Signals", "Do not rank individuals", "## Improvement Candidates"],
        failures,
    )
    require_text(IGNORE, ["local/"], failures)

    try:
        policy = load_json(POLICY)
        registry = load_json(REGISTRY)
        active_index = load_json(ACTIVE_INDEX)
        backend = load_json(BACKEND)
        task = load_json(TASK_TEMPLATE)
        overlay = load_json(CONTEXT_OVERLAY)
        identity = load_json(IDENTITY_EXAMPLE)
        catalog = load_json(CATALOG)
        router = load_json(ROUTER)
    except AssertionError as exc:
        failures.append(str(exc))
        policy = registry = active_index = backend = task = overlay = identity = {}
        catalog = router = {}

    if policy.get("schema_version") != 1 or policy.get("policy_kind") != "target-team-policy":
        failures.append("team policy identity is invalid")
    require_fields(
        policy,
        [
            "policy_revision",
            "owner_actor_id",
            "identity",
            "coordination_backend",
            "actors",
            "priorities",
            "review_policy",
            "decision_owners",
            "state_transitions",
            "conflict_policy",
        ],
        "team policy",
        failures,
    )
    identity_policy = policy.get("identity", {})
    if not isinstance(identity_policy, dict):
        failures.append("team policy identity must be an object")
    else:
        if identity_policy.get("git_identity_is_authoritative") is not False:
            failures.append("Git identity must not be authoritative by default")
        if identity_policy.get("local_identity_path") != ".ai/local/team-identity.json":
            failures.append("team policy local identity path is invalid")
    for field in ["actors", "priorities", "state_transitions"]:
        if not isinstance(policy.get(field), list) or not policy[field]:
            failures.append(f"team policy {field} must contain a placeholder contract")

    if registry.get("schema_version") != 2:
        failures.append("team work registry schema_version must be 2")
    if registry.get("registry_kind") != "target-team-work-registry":
        failures.append("team work registry kind is invalid")
    expected_registry_paths = {
        "team_policy": ".ai/project/team-policy.json",
        "active_work_index": ".ai/assistant/team/active-work-index.json",
        "backend_contract": ".ai/assistant/team/backend-contract.json",
        "task_records_directory": ".ai/assistant/team/tasks",
        "task_record_template": ".ai/assistant/team/task-record-template.json",
    }
    for field, expected in expected_registry_paths.items():
        if registry.get(field) != expected:
            failures.append(f"registry {field} must point to {expected}")
    if not isinstance(registry.get("registry_revision"), int):
        failures.append("registry revision must be an integer")
    if "tasks" in registry:
        failures.append("schema-2 registry must not contain a monolithic tasks array")

    if active_index.get("schema_version") != 1 or active_index.get("index_kind") != "target-team-active-work-index":
        failures.append("active-work index identity is invalid")
    if active_index.get("source_registry") != ".ai/assistant/team/work-registry.json":
        failures.append("active-work index source registry is invalid")
    if not isinstance(active_index.get("entries"), list):
        failures.append("active-work index entries must be a list")

    if backend.get("schema_version") != 1 or backend.get("contract_kind") != "target-team-backend-contract":
        failures.append("team backend contract identity is invalid")
    require_fields(
        backend,
        [
            "backend_id",
            "backend_mode",
            "provider",
            "consistency_model",
            "write_strategy",
            "idempotency_policy",
            "conflict_policy",
            "permission_policy",
            "authentication_policy",
            "extension_id",
            "validation",
        ],
        "team backend contract",
        failures,
    )
    require_string_list(backend.get("capabilities"), "backend capabilities", failures)

    if task.get("schema_version") != 2 or task.get("record_kind") != "target-team-task":
        failures.append("task record template identity is invalid")
    require_fields(
        task,
        [
            "record_revision",
            "expected_revision",
            "backend_revision",
            "requested_by_actor_id",
            "last_updated_by_actor_id",
            "assistant_actor_id",
            "transition",
            "reviewed_head_revision",
            "reviewed_base_revision",
        ],
        "task record template",
        failures,
    )
    if not isinstance(task.get("record_revision"), int) or not isinstance(
        task.get("expected_revision"), int
    ):
        failures.append("task record revisions must be integers")
    claim = task.get("claim")
    if not isinstance(claim, dict):
        failures.append("task claim must be an object")
    else:
        require_fields(
            claim,
            ["lease_id", "heartbeat_at", "backend_revision", "state"],
            "task claim",
            failures,
        )

    if overlay.get("schema_version") != 2 or overlay.get("overlay_id") != "team-active":
        failures.append("team-active overlay identity is invalid")
    if set(overlay.get("operation_candidates", [])) != TEAM_OPERATIONS:
        failures.append("team-active operation candidates must match team operations")
    if overlay.get("required_context") != [
        ".ai/assistant/team/active-work-index.json"
    ]:
        failures.append("team-active must preflight only the active-work index")
    conditional = {
        entry.get("path")
        for entry in overlay.get("conditional_context", [])
        if isinstance(entry, dict)
    }
    for required in [
        ".ai/framework/team-collaboration.md",
        ".ai/project/team-policy.json",
        ".ai/assistant/team/work-registry.json",
        ".ai/assistant/team/backend-contract.json",
        ".ai/assistant/gates/team-collaboration.md",
    ]:
        if required not in conditional:
            failures.append(f"team-active conditional context missing {required}")

    if identity.get("schema_version") != 1 or identity.get("identity_kind") != "local-team-identity":
        failures.append("local identity example is invalid")
    if identity.get("selected_by") != "explicit-user-request":
        failures.append("local identity must require explicit user selection")

    operations = catalog.get("operations", [])
    operation_by_id = {
        item.get("id"): item for item in operations if isinstance(item, dict)
    }
    missing_operations = sorted(TEAM_OPERATIONS - set(operation_by_id))
    if missing_operations:
        failures.append(f"operation catalog missing team operations {missing_operations}")
    for operation_id in TEAM_OPERATIONS:
        if operation_by_id.get(operation_id, {}).get("required_module") != "team-collaboration":
            failures.append(f"{operation_id} must require team-collaboration")
    for operation_id in READ_ONLY_OPERATIONS:
        if operation_by_id.get(operation_id, {}).get("allowed_actions") != ["read-only"]:
            failures.append(f"{operation_id} must be read-only")
    if operation_by_id.get("team-identity", {}).get("allowed_actions") != [
        "read-only",
        "adapter-only",
    ]:
        failures.append("team-identity must restrict writes to adapter-only")

    route = router.get("task_scale_overlays", {}).get("team-active", {})
    if route.get("descriptor") != ".ai/assistant/team/context-overlay.json":
        failures.append("context router team-active descriptor is invalid")
    route_signals = " ".join(route.get("use_when", []))
    if "write operation" not in route_signals or "active" not in route_signals:
        failures.append("context router must trigger team preflight for writes")
    for forbidden in [
        ".ai/project/team-policy.json",
        ".ai/assistant/team/active-work-index.json",
        ".ai/assistant/team/work-registry.json",
    ]:
        if forbidden in router.get("bootstrap_context", []):
            failures.append(f"team state must stay outside bootstrap: {forbidden}")

    manifest_text = MANIFEST.read_text(encoding="utf-8")
    module_text = MODULE_PROFILE.read_text(encoding="utf-8")
    for required in [
        ".ai/project/team-policy.json",
        ".ai/assistant/team/active-work-index.json",
        ".ai/assistant/team/backend-contract.json",
        ".ai/assistant/team/task-record-template.json",
        ".ai/local/team-identity.json",
        ".ai/assistant/flows/team-identity.flow.md",
        ".ai/assistant/templates/team-collaboration-review.md",
        ".ai/assistant/skills/team-collaboration/SKILL.md",
    ]:
        if required not in manifest_text:
            failures.append(f"manifest missing team path {required}")
        if required != ".ai/local/team-identity.json" and required not in module_text:
            failures.append(f"module profile missing team path {required}")

    combined_help = " ".join(
        (
            HELP.read_text(encoding="utf-8")
            + HELP_REFERENCE.read_text(encoding="utf-8")
        ).split()
    )
    for alias in ["Alatyr set actor", "Alatyr who am I", "Alatyr clear actor", "Alatyr team status"]:
        if alias not in combined_help:
            failures.append(f"help missing alias {alias}")

    if not re.search(r"state-changing operation.*active-work", FRAMEWORK.read_text(encoding="utf-8"), re.DOTALL):
        failures.append("framework missing automatic active-work preflight contract")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "OK: checked team policy, local identity, active-work preflight, "
        f"schema-2 task records, backend contract, and {len(TEAM_OPERATIONS)} operations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

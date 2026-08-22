#!/usr/bin/env python3
"""Validate portable worker delegation contracts and target templates."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
ASSISTANT = TARGET / ".ai" / "assistant"
FRAMEWORK = ROOT / "framework" / "subagent-delegation.md"
POLICY = ASSISTANT / "delegation-policy.json"
ROLE_CATALOG = ASSISTANT / "workers" / "role-catalog.json"
ROLE_DIR = ASSISTANT / "workers" / "roles"
ORCHESTRATION = ASSISTANT / "prompts" / "worker-orchestration.md"
EXECUTION_PLAN = ASSISTANT / "templates" / "worker-execution-plan.md"
NATIVE_BINDING = ASSISTANT / "templates" / "native-worker-binding.md"
PACKET = ASSISTANT / "templates" / "subagent-task-packet.md"
RESULT = ASSISTANT / "templates" / "worker-result.md"
FLOW = ASSISTANT / "flows" / "subagent-delegation.flow.md"
OVERLAY = ASSISTANT / "context" / "task-scales" / "delegated-execution.json"
ROUTER = ASSISTANT / "context-router.json"
MATRIX = ASSISTANT / "bridge-capability-matrix.md"
CAPABILITIES = ASSISTANT / "assistant-capabilities"
CAPABILITY_INDEX = ASSISTANT / "assistant-capabilities.json"
SURFACES = ROOT / "conformance" / "runs" / "assistant-surfaces.json"
CONFORMANCE = ROOT / "conformance" / "operations" / "worker-delegation.json"
BRIDGE_MANIFEST = ROOT / "tools" / "bridge_template_manifest.json"

ROLE_IDS = {
    "explorer",
    "implementer",
    "test-runner",
    "documentation-worker",
    "reviewer",
    "fast-focused-worker",
}
POLICY_FIELDS = {
    "schema_version",
    "policy_kind",
    "state",
    "owner",
    "decision_mode",
    "default_preference",
    "max_parallel_delegates",
    "role_catalog",
    "enabled_role_ids",
    "requirements",
    "eligible_work",
    "prohibited_work",
    "retry_policy",
    "conflict_policy",
    "result_policy",
    "privacy_and_retention",
    "validation",
    "review_triggers",
}
ROLE_FIELDS = {
    "id",
    "state",
    "prompt",
    "use_when",
    "action_ceiling",
    "write_mode",
    "max_files",
    "max_context_words",
    "required_output",
    "prohibited_responsibilities",
}
CAPABILITY_FIELDS = {
    "route",
    "dispatch_backend",
    "external_dispatcher",
    "client_product",
    "runtime_variant",
    "native_subagents",
    "automatic_delegation",
    "explicit_delegation",
    "project_worker_definitions",
    "worker_definition_format",
    "worker_definition_paths",
    "tool_restrictions",
    "write_isolation",
    "background_execution",
    "nested_delegation",
    "model_override",
    "parallel_dispatch",
    "actual_model_evidence",
    "role_bindings",
    "verified_at",
    "client_version",
    "evidence",
    "expires_at",
    "review_triggers",
}
ROLE_BINDING_FIELDS = {
    "role_id",
    "selection_mode",
    "model",
    "reasoning",
    "availability",
    "evidence",
    "expires_at",
}
PROVIDER_TERMS = {
    "openai",
    "codex",
    "anthropic",
    "claude",
    "gemini",
    "github copilot",
    "cursor",
    "devin",
    "windsurf",
    "gpt-",
}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return value


def require_text(path: Path, values: list[str], failures: list[str]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        failures.append(str(exc))
        return
    for value in values:
        if value not in text:
            failures.append(f"{path.relative_to(ROOT)} missing {value}")


def placeholder(value: object) -> bool:
    return isinstance(value, str) and "{" in value and "}" in value


def require_placeholder(owner: str, value: object, failures: list[str]) -> None:
    if not placeholder(value):
        failures.append(f"{owner} must remain placeholder-based")


def main() -> int:
    failures: list[str] = []

    require_text(
        FRAMEWORK,
        [
            "## Responsibility Boundary",
            "## Task Planning Contract",
            "## Worker Role Catalog",
            "## Capability Negotiation",
            "## Normalized Result Contract",
            "## Retry And Conflict Handling",
            "## Dispatch And Convergence",
            "primary assistant",
            "actual model",
            "thin execution",
        ],
        failures,
    )
    require_text(
        FLOW,
        [
            "## Activation Gate",
            "## Capability And Role Selection",
            "## Task Graph And Readiness",
            "## Packet And Dispatch",
            "## Result Review And Convergence",
            ".ai/assistant/prompts/worker-orchestration.md",
            ".ai/assistant/templates/worker-result.md",
        ],
        failures,
    )
    require_text(
        ORCHESTRATION,
        [
            "primary assistant remains responsible",
            "worker-execution-plan.md",
            "capability record",
            "Normalize every return",
            "suggestion-only or sequential-primary fallback",
        ],
        failures,
    )
    require_text(
        EXECUTION_PLAN,
        [
            "Base revision:",
            "Authorized action phases:",
            "## Task Graph",
            "Only the primary assistant computes readiness",
            "Expected write scope:",
            "## Conflict Review",
            "## Primary Convergence",
        ],
        failures,
    )
    require_text(
        PACKET,
        [
            "Packet ID:",
            "Task ID:",
            "Execution plan ID:",
            "Base revision:",
            "Allowed actions:",
            "Allowed files or surfaces:",
            "Role prompt:",
            "Capability evidence:",
            ".ai/assistant/templates/worker-result.md",
            "## Primary Review",
        ],
        failures,
    )
    require_text(
        RESULT,
        [
            "Result ID:",
            "Task ID:",
            "Base revision observed:",
            "Actual assistant surface:",
            "Scope violation:",
            "Architecture or semantic deviation:",
            "Authorization or approval concern:",
            "evidence for primary review",
        ],
        failures,
    )
    require_text(
        NATIVE_BINDING,
        [
            "Native definition format:",
            "Native definition path:",
            "Role prompt:",
            "The native definition must stay thin",
            "record its exact path",
            "sequential-primary fallback",
        ],
        failures,
    )

    portable_paths = [
        FRAMEWORK,
        POLICY,
        ROLE_CATALOG,
        ORCHESTRATION,
        EXECUTION_PLAN,
        NATIVE_BINDING,
        PACKET,
        RESULT,
        FLOW,
        OVERLAY,
    ]
    portable_paths.extend(sorted(ROLE_DIR.glob("*.md")))
    for path in portable_paths:
        try:
            text = path.read_text(encoding="utf-8").casefold()
        except OSError as exc:
            failures.append(str(exc))
            continue
        for term in sorted(PROVIDER_TERMS):
            if term in text:
                failures.append(
                    f"{path.relative_to(ROOT)} hard-codes provider term {term}"
                )

    try:
        policy = load_object(POLICY)
        catalog = load_object(ROLE_CATALOG)
        overlay = load_object(OVERLAY)
        router = load_object(ROUTER)
        capability_index = load_object(CAPABILITY_INDEX)
        surfaces = load_object(SURFACES).get("surfaces")
        conformance = load_object(CONFORMANCE)
        bridge_manifest = load_object(BRIDGE_MANIFEST)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))
        policy, catalog, overlay, router, capability_index, conformance, bridge_manifest = ({},) * 7
        surfaces = []

    missing_policy = sorted(POLICY_FIELDS - set(policy))
    if missing_policy:
        failures.append(f"delegation policy missing fields {missing_policy}")
    if policy.get("schema_version") != 2:
        failures.append("delegation policy schema_version must be 2")
    if policy.get("policy_kind") != "target-subagent-delegation-policy":
        failures.append("delegation policy kind is incorrect")
    if policy.get("role_catalog") != ".ai/assistant/workers/role-catalog.json":
        failures.append("delegation policy role_catalog path is incorrect")
    for field in [
        "state",
        "owner",
        "decision_mode",
        "default_preference",
        "max_parallel_delegates",
        "privacy_and_retention",
    ]:
        if field in policy:
            require_placeholder(f"delegation policy {field}", policy[field], failures)
    enabled_role_ids = policy.get("enabled_role_ids")
    if (
        not isinstance(enabled_role_ids, list)
        or not enabled_role_ids
        or any(not placeholder(value) for value in enabled_role_ids)
    ):
        failures.append(
            "delegation policy enabled_role_ids must remain a non-empty placeholder list"
        )
    retry = policy.get("retry_policy")
    if (
        not isinstance(retry, dict)
        or retry.get("retry_only_when_scope_unchanged") is not True
    ):
        failures.append("delegation policy must prevent scope-expanding retries")
    conflict = policy.get("conflict_policy")
    expected_conflicts = {
        "overlapping_writes": "reject-concurrent-dispatch",
        "contradictory_results": "return-to-primary",
        "stale_baseline": "revalidate-before-integration",
        "scope_violation": "reject-result",
    }
    if not isinstance(conflict, dict) or any(
        conflict.get(key) != value for key, value in expected_conflicts.items()
    ):
        failures.append("delegation policy conflict guards are incomplete")
    result_policy = policy.get("result_policy")
    expected_results = {
        "accept_out_of_scope_changes": False,
        "accept_unvalidated_changes": False,
        "require_primary_review": True,
        "require_actual_model_or_unverified_status": True,
        "require_normalized_worker_result": True,
    }
    if not isinstance(result_policy, dict) or any(
        result_policy.get(key) is not value
        for key, value in expected_results.items()
    ):
        failures.append("delegation result policy guards are incomplete")

    if (
        catalog.get("schema_version") != 1
        or catalog.get("catalog_kind") != "target-worker-role-catalog"
    ):
        failures.append("worker role catalog identity is invalid")
    if catalog.get("result_template") != ".ai/assistant/templates/worker-result.md":
        failures.append("worker role catalog result template is invalid")
    roles = catalog.get("roles")
    seen_roles: set[str] = set()
    if not isinstance(roles, list):
        failures.append("worker role catalog roles must be a list")
        roles = []
    for role in roles:
        if not isinstance(role, dict):
            failures.append("worker role catalog contains a non-object role")
            continue
        missing = sorted(ROLE_FIELDS - set(role))
        if missing:
            failures.append(
                f"worker role {role.get('id', '<unknown>')} missing {missing}"
            )
        role_id = role.get("id")
        if not isinstance(role_id, str) or role_id in seen_roles:
            failures.append(f"invalid or duplicate worker role ID {role_id}")
            continue
        seen_roles.add(role_id)
        expected_prompt = f".ai/assistant/workers/roles/{role_id}.md"
        if (
            role.get("prompt") != expected_prompt
            or not (TARGET / expected_prompt).is_file()
        ):
            failures.append(f"worker role {role_id} has no matching prompt")
        if role.get("required_output") != "normalized-worker-result":
            failures.append(
                f"worker role {role_id} must require normalized-worker-result"
            )
    if seen_roles != ROLE_IDS:
        failures.append(
            "worker role catalog IDs differ: "
            f"expected {sorted(ROLE_IDS)}, got {sorted(seen_roles)}"
        )

    expected_context = {
        ".ai/framework/subagent-delegation.md",
        ".ai/assistant/delegation-policy.json",
        ".ai/assistant/workers/role-catalog.json",
        ".ai/assistant/prompts/worker-orchestration.md",
        ".ai/assistant/flows/subagent-delegation.flow.md",
        ".ai/assistant/templates/worker-execution-plan.md",
        ".ai/assistant/templates/subagent-task-packet.md",
        ".ai/assistant/templates/worker-result.md",
        ".ai/assistant/assistant-capabilities.json",
    }
    overlay_context = overlay.get("required_context")
    if (
        overlay.get("id") != "delegated-execution"
        or overlay.get("required_module") != "subagent-delegation"
    ):
        failures.append("delegated execution overlay identity is incorrect")
    if not isinstance(overlay_context, list) or not expected_context.issubset(
        set(overlay_context)
    ):
        failures.append("delegated execution overlay required_context is incomplete")
    task_scale_overlays = router.get("task_scale_overlays")
    route = (
        task_scale_overlays.get("delegated-execution")
        if isinstance(task_scale_overlays, dict)
        else None
    )
    if (
        not isinstance(route, dict)
        or route.get("descriptor")
        != ".ai/assistant/context/task-scales/delegated-execution.json"
    ):
        failures.append("context router does not select delegated-execution overlay")

    try:
        matrix_text = MATRIX.read_text(encoding="utf-8")
    except OSError as exc:
        failures.append(str(exc))
        matrix_text = ""
    if not isinstance(surfaces, list):
        failures.append("assistant surface list is invalid")
        surfaces = []
    surface_ids = {
        surface.get("id")
        for surface in surfaces
        if isinstance(surface, dict) and isinstance(surface.get("id"), str)
    }
    indexed_surfaces = capability_index.get("surfaces")
    if not isinstance(indexed_surfaces, dict) or set(indexed_surfaces) != surface_ids:
        failures.append(
            "assistant capability index must cover every supported surface exactly"
        )
        indexed_surfaces = {}
    scalar_capability_fields = CAPABILITY_FIELDS - {
        "worker_definition_paths",
        "role_bindings",
        "review_triggers",
    }
    for surface_id in sorted(surface_ids):
        path = CAPABILITIES / f"{surface_id}.json"
        expected_path = f".ai/assistant/assistant-capabilities/{surface_id}.json"
        if indexed_surfaces.get(surface_id) != expected_path:
            failures.append(
                f"assistant capability index has an invalid path for {surface_id}"
            )
        try:
            record = load_object(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            failures.append(str(exc))
            continue
        delegation = record.get("subagent_delegation")
        if not isinstance(delegation, dict):
            failures.append(f"{surface_id} has no subagent_delegation capability")
            continue
        missing = sorted(CAPABILITY_FIELDS - set(delegation))
        if missing:
            failures.append(f"{surface_id} delegation capability missing {missing}")
        for field in scalar_capability_fields:
            if field in delegation:
                require_placeholder(
                    f"{surface_id} delegation capability {field}",
                    delegation[field],
                    failures,
                )
        paths = delegation.get("worker_definition_paths")
        if (
            not isinstance(paths, list)
            or not paths
            or any(not placeholder(value) for value in paths)
        ):
            failures.append(
                f"{surface_id} worker_definition_paths must remain a placeholder list"
            )
        bindings = delegation.get("role_bindings")
        if (
            not isinstance(bindings, list)
            or not bindings
            or not isinstance(bindings[0], dict)
        ):
            failures.append(
                f"{surface_id} role_bindings must contain a template binding"
            )
        else:
            missing_binding = sorted(ROLE_BINDING_FIELDS - set(bindings[0]))
            if missing_binding:
                failures.append(
                    f"{surface_id} role binding missing {missing_binding}"
                )
            for field in ROLE_BINDING_FIELDS:
                if field in bindings[0]:
                    require_placeholder(
                        f"{surface_id} role binding {field}",
                        bindings[0][field],
                        failures,
                    )
        reference = (
            "Subagent delegation capability record: " f"`{expected_path}`"
        )
        if reference not in matrix_text:
            failures.append(
                f"bridge matrix missing delegation record for {surface_id}"
            )

    cases = conformance.get("cases")
    expected_cases = {
        "bounded-read-only-exploration": "eligible",
        "overlapping-write-scopes": "reject",
        "unresolved-architecture-decision": "primary-only",
        "scope-violating-result": "reject-result",
        "unsupported-surface": "sequential-primary-fallback",
    }
    actual_cases = {
        case.get("id"): case.get("expected_outcome")
        for case in cases
        if isinstance(cases, list) and isinstance(case, dict)
    }
    if actual_cases != expected_cases:
        failures.append(
            "worker delegation conformance cases are incomplete or inconsistent"
        )

    bridge_templates = bridge_manifest.get("templates")
    if not isinstance(bridge_templates, list) or not bridge_templates:
        failures.append("bridge template manifest has no templates")
        bridge_templates = []
    for entry in bridge_templates:
        path_value = entry.get("path") if isinstance(entry, dict) else None
        if not isinstance(path_value, str):
            failures.append("bridge template manifest contains an invalid path")
            continue
        require_text(
            ROOT / path_value,
            [".ai/assistant/prompts/worker-orchestration.md"],
            failures,
        )

    for path in [
        ASSISTANT / "flows" / "operation-routing.flow.md",
        ASSISTANT / "templates" / "operation-request.md",
        ROOT / "installer" / "installed-operation-request-template.md",
    ]:
        require_text(path, ["Delegation preference"], failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "OK: checked portable worker policy, six roles, task/result contracts, "
        f"five conformance cases, and {len(surface_ids)} capability records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

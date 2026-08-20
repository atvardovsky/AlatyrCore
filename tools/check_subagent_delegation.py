#!/usr/bin/env python3
"""Validate source and target-template subagent delegation contracts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
FRAMEWORK = ROOT / "framework" / "subagent-delegation.md"
POLICY = TARGET / ".ai" / "assistant" / "delegation-policy.json"
FLOW = TARGET / ".ai" / "assistant" / "flows" / "subagent-delegation.flow.md"
PACKET = TARGET / ".ai" / "assistant" / "templates" / "subagent-task-packet.md"
OVERLAY = (
    TARGET
    / ".ai"
    / "assistant"
    / "context"
    / "task-scales"
    / "delegated-execution.json"
)
ROUTER = TARGET / ".ai" / "assistant" / "context-router.json"
MATRIX = TARGET / ".ai" / "assistant" / "bridge-capability-matrix.md"
CAPABILITIES = TARGET / ".ai" / "assistant" / "assistant-capabilities"
CAPABILITY_INDEX = TARGET / ".ai" / "assistant" / "assistant-capabilities.json"
SURFACES = ROOT / "conformance" / "runs" / "assistant-surfaces.json"

FRAMEWORK_REQUIRED = [
    "## Responsibility Boundary",
    "## Activation Gate",
    "## Fast Focused Worker",
    "## Non-Delegable Work",
    "## Capability Negotiation",
    "## Delegation Packet",
    "## Dispatch And Convergence",
    "## Cost And Performance Evidence",
    "primary assistant",
    "actual model",
    "approved external dispatcher",
    "suggestion-only handoff",
]
FLOW_REQUIRED = [
    "## Activation Gate",
    "## Capability And Role Selection",
    "## Packet And Dispatch",
    "## Result Review And Convergence",
    "delegated-execution",
    ".ai/assistant/delegation-policy.json",
    ".ai/assistant/templates/subagent-task-packet.md",
    "approved target AI-infrastructure dispatcher",
]
PACKET_REQUIRED = [
    "Packet ID:",
    "Parent operation ID:",
    "Goal:",
    "Non-goals:",
    "Local acceptance criteria:",
    "Required context:",
    "Excluded context:",
    "Allowed actions:",
    "Allowed files or surfaces:",
    "Concurrent packets and write-isolation decision:",
    "Requested model or selection mode:",
    "Dispatch backend:",
    "External dispatcher item:",
    "Capability evidence:",
    "Fallback:",
    "Actual role/model:",
    "## Primary Review",
]
POLICY_FIELDS = {
    "schema_version",
    "policy_kind",
    "state",
    "owner",
    "decision_mode",
    "default_preference",
    "max_parallel_delegates",
    "requirements",
    "eligible_work",
    "prohibited_work",
    "roles",
    "result_policy",
    "privacy_and_retention",
    "validation",
    "review_triggers",
}
ROLE_FIELDS = {
    "id",
    "state",
    "use_when",
    "allowed_actions",
    "allowed_tools",
    "max_files",
    "max_context_words",
    "model_binding",
    "required_validation",
    "fallback",
}
MODEL_FIELDS = {
    "assistant_surface",
    "selection_mode",
    "model",
    "availability",
    "verified_at",
    "client_version",
    "evidence",
    "expires_at",
}
CAPABILITY_FIELDS = {
    "route",
    "dispatch_backend",
    "external_dispatcher",
    "native_subagents",
    "model_override",
    "parallel_dispatch",
    "actual_model_evidence",
    "verified_at",
    "client_version",
    "evidence",
    "expires_at",
    "review_triggers",
}
PORTABLE_PROVIDER_TERMS = {
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


def main() -> int:
    failures: list[str] = []
    require_text(FRAMEWORK, FRAMEWORK_REQUIRED, failures)
    require_text(FLOW, FLOW_REQUIRED, failures)
    require_text(PACKET, PACKET_REQUIRED, failures)
    for path in [FRAMEWORK, POLICY, FLOW, PACKET, OVERLAY]:
        try:
            text = path.read_text(encoding="utf-8").casefold()
        except OSError as exc:
            failures.append(str(exc))
            continue
        for term in sorted(PORTABLE_PROVIDER_TERMS):
            if term in text:
                failures.append(
                    f"{path.relative_to(ROOT)} hard-codes provider term {term}"
                )

    try:
        policy = load_object(POLICY)
        overlay = load_object(OVERLAY)
        router = load_object(ROUTER)
        capability_index = load_object(CAPABILITY_INDEX)
        surfaces = load_object(SURFACES).get("surfaces")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))
        policy = {}
        overlay = {}
        router = {}
        capability_index = {}
        surfaces = []

    missing_policy = sorted(POLICY_FIELDS - set(policy))
    if missing_policy:
        failures.append(f"delegation policy missing fields {missing_policy}")
    if policy.get("schema_version") != 1:
        failures.append("delegation policy schema_version must be 1")
    if policy.get("policy_kind") != "target-subagent-delegation-policy":
        failures.append("delegation policy kind is incorrect")
    for field in [
        "state",
        "owner",
        "decision_mode",
        "default_preference",
        "max_parallel_delegates",
        "privacy_and_retention",
    ]:
        if field in policy and not placeholder(policy[field]):
            failures.append(f"delegation policy {field} must remain placeholder-based")

    roles = policy.get("roles")
    if not isinstance(roles, list) or not roles or not isinstance(roles[0], dict):
        failures.append("delegation policy must define a role object")
    else:
        role = roles[0]
        missing_role = sorted(ROLE_FIELDS - set(role))
        if missing_role:
            failures.append(f"delegation role missing fields {missing_role}")
        if role.get("id") != "fast-focused-worker":
            failures.append("delegation policy must define fast-focused-worker")
        binding = role.get("model_binding")
        if not isinstance(binding, dict):
            failures.append("fast-focused-worker model_binding must be an object")
        else:
            missing_model = sorted(MODEL_FIELDS - set(binding))
            if missing_model:
                failures.append(f"model binding missing fields {missing_model}")
            for field in MODEL_FIELDS:
                if field in binding and not placeholder(binding[field]):
                    failures.append(f"model binding {field} must be placeholder-based")

    expected_context = {
        ".ai/framework/subagent-delegation.md",
        ".ai/assistant/delegation-policy.json",
        ".ai/assistant/flows/subagent-delegation.flow.md",
        ".ai/assistant/templates/subagent-task-packet.md",
        ".ai/assistant/assistant-capabilities.json",
    }
    if overlay.get("id") != "delegated-execution":
        failures.append("delegated execution overlay ID is incorrect")
    if overlay.get("required_module") != "subagent-delegation":
        failures.append("delegated execution overlay module is incorrect")
    overlay_context = overlay.get("required_context")
    if not isinstance(overlay_context, list) or not expected_context.issubset(
        set(overlay_context)
    ):
        failures.append("delegated execution overlay required_context is incomplete")
    routed = router.get("task_scale_overlays")
    route = routed.get("delegated-execution") if isinstance(routed, dict) else None
    expected_descriptor = (
        ".ai/assistant/context/task-scales/delegated-execution.json"
    )
    if not isinstance(route, dict) or route.get("descriptor") != expected_descriptor:
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
    for surface in surfaces:
        surface_id = surface.get("id") if isinstance(surface, dict) else None
        if not isinstance(surface_id, str) or not surface_id:
            failures.append("assistant surface has no valid ID")
            continue
        path = CAPABILITIES / f"{surface_id}.json"
        expected_index_path = (
            f".ai/assistant/assistant-capabilities/{surface_id}.json"
        )
        if indexed_surfaces.get(surface_id) != expected_index_path:
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
        for field in CAPABILITY_FIELDS - {"review_triggers"}:
            if field in delegation and not placeholder(delegation[field]):
                failures.append(
                    f"{surface_id} delegation capability {field} must be placeholder-based"
                )
        expected_reference = (
            "Subagent delegation capability record: "
            f"`.ai/assistant/assistant-capabilities/{surface_id}.json`"
        )
        if expected_reference not in matrix_text:
            failures.append(f"bridge matrix missing delegation record for {surface_id}")

    for path in [
        TARGET / ".ai" / "assistant" / "flows" / "operation-routing.flow.md",
        TARGET / ".ai" / "assistant" / "templates" / "operation-request.md",
        ROOT / "installer" / "installed-operation-request-template.md",
    ]:
        require_text(path, ["Delegation preference"], failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "OK: checked subagent delegation policy, overlay, packet, and "
        f"{len(surfaces)} assistant capability records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

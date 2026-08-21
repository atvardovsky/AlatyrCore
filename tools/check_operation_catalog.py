#!/usr/bin/env python3
"""Validate the target operation catalog and control-surface contracts.

This validates AlatyrCore source templates only. It is not a portable
framework requirement for target projects.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
CATALOG = TARGET / ".ai" / "assistant" / "operation-catalog.json"
INDEX = TARGET / ".ai" / "assistant" / "operation-index.json"
ROUTER = TARGET / ".ai" / "assistant" / "context-router.json"
HELP_REFERENCE = TARGET / ".ai" / "assistant" / "help-reference.md"
MANIFEST = TARGET / ".ai" / "alatyr.yaml"
ROUTING_FLOW = TARGET / ".ai" / "assistant" / "flows" / "operation-routing.flow.md"
HEALTH_FLOW = TARGET / ".ai" / "assistant" / "flows" / "adapter-health.flow.md"
PREVIEW = TARGET / ".ai" / "assistant" / "templates" / "pre-change-preview.md"

EXPECTED_OPERATIONS = {
    "help",
    "adapter-health",
    "create-project-blueprint",
    "architecture-assistance",
    "recheck-after-installation",
    "recheck-after-framework-update",
    "product-change",
    "large-task",
    "team-identity",
    "team-status",
    "team-task",
    "team-conflict-review",
    "team-handoff",
    "team-decision",
    "team-review",
    "team-merge-check",
    "logical-integrity-review",
    "diagram-discussion",
    "ai-infrastructure-inventory",
    "ai-infrastructure-recommendation",
    "skill-adaptation",
    "drift-review",
    "documentation-sync",
    "project-vocabulary",
    "test-first-configuration",
    "test-first-change",
    "extension-management",
    "dependency-knowledge",
    "workspace-mode",
    "adapter-maturity-review",
}

CATALOG_PATHS = {
    "compact_help": ".ai/assistant/help.md",
    "human_reference": ".ai/assistant/help-reference.md",
    "routing_flow": ".ai/assistant/flows/operation-routing.flow.md",
    "health_flow": ".ai/assistant/flows/adapter-health.flow.md",
    "pre_change_preview": ".ai/assistant/templates/pre-change-preview.md",
    "action_authorization_policy": ".ai/assistant/policies/action-authorization.json",
    "module_profile": ".ai/assistant/module-profile.md",
}

AUTHORIZATION_PHASES = ["inspect", "modify", "commit", "publish", "live-external"]

REQUIRED_OPERATION_STRINGS = ["id", "title", "summary", "required_module", "flow", "preview"]
REQUIRED_OPERATION_LISTS = [
    "use_when",
    "context_profiles",
    "minimum_inputs",
    "allowed_actions",
    "aliases",
    "final_evidence",
]
ALLOWED_ACTIONS = {
    "read-only",
    "docs-only",
    "adapter-only",
    "code-and-tests",
    "full-with-approval",
}
ALLOWED_MODULES = {
    "core-profile",
    "blueprint-change",
    "ai-infrastructure",
    "large-task-orchestration",
    "team-collaboration",
    "diagrams",
    "architecture-knowledge",
    "project-vocabulary",
    "test-first-development",
    "dependency-knowledge",
    "workspace-modes",
}
ALLOWED_PREVIEW = {"never", "risk-gated"}
ALLOWED_PROFILES = {
    "docs-local",
    "code-local",
    "business-change",
    "architecture-change",
    "data-change",
    "security-sensitive",
    "ai-infrastructure",
    "framework-upgrade",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AssertionError(f"missing {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(data, dict):
        raise AssertionError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return data


def string_list(value: Any, label: str, failures: list[str]) -> list[str]:
    if not isinstance(value, list):
        failures.append(f"{label} must be a string list")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            failures.append(f"{label}[{index}] must be a non-empty string")
        else:
            result.append(item)
    return result


def target_path_exists(value: str) -> bool:
    return value.startswith(".ai/") and (TARGET / value).exists()


def main() -> int:
    failures: list[str] = []
    try:
        catalog = load_json(CATALOG)
        operation_index = load_json(INDEX)
        router = load_json(ROUTER)
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if catalog.get("schema_version") != 1:
        failures.append("operation catalog schema_version must be 1")
    if catalog.get("catalog_kind") != "target-operation-catalog":
        failures.append("operation catalog catalog_kind must be target-operation-catalog")
    if catalog.get("fallback_operation") != "help":
        failures.append("operation catalog fallback_operation must be help")
    if catalog.get("authorization_phases") != AUTHORIZATION_PHASES:
        failures.append("operation catalog authorization phases are invalid")
    if catalog.get("required_final_evidence") != ["current_user_authorization"]:
        failures.append("operation catalog must require current user authorization evidence")

    for field, expected in CATALOG_PATHS.items():
        if catalog.get(field) != expected:
            failures.append(f"operation catalog {field} must be {expected}")
        elif not target_path_exists(expected):
            failures.append(f"operation catalog {field} points to missing {expected}")

    operations = catalog.get("operations")
    if not isinstance(operations, list) or not operations:
        failures.append("operation catalog operations must be a non-empty list")
        operations = []

    ids: list[str] = []
    aliases: dict[str, str] = {}
    for index, operation in enumerate(operations):
        label = f"operations[{index}]"
        if not isinstance(operation, dict):
            failures.append(f"{label} must be an object")
            continue
        for field in REQUIRED_OPERATION_STRINGS:
            if not isinstance(operation.get(field), str) or not operation.get(field):
                failures.append(f"{label}.{field} must be a non-empty string")
        operation_id = operation.get("id")
        if isinstance(operation_id, str) and operation_id:
            if operation_id in ids:
                failures.append(f"duplicate operation id {operation_id}")
            ids.append(operation_id)
        lists = {
            field: string_list(operation.get(field), f"{label}.{field}", failures)
            for field in REQUIRED_OPERATION_LISTS
        }
        for alias in lists["aliases"]:
            normalized = alias.casefold()
            previous = aliases.get(normalized)
            if previous and previous != operation_id:
                failures.append(
                    f"alias {alias!r} maps to both {previous} and {operation_id}"
                )
            aliases[normalized] = str(operation_id)
        unknown_actions = sorted(set(lists["allowed_actions"]) - ALLOWED_ACTIONS)
        if unknown_actions:
            failures.append(f"{label}.allowed_actions has unknown values {unknown_actions}")
        unknown_profiles = sorted(set(lists["context_profiles"]) - ALLOWED_PROFILES)
        if unknown_profiles:
            failures.append(f"{label}.context_profiles has unknown values {unknown_profiles}")
        if operation.get("required_module") not in ALLOWED_MODULES:
            failures.append(f"{label}.required_module is unsupported")
        if operation.get("preview") not in ALLOWED_PREVIEW:
            failures.append(f"{label}.preview must be never or risk-gated")
        flow = operation.get("flow")
        if isinstance(flow, str) and flow and not target_path_exists(flow):
            failures.append(f"{label}.flow points to missing {flow}")

    operation_ids = set(ids)
    if operation_ids != EXPECTED_OPERATIONS:
        failures.append(
            "operation catalog IDs differ from expected operations: "
            f"missing={sorted(EXPECTED_OPERATIONS - operation_ids)}, "
            f"extra={sorted(operation_ids - EXPECTED_OPERATIONS)}"
        )

    expected_alias_index: dict[str, str] = {}
    expected_operation_index: dict[str, list[str]] = {}
    for operation in operations:
        if not isinstance(operation, dict) or not isinstance(operation.get("id"), str):
            continue
        operation_id = operation["id"]
        for alias in operation.get("aliases", []):
            if isinstance(alias, str):
                expected_alias_index[alias] = operation_id
        module = operation.get("required_module")
        flow = operation.get("flow")
        actions = operation.get("allowed_actions")
        if isinstance(module, str) and isinstance(flow, str) and isinstance(actions, list):
            expected_operation_index[operation_id] = [module, flow, *actions]

    if operation_index.get("schema_version") != 1:
        failures.append("operation index schema_version must be 1")
    if operation_index.get("index_kind") != "target-operation-index":
        failures.append("operation index index_kind must be target-operation-index")
    if operation_index.get("catalog") != ".ai/assistant/operation-catalog.json":
        failures.append("operation index must point to the canonical catalog")
    if operation_index.get("aliases") != expected_alias_index:
        failures.append("operation index aliases must exactly derive from catalog aliases")
    if operation_index.get("operations") != expected_operation_index:
        failures.append(
            "operation index modules, flows, and allowed actions must exactly derive "
            "from the catalog"
        )

    reference_operations = set(
        re.findall(
            r"^Operation: `([^`]+)`",
            HELP_REFERENCE.read_text(encoding="utf-8"),
            flags=re.MULTILINE,
        )
    )
    if reference_operations != operation_ids:
        failures.append("help-reference operation IDs must match the operation catalog")

    operation_routing = router.get("operation_routing")
    if not isinstance(operation_routing, dict):
        failures.append("context router must define operation_routing")
    else:
        expected_routing = {
            "index": ".ai/assistant/operation-index.json",
            "catalog": ".ai/assistant/operation-catalog.json",
            "fallback_operation": "help",
            "health_operation": "adapter-health",
            "single_entry_alias": "Alatyr",
            "preview_policy": "risk-gated",
        }
        for field, expected in expected_routing.items():
            if operation_routing.get(field) != expected:
                failures.append(f"operation_routing.{field} must be {expected}")

    bootstrap = router.get("bootstrap_context")
    if isinstance(bootstrap, list) and ".ai/assistant/operation-catalog.json" in bootstrap:
        failures.append("operation catalog must stay outside routine bootstrap")

    profiles: dict[str, Any] = {}
    profile_index = router.get("profile_index")
    if isinstance(profile_index, dict):
        for profile, entry in profile_index.items():
            descriptor = entry.get("descriptor") if isinstance(entry, dict) else None
            if isinstance(descriptor, str) and target_path_exists(descriptor):
                profiles[profile] = load_json(TARGET / descriptor)
    else:
        inline_profiles = router.get("profiles")
        if isinstance(inline_profiles, dict):
            profiles = inline_profiles
    if not isinstance(profiles, dict):
        failures.append("context router profiles must be an object")
    else:
        routed_ids: set[str] = set()
        for profile, data in profiles.items():
            if not isinstance(data, dict):
                continue
            candidates = string_list(
                data.get("operation_candidates"),
                f"profiles.{profile}.operation_candidates",
                failures,
            )
            unknown = sorted(set(candidates) - operation_ids)
            if unknown:
                failures.append(f"profiles.{profile} has unknown operation candidates {unknown}")
            routed_ids.update(candidates)
        scale_overlays = router.get("task_scale_overlays")
        if isinstance(scale_overlays, dict):
            for overlay_name, overlay_route in scale_overlays.items():
                if not isinstance(overlay_route, dict):
                    continue
                overlay = overlay_route
                descriptor = overlay_route.get("descriptor")
                if isinstance(descriptor, str) and target_path_exists(descriptor):
                    overlay = load_json(TARGET / descriptor)
                if "operation_candidates" not in overlay:
                    continue
                candidates = string_list(
                    overlay.get("operation_candidates"),
                    f"task_scale_overlays.{overlay_name}.operation_candidates",
                    failures,
                )
                unknown = sorted(set(candidates) - operation_ids)
                if unknown:
                    failures.append(
                        f"task_scale_overlays.{overlay_name} has unknown "
                        f"operation candidates {unknown}"
                    )
                routed_ids.update(candidates)
        intent_overlays = router.get("intent_overlays")
        if isinstance(intent_overlays, dict):
            for overlay_name, overlay_route in intent_overlays.items():
                if not isinstance(overlay_route, dict):
                    continue
                overlay = overlay_route
                descriptor = overlay_route.get("descriptor")
                if isinstance(descriptor, str) and target_path_exists(descriptor):
                    overlay = load_json(TARGET / descriptor)
                candidates = string_list(
                    overlay.get("operation_candidates"),
                    f"intent_overlays.{overlay_name}.operation_candidates",
                    failures,
                )
                unknown = sorted(set(candidates) - operation_ids)
                if unknown:
                    failures.append(
                        f"intent_overlays.{overlay_name} has unknown operation "
                        f"candidates {unknown}"
                    )
                routed_ids.update(candidates)
        expected_routed = operation_ids - {"help", "large-task"}
        missing_routed = sorted(expected_routed - routed_ids)
        if missing_routed:
            failures.append(f"operation candidates do not route {missing_routed}")

    manifest_text = MANIFEST.read_text(encoding="utf-8")
    for key, value in {
        "index": ".ai/assistant/operation-index.json",
        "catalog": ".ai/assistant/operation-catalog.json",
        "routing": ".ai/assistant/flows/operation-routing.flow.md",
        "health": ".ai/assistant/flows/adapter-health.flow.md",
        "pre_change_preview": ".ai/assistant/templates/pre-change-preview.md",
        "action_authorization_policy": ".ai/assistant/policies/action-authorization.json",
        "diagram_discussion": ".ai/assistant/flows/diagram-discussion.flow.md",
        "diagram_presentation": ".ai/assistant/templates/diagram-presentation.md",
    }.items():
        if f'{key}: "{value}"' not in manifest_text:
            failures.append(f"manifest operations missing {key}: {value}")

    required_text = {
        ROUTING_FLOW: [
            "For `Alatyr` without a task:",
            "When exactly one operation fits",
            "The preview is not approval.",
        ],
        HEALTH_FLOW: [
            "Allowed actions are `read-only`.",
            "`ready`",
            "`attention`",
            "`blocked`",
            "`unverified`",
            "no more than three prioritized repair operations",
        ],
        PREVIEW: [
            "The preview is not approval.",
            "It is also not action authorization.",
            "Changed facts or suspected facts:",
            "Canonical owners:",
            "Allowed actions:",
            "Current user authorization:",
            "Decision: `{PROCEED_ASK_OR_BLOCKED}`",
        ],
    }
    for path, snippets in required_text.items():
        text = path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in text:
                failures.append(f"{path.relative_to(ROOT)} missing {snippet}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "OK: checked operation catalog, automatic routing, adapter health, "
        f"and pre-change preview for {len(operation_ids)} operations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

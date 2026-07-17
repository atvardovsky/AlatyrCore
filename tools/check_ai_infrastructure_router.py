#!/usr/bin/env python3
"""Validate AI infrastructure routing and adaptation-record templates."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
ROUTER = TARGET / ".ai" / "assistant" / "ai-infrastructure-router.json"
RECORD = (
    TARGET
    / ".ai"
    / "assistant"
    / "templates"
    / "ai-infrastructure-adaptation-record.md"
)
MANIFEST = TARGET / ".ai" / "alatyr.yaml"
CONTEXT_ROUTER = TARGET / ".ai" / "assistant" / "context-router.json"

ROUTES = [
    "inventory",
    "recommend",
    "use-existing",
    "adapt-import",
    "gate-checker-change",
    "tool-mcp-change",
    "bridge-wrapper-change",
]
ROUTE_FIELDS = [
    "use_when",
    "required_context",
    "expand_when",
    "allowed_actions",
    "approval_gates",
    "validation",
    "final_evidence",
]
ITEM_FIELDS = [
    "id",
    "type",
    "purpose",
    "status",
    "activation_triggers",
    "canonical_source",
    "required_context",
    "assistant_surfaces",
    "wrappers",
    "allowed_actions",
    "required_permissions",
    "approval_triggers",
    "gates",
    "validation",
    "output_contract",
    "conflicts_with",
    "adaptation_record",
]
RECORD_FIELDS = [
    "Adaptation ID:",
    "Target item ID:",
    "Item type:",
    "Source:",
    "Source type:",
    "Source hash, commit, or version:",
    "License status:",
    "Recommendation record or ID:",
    "Project-contour basis:",
    "Target purpose:",
    "Non-goals:",
    "Canonical normalized source:",
    "Activation triggers:",
    "Required context:",
    "Supported assistant surfaces:",
    "Allowed actions:",
    "Required permissions:",
    "Gates:",
    "Validation or manual review:",
    "Output contract:",
    "Existing item baseline and observed outcome:",
    "Expected quality and context-cost effect:",
    "Recommendation acceptance criteria:",
    "Source instructions rejected or not carried forward:",
    "Prompt-injection review:",
    "Permission and tool review:",
    "Approval record:",
    "Router entry result:",
    "Validation result:",
    "Residual risk:",
    "Final status:",
]


def non_empty_string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item for item in value)
    )


def placeholder(value: Any) -> bool:
    return isinstance(value, str) and "{" in value and "}" in value


def target_reference_exists(value: str) -> bool:
    if placeholder(value):
        return True
    if value.startswith(".ai/framework/"):
        return (ROOT / "framework" / value[len(".ai/framework/") :]).is_file()
    if value.startswith(".ai/"):
        return (TARGET / value).exists()
    return True


def main() -> int:
    failures: list[str] = []
    try:
        router = json.loads(ROUTER.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"FAIL: missing {ROUTER.relative_to(ROOT)}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"FAIL: invalid {ROUTER.relative_to(ROOT)}: {exc}", file=sys.stderr)
        return 1

    if router.get("schema_version") != 2:
        failures.append("AI infrastructure router schema_version must be 2")
    if router.get("router_kind") != "target-ai-infrastructure-router":
        failures.append("AI infrastructure router router_kind is incorrect")
    if router.get("recommendation_template") != (
        ".ai/assistant/templates/ai-infrastructure-recommendation.md"
    ):
        failures.append("AI infrastructure router recommendation_template is incorrect")
    if router.get("routing_order") != ROUTES:
        failures.append("AI infrastructure router routing_order is incorrect")
    if not non_empty_string_list(router.get("item_types")):
        failures.append("AI infrastructure router item_types must be non-empty")

    routes = router.get("routes")
    if not isinstance(routes, dict):
        failures.append("AI infrastructure router routes must be an object")
        routes = {}
    for route_name in ROUTES:
        route = routes.get(route_name)
        if not isinstance(route, dict):
            failures.append(f"missing AI infrastructure route {route_name}")
            continue
        for field in ROUTE_FIELDS:
            values = route.get(field)
            if not non_empty_string_list(values):
                failures.append(f"route {route_name}.{field} must be non-empty")
                continue
            if field == "required_context":
                for value in values:
                    if not target_reference_exists(value):
                        failures.append(
                            f"route {route_name}.required_context points to "
                            f"missing path: {value}"
                        )

    items = router.get("items")
    if not isinstance(items, list) or not items:
        failures.append("AI infrastructure router items must be non-empty")
        items = []
    for item_index, item in enumerate(items):
        if not isinstance(item, dict):
            failures.append(f"items[{item_index}] must be an object")
            continue
        for field in ITEM_FIELDS:
            if field not in item:
                failures.append(f"items[{item_index}] missing {field}")
        for field in [
            "id",
            "type",
            "purpose",
            "status",
            "canonical_source",
            "output_contract",
            "adaptation_record",
        ]:
            if field in item and not placeholder(item[field]):
                failures.append(f"items[{item_index}].{field} must be placeholder-based")
        for field in [
            "activation_triggers",
            "required_context",
            "assistant_surfaces",
            "wrappers",
            "allowed_actions",
            "required_permissions",
            "approval_triggers",
            "gates",
            "validation",
            "conflicts_with",
        ]:
            values = item.get(field)
            if not non_empty_string_list(values) or not all(
                placeholder(value) for value in values
            ):
                failures.append(
                    f"items[{item_index}].{field} must use placeholder items"
                )

    record_text = RECORD.read_text(encoding="utf-8")
    for field in RECORD_FIELDS:
        if field not in record_text:
            failures.append(f"adaptation record missing {field}")

    manifest_text = MANIFEST.read_text(encoding="utf-8")
    for value in [
        'router: ".ai/assistant/ai-infrastructure-router.json"',
        'recommendation: ".ai/assistant/templates/ai-infrastructure-recommendation.md"',
        'adaptation_record: ".ai/assistant/templates/ai-infrastructure-adaptation-record.md"',
    ]:
        if value not in manifest_text:
            failures.append(f"target manifest missing AI infrastructure {value}")

    try:
        context_router = json.loads(CONTEXT_ROUTER.read_text(encoding="utf-8"))
        profile_context = context_router["profiles"]["ai-infrastructure"][
            "required_context"
        ]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        failures.append(f"invalid context-router AI infrastructure route: {exc}")
    else:
        for required in [
            ".ai/framework/ai-infrastructure-routing.md",
            ".ai/assistant/ai-infrastructure-router.json",
        ]:
            if required not in profile_context:
                failures.append(f"AI infrastructure profile missing {required}")
        for eager_path in [
            ".ai/framework/prompt-injection.md",
            ".ai/assistant/policies/ai-infrastructure-source-access.md",
            ".ai/assistant/policies/prompt-injection.md",
        ]:
            if eager_path in profile_context:
                failures.append(
                    "AI infrastructure profile eagerly loads route-specific "
                    f"context: {eager_path}"
                )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "OK: checked AI infrastructure router with "
        f"{len(ROUTES)} routes and {len(items)} placeholder item(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

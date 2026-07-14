#!/usr/bin/env python3
"""Validate the target multi-level consistency-map template contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
MAP = TARGET / ".ai" / "project" / "consistency-map.json"
REGISTRY = TARGET / ".ai" / "project" / "source-of-truth-registry.md"
MANIFEST = TARGET / ".ai" / "alatyr.yaml"
ROUTER = TARGET / ".ai" / "assistant" / "context-router.json"

LEVELS = ["fact", "contract", "area", "system", "adapter"]
RELATIONSHIPS = [
    "implements",
    "verifies",
    "documents",
    "visualizes",
    "generates",
    "constrains",
    "depends-on",
    "routes",
]
NODE_FIELDS = [
    "id",
    "fact_type",
    "level",
    "project_area",
    "canonical_owner",
    "relationships",
]
EDGE_FIELDS = [
    "id",
    "type",
    "target",
    "target_level",
    "target_area",
    "direction",
    "required_when",
    "validation",
    "approval_trigger",
]


def is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and "{" in value and "}" in value


def non_empty_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item for item in value)
    )


def main() -> int:
    failures: list[str] = []
    try:
        data = json.loads(MAP.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"FAIL: missing {MAP.relative_to(ROOT)}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"FAIL: invalid {MAP.relative_to(ROOT)}: {exc}", file=sys.stderr)
        return 1

    if data.get("schema_version") != 1:
        failures.append("consistency-map schema_version must be 1")
    if data.get("map_kind") != "target-consistency-map":
        failures.append("consistency-map map_kind must be target-consistency-map")
    if data.get("human_registry") != ".ai/project/source-of-truth-registry.md":
        failures.append("consistency-map human_registry path is incorrect")
    if data.get("levels") != LEVELS:
        failures.append("consistency-map levels must match the portable level order")
    if data.get("relationship_types") != RELATIONSHIPS:
        failures.append(
            "consistency-map relationship_types must match portable relationship types"
        )

    policy = data.get("impact_policy")
    if not isinstance(policy, dict):
        failures.append("consistency-map impact_policy must be an object")
    else:
        if policy.get("default_mode") != "owner-and-applicable-direct-relationships":
            failures.append("consistency-map impact_policy.default_mode is incorrect")
        for field in ["transitive_expand_when", "required_evidence"]:
            if not non_empty_strings(policy.get(field)):
                failures.append(f"consistency-map impact_policy.{field} is invalid")

    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        failures.append("consistency-map nodes must be a non-empty list")
        nodes = []
    for node_index, node in enumerate(nodes):
        if not isinstance(node, dict):
            failures.append(f"nodes[{node_index}] must be an object")
            continue
        for field in NODE_FIELDS:
            if field not in node:
                failures.append(f"nodes[{node_index}] missing {field}")
        for field in ["id", "fact_type", "level", "project_area", "canonical_owner"]:
            if field in node and not is_placeholder(node[field]):
                failures.append(f"nodes[{node_index}].{field} must be placeholder-based")
        edges = node.get("relationships")
        if not isinstance(edges, list) or not edges:
            failures.append(f"nodes[{node_index}].relationships must be non-empty")
            continue
        for edge_index, edge in enumerate(edges):
            label = f"nodes[{node_index}].relationships[{edge_index}]"
            if not isinstance(edge, dict):
                failures.append(f"{label} must be an object")
                continue
            for field in EDGE_FIELDS:
                if field not in edge:
                    failures.append(f"{label} missing {field}")
            for field in [
                "id",
                "type",
                "target",
                "target_level",
                "target_area",
                "approval_trigger",
            ]:
                if field in edge and not is_placeholder(edge[field]):
                    failures.append(f"{label}.{field} must be placeholder-based")
            if edge.get("direction") != "outbound":
                failures.append(f"{label}.direction must be outbound")
            for field in ["required_when", "validation"]:
                values = edge.get(field)
                if not non_empty_strings(values) or not all(
                    is_placeholder(value) for value in values
                ):
                    failures.append(f"{label}.{field} must use placeholder items")

    registry_text = REGISTRY.read_text(encoding="utf-8")
    for required in [
        "Consistency level:",
        "Project area:",
        "Consistency map node:",
        "Relationship coverage:",
    ]:
        if required not in registry_text:
            failures.append(f"source-of-truth registry missing {required}")

    manifest_text = MANIFEST.read_text(encoding="utf-8")
    if 'consistency_map: ".ai/project/consistency-map.json"' not in manifest_text:
        failures.append("target manifest missing source_of_truth.consistency_map")

    try:
        router = json.loads(ROUTER.read_text(encoding="utf-8"))
        routing_context = router["consistency_routing"]["required_context"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        failures.append(f"invalid context-router consistency routing: {exc}")
    else:
        for required in [
            ".ai/framework/consistency-model.md",
            ".ai/project/consistency-map.json",
        ]:
            if required not in routing_context:
                failures.append(f"consistency routing missing {required}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "OK: checked consistency-map template with "
        f"{len(nodes)} placeholder node(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

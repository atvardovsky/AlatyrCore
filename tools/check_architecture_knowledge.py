#!/usr/bin/env python3
"""Validate architecture-knowledge framework and target source contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
RULE = ROOT / "framework" / "architecture-knowledge.md"
INDEX = TARGET / ".ai/project/architecture/README.md"
CATALOG = TARGET / ".ai/project/architecture/catalog.json"
FLOW = TARGET / ".ai/assistant/flows/architecture-assistance.flow.md"
PATTERN = TARGET / ".ai/assistant/templates/architecture-pattern.md"
AREA = TARGET / ".ai/assistant/templates/architecture-area.md"
RESULT = TARGET / ".ai/assistant/templates/architecture-discussion-result.md"
INTENT = TARGET / ".ai/assistant/context/intents/architecture-request.json"
ROUTER = TARGET / ".ai/assistant/context-router.json"
OPERATIONS = TARGET / ".ai/assistant/operation-catalog.json"
MODULES = TARGET / ".ai/assistant/module-profile.md"
GATES = TARGET / ".ai/assistant/gates/checklist.md"
REGISTRY = TARGET / ".ai/project/source-of-truth-registry.md"
MANIFEST = TARGET / ".ai/alatyr.yaml"
HELP = TARGET / ".ai/assistant/help.md"
HELP_REFERENCE = TARGET / ".ai/assistant/help-reference.md"

STATUSES = {
    "observed",
    "proposed",
    "accepted",
    "preferred",
    "restricted",
    "deprecated",
    "contradicted",
    "unknown",
}


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return data


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require_snippets(
    path: Path, snippets: list[str], failures: list[str]
) -> None:
    text = read(path)
    normalized = " ".join(text.split())
    for snippet in snippets:
        if snippet not in text and snippet not in normalized:
            failures.append(f"{path.relative_to(ROOT)} missing {snippet}")


def check_entry_fields(
    entry: Any,
    fields: set[str],
    label: str,
    failures: list[str],
) -> None:
    if not isinstance(entry, dict):
        failures.append(f"{label} must be an object")
        return
    missing = sorted(fields - set(entry))
    if missing:
        failures.append(f"{label} missing fields {missing}")


def main() -> int:
    failures: list[str] = []
    required_files = [
        RULE,
        INDEX,
        CATALOG,
        FLOW,
        PATTERN,
        AREA,
        RESULT,
        INTENT,
        ROUTER,
        OPERATIONS,
        MODULES,
        GATES,
        REGISTRY,
        MANIFEST,
        HELP,
        HELP_REFERENCE,
    ]
    for path in required_files:
        if not path.is_file():
            failures.append(f"missing {path.relative_to(ROOT)}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    require_snippets(
        RULE,
        [
            "ALATYR-ARCHITECTURE-001",
            "## Knowledge States",
            "## Pattern Record Contract",
            "## Pattern Discussion Sequence",
            "## Documentation Maintenance",
            "## Context Economy",
            "## Rejection Criteria",
        ],
        failures,
    )
    rule_text = read(RULE)
    for status in STATUSES:
        if f"`{status}`" not in rule_text:
            failures.append(f"architecture rule missing status {status}")

    try:
        catalog = load_object(CATALOG)
        intent = load_object(INTENT)
        router = load_object(ROUTER)
        operation_catalog = load_object(OPERATIONS)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))
        catalog = {}
        intent = {}
        router = {}
        operation_catalog = {}

    if catalog.get("schema_version") != 1:
        failures.append("architecture catalog schema_version must be 1")
    if catalog.get("catalog_kind") != "target-architecture-knowledge-catalog":
        failures.append("architecture catalog kind is invalid")
    if catalog.get("human_index") != ".ai/project/architecture/README.md":
        failures.append("architecture catalog human_index is invalid")
    for field in [
        "project",
        "module_state",
        "architecture_owner",
        "decision_authority",
        "last_reviewed",
        "evidence_revision",
    ]:
        value = catalog.get(field)
        if not isinstance(value, str) or not value:
            failures.append(f"architecture catalog {field} must be a string")
    for field in ["canonical_sources", "decision_sources", "known_gaps"]:
        value = catalog.get(field)
        if not isinstance(value, list) or not value:
            failures.append(f"architecture catalog {field} must be a non-empty list")

    areas = catalog.get("areas")
    if not isinstance(areas, list) or not areas:
        failures.append("architecture catalog areas must be a non-empty list")
    else:
        check_entry_fields(
            areas[0],
            {"id", "name", "status", "owner", "detail", "evidence", "pattern_ids"},
            "architecture catalog area",
            failures,
        )
    patterns = catalog.get("patterns")
    if not isinstance(patterns, list) or not patterns:
        failures.append("architecture catalog patterns must be a non-empty list")
    else:
        check_entry_fields(
            patterns[0],
            {
                "id",
                "name",
                "kind",
                "status",
                "scope",
                "problem",
                "decision_owner",
                "decision_record",
                "detail",
                "evidence",
                "validation",
                "related_pattern_ids",
                "last_verified_revision",
            },
            "architecture catalog pattern",
            failures,
        )

    if intent.get("intent") != "architecture-request":
        failures.append("architecture intent identity is invalid")
    if intent.get("required_module") != "architecture-knowledge":
        failures.append("architecture intent must require architecture-knowledge")
    if intent.get("operation_candidates") != ["architecture-assistance"]:
        failures.append("architecture intent must route architecture-assistance")
    required_context = intent.get("required_context")
    for path in [
        ".ai/framework/architecture-knowledge.md",
        ".ai/project/architecture/catalog.json",
        ".ai/assistant/flows/architecture-assistance.flow.md",
        ".ai/assistant/templates/architecture-discussion-result.md",
    ]:
        if not isinstance(required_context, list) or path not in required_context:
            failures.append(f"architecture intent required_context missing {path}")
    conditional = intent.get("conditional_context")
    conditional_paths = {
        entry.get("path")
        for entry in conditional
        if isinstance(entry, dict)
    } if isinstance(conditional, list) else set()
    for path in [
        ".ai/project/architecture/README.md",
        ".ai/assistant/templates/architecture-pattern.md",
        ".ai/assistant/templates/architecture-area.md",
        ".ai/framework/diagram-guidance.md",
        ".ai/framework/blueprint-driven-change.md",
    ]:
        if path not in conditional_paths:
            failures.append(f"architecture intent conditional_context missing {path}")

    route = router.get("intent_overlays", {}).get("architecture-request")
    if not isinstance(route, dict):
        failures.append("context router missing architecture-request")
    else:
        if route.get("descriptor") != ".ai/assistant/context/intents/architecture-request.json":
            failures.append("architecture router descriptor is invalid")
        if route.get("operation_candidates") != ["architecture-assistance"]:
            failures.append("architecture router candidate is invalid")

    operations = operation_catalog.get("operations")
    operation = next(
        (
            item
            for item in operations
            if isinstance(item, dict) and item.get("id") == "architecture-assistance"
        ),
        None,
    ) if isinstance(operations, list) else None
    if not isinstance(operation, dict):
        failures.append("operation catalog missing architecture-assistance")
    else:
        expected = {
            "required_module": "architecture-knowledge",
            "flow": ".ai/assistant/flows/architecture-assistance.flow.md",
            "preview": "risk-gated",
        }
        for field, value in expected.items():
            if operation.get(field) != value:
                failures.append(f"architecture-assistance.{field} must be {value}")
        if operation.get("allowed_actions") != [
            "read-only",
            "docs-only",
            "full-with-approval",
        ]:
            failures.append("architecture-assistance allowed actions are invalid")

    require_snippets(
        FLOW,
        [
            "## Routing Modes",
            "`inventory`",
            "`explain`",
            "`discuss`",
            "`compare`",
            "`review`",
            "`document`",
            "no-change baseline",
            "reuse of an accepted project pattern",
            "adaptation of an existing pattern",
            "new pattern",
            "current and proposed",
            "`docs-only`",
            "`full-with-approval`",
        ],
        failures,
    )
    require_snippets(
        PATTERN,
        [
            "Pattern ID:",
            "Problem addressed:",
            "Rules and invariants:",
            "Use when:",
            "Do not use when:",
            "Last verified revision:",
        ],
        failures,
    )
    require_snippets(
        AREA,
        [
            "Area ID:",
            "Responsibilities:",
            "Owned data and lifecycle:",
            "Pattern IDs:",
            "Validation or fitness checks:",
        ],
        failures,
    )
    require_snippets(
        RESULT,
        [
            "No-change baseline:",
            "Reuse accepted project pattern:",
            "Adapt existing project pattern:",
            "Introduce new pattern:",
            "Pattern-proliferation result:",
            "Decision or blueprint handoff:",
        ],
        failures,
    )
    require_snippets(
        MODULES,
        [
            "Module: `architecture-knowledge`",
            ".ai/project/architecture/catalog.json",
            ".ai/assistant/flows/architecture-assistance.flow.md",
        ],
        failures,
    )
    require_snippets(
        GATES,
        ["`ALATYR-ARCHITECTURE-001`", "pattern proliferation"],
        failures,
    )
    require_snippets(
        REGISTRY,
        ["### Fact Type: `architecture pattern`", ".ai/project/architecture/catalog.json"],
        failures,
    )
    require_snippets(
        MANIFEST,
        [
            'architecture_index: ".ai/project/architecture/README.md"',
            'architecture_catalog: ".ai/project/architecture/catalog.json"',
            'architecture_assistance: ".ai/assistant/flows/architecture-assistance.flow.md"',
        ],
        failures,
    )
    for path in [HELP, HELP_REFERENCE]:
        require_snippets(path, ["architecture-assistance", "Alatyr architecture"], failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("OK: checked architecture knowledge, pattern discussion, and documentation contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

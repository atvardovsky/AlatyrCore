#!/usr/bin/env python3
"""Validate code-documentation framework and target template contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
RULE = ROOT / "framework" / "code-documentation.md"
INDEX = TARGET / ".ai/project/documentation/README.md"
CATALOG = TARGET / ".ai/project/documentation/catalog.json"
PROFILES = TARGET / ".ai/project/documentation/profiles.json"
INTENT = TARGET / ".ai/assistant/context/intents/code-documentation.json"
FLOW = TARGET / ".ai/assistant/flows/documentation-sync.flow.md"
SKILL = TARGET / ".ai/assistant/skills/code-documentation/SKILL.md"
REVIEW = TARGET / ".ai/assistant/templates/code-documentation-profile-review.md"
ROUTER = TARGET / ".ai/assistant/context-router.json"
OPERATIONS = TARGET / ".ai/assistant/operation-catalog.json"
MODULES = TARGET / ".ai/assistant/module-profile.md"
GATES = TARGET / ".ai/assistant/gates/checklist.md"
MANIFEST = TARGET / ".ai/alatyr.yaml"
REGISTRY = TARGET / ".ai/project/source-of-truth-registry.md"

PROFILE_STATES = {"proposed", "accepted", "deprecated", "contradicted", "unknown"}
OUTPUT_POLICIES = {
    "ci-artifact",
    "committed-generated",
    "local-only",
    "external-publish",
    "unresolved",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(read(path))
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return data


def require(path: Path, snippets: list[str], failures: list[str]) -> None:
    text = read(path)
    normalized = " ".join(text.split())
    for snippet in snippets:
        if snippet not in text and snippet not in normalized:
            failures.append(f"{path.relative_to(ROOT)} missing {snippet}")


def require_fields(
    value: Any, fields: set[str], label: str, failures: list[str]
) -> dict[str, Any]:
    if not isinstance(value, dict):
        failures.append(f"{label} must be an object")
        return {}
    missing = sorted(fields - set(value))
    if missing:
        failures.append(f"{label} missing fields {missing}")
    return value


def main() -> int:
    failures: list[str] = []
    required_files = [
        RULE, INDEX, CATALOG, PROFILES, INTENT, FLOW, SKILL, REVIEW,
        ROUTER, OPERATIONS, MODULES, GATES, MANIFEST, REGISTRY,
    ]
    for path in required_files:
        if not path.is_file():
            failures.append(f"missing {path.relative_to(ROOT)}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    require(
        RULE,
        [
            "ALATYR-CODEDOC-001",
            "## Source-Of-Truth Boundary",
            "## Multiple Documentation Profiles",
            "## Profile Selection",
            "## Style Proposal Process",
            "## Comment Content Contract",
            "## Generation And Output Policy",
            "## Assistant Skill Boundary",
            "## Context Economy",
            "## Rejection Criteria",
            "Generated documentation is always a derived surface",
        ],
        failures,
    )
    rule_text = read(RULE)
    for value in PROFILE_STATES | OUTPUT_POLICIES:
        if f"`{value}`" not in rule_text:
            failures.append(f"code-documentation rule missing value {value}")

    try:
        catalog = load_object(CATALOG)
        profiles = load_object(PROFILES)
        intent = load_object(INTENT)
        router = load_object(ROUTER)
        operations = load_object(OPERATIONS)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))
        catalog = profiles = intent = router = operations = {}

    if catalog.get("schema_version") != 1:
        failures.append("code-documentation catalog schema_version must be 1")
    if catalog.get("catalog_kind") != "target-code-documentation-catalog":
        failures.append("code-documentation catalog kind is invalid")
    if catalog.get("human_index") != ".ai/project/documentation/README.md":
        failures.append("code-documentation catalog human_index is invalid")
    if catalog.get("profiles") != ".ai/project/documentation/profiles.json":
        failures.append("code-documentation catalog profiles path is invalid")
    areas = catalog.get("areas")
    if not isinstance(areas, list) or not areas:
        failures.append("code-documentation catalog areas must be non-empty")
    else:
        require_fields(
            areas[0],
            {"id", "name", "owner", "source_scope", "profile_ids", "audiences",
             "public_boundary", "generated_outputs", "status", "evidence"},
            "code-documentation area",
            failures,
        )

    if profiles.get("schema_version") != 1:
        failures.append("code-documentation profiles schema_version must be 1")
    if profiles.get("profile_kind") != "target-code-documentation-profiles":
        failures.append("code-documentation profile kind is invalid")
    require_fields(
        profiles.get("selection_policy"),
        {"order", "on_equal_conflict", "on_no_accepted_match"},
        "code-documentation selection_policy",
        failures,
    )
    entries = profiles.get("profiles")
    if not isinstance(entries, list) or not entries:
        failures.append("code-documentation profiles must be non-empty")
    else:
        entry = require_fields(
            entries[0],
            {"id", "state", "owner", "priority", "match", "audiences",
             "visibility", "purpose", "evidence", "comment_contract",
             "generation", "validation", "assistant_skill", "migration_scope",
             "approval_needs", "known_gaps"},
            "code-documentation profile",
            failures,
        )
        require_fields(
            entry.get("match"),
            {"include", "exclude", "languages", "frameworks"},
            "code-documentation profile.match",
            failures,
        )
        require_fields(
            entry.get("comment_contract"),
            {"syntax", "required_for", "required_sections", "content_focus",
             "avoid", "canonical_fact_owners", "uncertainty_policy"},
            "code-documentation profile.comment_contract",
            failures,
        )
        generation = require_fields(
            entry.get("generation"),
            {"generator", "config", "entry_point", "output", "output_policy",
             "direct_edit", "publication_boundary"},
            "code-documentation profile.generation",
            failures,
        )
        if generation.get("direct_edit") != "forbidden":
            failures.append("generated output direct_edit must be forbidden")

    if intent.get("intent") != "code-documentation":
        failures.append("code-documentation intent identity is invalid")
    if intent.get("required_module") != "code-documentation":
        failures.append("code-documentation intent must require its module")
    if intent.get("operation_candidates") != ["documentation-sync"]:
        failures.append("code-documentation intent must route documentation-sync")
    required_context = intent.get("required_context")
    for path in [
        ".ai/framework/code-documentation.md",
        ".ai/project/documentation/catalog.json",
        ".ai/project/documentation/profiles.json",
        ".ai/assistant/flows/documentation-sync.flow.md",
    ]:
        if not isinstance(required_context, list) or path not in required_context:
            failures.append(f"code-documentation intent missing {path}")

    route = router.get("intent_overlays", {}).get("code-documentation")
    if not isinstance(route, dict):
        failures.append("context router missing code-documentation intent")
    else:
        if route.get("descriptor") != ".ai/assistant/context/intents/code-documentation.json":
            failures.append("code-documentation router descriptor is invalid")
        if route.get("required_module") != "code-documentation":
            failures.append("code-documentation router module is invalid")
        if route.get("operation_candidates") != ["documentation-sync"]:
            failures.append("code-documentation router candidate is invalid")

    operation_list = operations.get("operations")
    operation = next(
        (item for item in operation_list
         if isinstance(item, dict) and item.get("id") == "documentation-sync"),
        None,
    ) if isinstance(operation_list, list) else None
    if not isinstance(operation, dict):
        failures.append("operation catalog missing documentation-sync")
    else:
        for alias in ["document code", "propose comment style",
                      "generate code docs", "review code documentation"]:
            if alias not in operation.get("aliases", []):
                failures.append(f"documentation-sync missing alias {alias}")
        if "code-and-tests" not in operation.get("allowed_actions", []):
            failures.append("documentation-sync must permit code-and-tests")

    require(
        FLOW,
        ["## Routing Modes", "`inventory`", "`propose`", "`review`",
         "`document`", "`synchronize`", "`generate`",
         "one convention repository-wide",
         "Never edit a configured generated output directly",
         "Frontend, backend, shared-library, and infrastructure profiles"],
        failures,
    )
    require(
        SKILL,
        ["Canonical profiles:", "most specific accepted profile",
         "Never edit generated output directly", "Do not activate this placeholder"],
        failures,
    )
    require(
        REVIEW,
        ["Languages and frameworks:", "Existing comments and style:",
         "Canonical owners comments must not replace:", "Profile state:",
         "Generator and configuration:", "Approval needs:"],
        failures,
    )
    require(
        MODULES,
        ["Module: `code-documentation`",
         ".ai/project/documentation/catalog.json",
         ".ai/project/documentation/profiles.json",
         ".ai/assistant/context/intents/code-documentation.json",
         ".ai/assistant/skills/code-documentation/SKILL.md"],
        failures,
    )
    require(
        GATES,
        ["ALATYR-CODEDOC-001",
         "different frontend, backend, shared, and infrastructure styles",
         "never edits generated output directly"],
        failures,
    )
    require(
        MANIFEST,
        ['code_documentation_catalog: ".ai/project/documentation/catalog.json"',
         'code_documentation_profiles: ".ai/project/documentation/profiles.json"',
         'intent: ".ai/assistant/context/intents/code-documentation.json"',
         'skill: ".ai/assistant/skills/code-documentation/SKILL.md"'],
        failures,
    )
    require(
        REGISTRY,
        ["### Fact Type: `code documentation profile`",
         "Canonical owner: `.ai/project/documentation/profiles.json`",
         "`{TARGET_GENERATED_CODE_REFERENCE_OR_NONE}`"],
        failures,
    )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: code-documentation framework and target templates are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

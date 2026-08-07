#!/usr/bin/env python3
"""Validate project-vocabulary framework and target template contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
RULE = ROOT / "framework" / "project-vocabulary.md"
INDEX = TARGET / ".ai/project/vocabulary/README.md"
CATALOG = TARGET / ".ai/project/vocabulary/catalog.json"
TERMS = TARGET / ".ai/project/vocabulary/terms.json"
LINKS = TARGET / ".ai/project/vocabulary/data-dictionary-links.json"
INTENT = TARGET / ".ai/assistant/context/intents/vocabulary-request.json"
FLOW = TARGET / ".ai/assistant/flows/project-vocabulary.flow.md"
SKILL = TARGET / ".ai/assistant/skills/project-vocabulary/SKILL.md"
REVIEW = TARGET / ".ai/assistant/templates/vocabulary-term-review.md"
ROUTER = TARGET / ".ai/assistant/context-router.json"
OPERATIONS = TARGET / ".ai/assistant/operation-catalog.json"
MODULES = TARGET / ".ai/assistant/module-profile.md"
GATES = TARGET / ".ai/assistant/gates/checklist.md"
MANIFEST = TARGET / ".ai/alatyr.yaml"
REGISTRY = TARGET / ".ai/project/source-of-truth-registry.md"
BRIDGES = TARGET / ".ai/assistant/bridge-capability-matrix.md"
INSTALL = ROOT / "INSTALL.md"
INSTALL_FLOW = ROOT / "installer/assistant-installation.flow.md"
READINESS = ROOT / "installer/readiness-checklist.md"
PLAN = ROOT / "installer/installation-plan-template.md"
LIFECYCLE = ROOT / "framework/lifecycle.md"
RECHECK = TARGET / ".ai/assistant/flows/adapter-recheck.flow.md"
POST_INSTALL = TARGET / ".ai/assistant/templates/post-install-message.md"
POST_UPDATE = TARGET / ".ai/assistant/templates/post-update-message.md"

TERM_STATES = {
    "observed", "proposed", "accepted", "deprecated", "contradicted", "unknown"
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
        RULE, INDEX, CATALOG, TERMS, LINKS, INTENT, FLOW, SKILL, REVIEW,
        ROUTER, OPERATIONS, MODULES, GATES, MANIFEST, REGISTRY, BRIDGES,
        INSTALL, INSTALL_FLOW, READINESS, PLAN, LIFECYCLE, RECHECK,
        POST_INSTALL, POST_UPDATE,
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
            "ALATYR-VOCABULARY-001",
            "## Vocabulary Boundaries",
            "## Term States",
            "## Record Contract",
            "## Compact Catalog And Lookup",
            "## Proposal And Acceptance",
            "## Data Dictionary Links",
            "## Synchronization And Integrity",
            "## Assistant Skill Boundary",
            "## Context Economy",
            "## Rejection Criteria",
        ],
        failures,
    )
    rule_text = read(RULE)
    for state in TERM_STATES:
        if f"`{state}`" not in rule_text:
            failures.append(f"project-vocabulary rule missing state {state}")

    try:
        catalog = load_object(CATALOG)
        terms = load_object(TERMS)
        links = load_object(LINKS)
        intent = load_object(INTENT)
        router = load_object(ROUTER)
        operations = load_object(OPERATIONS)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))
        catalog = terms = links = intent = router = operations = {}

    if catalog.get("schema_version") != 1:
        failures.append("vocabulary catalog schema_version must be 1")
    if catalog.get("catalog_kind") != "target-project-vocabulary-catalog":
        failures.append("vocabulary catalog kind is invalid")
    expected_catalog_paths = {
        "human_index": ".ai/project/vocabulary/README.md",
        "terms": ".ai/project/vocabulary/terms.json",
        "data_dictionary_links": ".ai/project/vocabulary/data-dictionary-links.json",
    }
    for field, expected in expected_catalog_paths.items():
        if catalog.get(field) != expected:
            failures.append(f"vocabulary catalog {field} must be {expected}")
    entries = catalog.get("entries")
    if not isinstance(entries, list) or not entries:
        failures.append("vocabulary catalog entries must be non-empty")
    else:
        require_fields(
            entries[0],
            {"term_id", "canonical_term", "normalized_term", "aliases",
             "acronyms", "domains", "state", "record",
             "replacement_term_id", "last_verified_revision"},
            "vocabulary catalog entry",
            failures,
        )

    if terms.get("schema_version") != 1:
        failures.append("vocabulary terms schema_version must be 1")
    if terms.get("record_kind") != "target-project-vocabulary-terms":
        failures.append("vocabulary terms record kind is invalid")
    term_entries = terms.get("terms")
    if not isinstance(term_entries, list) or not term_entries:
        failures.append("vocabulary terms must be non-empty")
    else:
        require_fields(
            term_entries[0],
            {"id", "canonical_term", "normalized_term", "kind", "state",
             "domains", "usage_scopes", "audiences", "definition",
             "non_meanings", "aliases", "acronym_expansions",
             "acronyms",
             "discouraged_synonyms", "replacement_term_id", "owner",
             "decision_authority", "canonical_sources", "evidence",
             "related_term_ids", "data_dictionary_refs", "examples",
             "sensitivity", "validation", "last_verified_revision",
             "contradictions", "known_gaps"},
            "vocabulary term",
            failures,
        )

    if links.get("schema_version") != 1:
        failures.append("vocabulary links schema_version must be 1")
    if links.get("record_kind") != "target-vocabulary-data-dictionary-links":
        failures.append("vocabulary links record kind is invalid")
    link_entries = links.get("links")
    if not isinstance(link_entries, list) or not link_entries:
        failures.append("vocabulary data links must be non-empty")
    else:
        require_fields(
            link_entries[0],
            {"id", "term_id", "fact_type", "canonical_owner",
             "target_identifier", "relationship", "direction", "evidence",
             "validation", "last_verified_revision", "known_gaps"},
            "vocabulary data link",
            failures,
        )

    if intent.get("intent") != "vocabulary-request":
        failures.append("vocabulary intent identity is invalid")
    if intent.get("required_module") != "project-vocabulary":
        failures.append("vocabulary intent must require project-vocabulary")
    if intent.get("operation_candidates") != ["project-vocabulary"]:
        failures.append("vocabulary intent operation candidate is invalid")
    for path in [
        ".ai/framework/project-vocabulary.md",
        ".ai/project/vocabulary/catalog.json",
        ".ai/assistant/flows/project-vocabulary.flow.md",
    ]:
        if path not in intent.get("required_context", []):
            failures.append(f"vocabulary intent missing {path}")

    route = router.get("intent_overlays", {}).get("vocabulary-request")
    if not isinstance(route, dict):
        failures.append("context router missing vocabulary-request")
    else:
        if route.get("descriptor") != ".ai/assistant/context/intents/vocabulary-request.json":
            failures.append("vocabulary router descriptor is invalid")
        if route.get("required_module") != "project-vocabulary":
            failures.append("vocabulary router module is invalid")
        if route.get("operation_candidates") != ["project-vocabulary"]:
            failures.append("vocabulary router candidate is invalid")

    operation_list = operations.get("operations")
    operation = next(
        (item for item in operation_list
         if isinstance(item, dict) and item.get("id") == "project-vocabulary"),
        None,
    ) if isinstance(operation_list, list) else None
    if not isinstance(operation, dict):
        failures.append("operation catalog missing project-vocabulary")
    else:
        if operation.get("required_module") != "project-vocabulary":
            failures.append("project-vocabulary operation module is invalid")
        if operation.get("flow") != ".ai/assistant/flows/project-vocabulary.flow.md":
            failures.append("project-vocabulary operation flow is invalid")
        for alias in ["Alatyr glossary", "Alatyr define term",
                      "propose glossary entry", "check terminology",
                      "review project vocabulary"]:
            if alias not in operation.get("aliases", []):
                failures.append(f"project-vocabulary missing alias {alias}")

    require(
        FLOW,
        ["## Routing Modes", "`lookup`", "`propose`", "`review`",
         "`terminology-check`", "## Allowed Actions",
         "Do not mark observed or proposed records accepted",
         "Do not load the full vocabulary for one term"],
        failures,
    )
    require(
        SKILL,
        ["Canonical catalog:", "Preserve `observed`, `proposed`, `accepted`",
         "Do not activate this placeholder", "Do not infer accepted meaning"],
        failures,
    )
    require(
        REVIEW,
        ["Selected term IDs:", "State:", "Canonical sources:",
         "Data dictionary links:", "Acceptance state:",
         "Residual ambiguity or risk:"],
        failures,
    )
    require(
        MODULES,
        ["Module: `project-vocabulary`", ".ai/project/vocabulary/catalog.json",
         ".ai/project/vocabulary/terms.json",
         ".ai/project/vocabulary/data-dictionary-links.json",
         ".ai/assistant/context/intents/vocabulary-request.json",
         ".ai/assistant/skills/project-vocabulary/SKILL.md"],
        failures,
    )
    require(
        GATES,
        ["ALATYR-VOCABULARY-001", "does not silently resolve multiple accepted meanings",
         "does not normalize project surfaces"],
        failures,
    )
    require(
        MANIFEST,
        ['vocabulary_catalog: ".ai/project/vocabulary/catalog.json"',
         'vocabulary_terms: ".ai/project/vocabulary/terms.json"',
         'intent: ".ai/assistant/context/intents/vocabulary-request.json"',
         'skill: ".ai/assistant/skills/project-vocabulary/SKILL.md"'],
        failures,
    )
    require(
        REGISTRY,
        ["### Fact Type: `project vocabulary`",
         "Canonical owner: `.ai/project/vocabulary/terms.json`",
         "Data dictionary links: `.ai/project/vocabulary/data-dictionary-links.json`"],
        failures,
    )
    if read(BRIDGES).count("Routes project-vocabulary aliases:") != 9:
        failures.append("bridge matrix must route project-vocabulary on 9 surfaces")
    require(
        INSTALL,
        ["ALATYR-VOCABULARY-001", "optional project-vocabulary owner",
         ".ai/project/vocabulary/README.md"],
        failures,
    )
    require(
        INSTALL_FLOW,
        ["framework/project-vocabulary.md", "ALATYR-VOCABULARY-001",
         ".ai/project/vocabulary/README.md", "`vocabulary-request` intent overlay"],
        failures,
    )
    require(
        READINESS,
        ["project-vocabulary owner", "term decision authority",
         "canonical sources", "terminology validation"],
        failures,
    )
    require(
        PLAN,
        ["Project-vocabulary need", "Project-vocabulary lookup",
         "Canonical term sources"],
        failures,
    )
    require(
        LIFECYCLE,
        ["When `project-vocabulary` is enabled", "Preserve target vocabulary term IDs",
         "project-vocabulary rule"],
        failures,
    )
    require(
        RECHECK,
        ["Project vocabulary:", "project-vocabulary ownership",
         "alias/acronym lookup"],
        failures,
    )
    require(
        POST_INSTALL,
        [".ai/project/vocabulary/catalog.json", "`project-vocabulary`:",
         "resolve aliases or acronyms"],
        failures,
    )
    require(
        POST_UPDATE,
        ["When project vocabulary is enabled", "preserve term IDs",
         "recheck lookup"],
        failures,
    )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: project-vocabulary framework and target templates are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

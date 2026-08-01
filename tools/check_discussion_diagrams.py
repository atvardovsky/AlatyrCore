#!/usr/bin/env python3
"""Validate portable discussion-diagram source and target template contracts.

This validates AlatyrCore source files only. It does not prove that an external
assistant client renders a syntax or can attach a generated artifact.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
RULE = ROOT / "framework" / "diagram-guidance.md"
CATALOG = TARGET / ".ai" / "assistant" / "operation-catalog.json"
INDEX = TARGET / ".ai" / "assistant" / "operation-index.json"
ROUTER = TARGET / ".ai" / "assistant" / "context-router.json"
FLOW = TARGET / ".ai" / "assistant" / "flows" / "diagram-discussion.flow.md"
PRESENTATION = (
    TARGET / ".ai" / "assistant" / "templates" / "diagram-presentation.md"
)
MATRIX = TARGET / ".ai" / "assistant" / "bridge-capability-matrix.md"
CAPABILITIES = TARGET / ".ai" / "assistant" / "assistant-capabilities.json"
SURFACES = ROOT / "conformance" / "runs" / "assistant-surfaces.json"
FIXTURE = ROOT / "conformance" / "operations" / "diagram-discussion.json"
MANIFEST = TARGET / ".ai" / "alatyr.yaml"
MODULE_PROFILE = TARGET / ".ai" / "assistant" / "module-profile.md"
HELP = TARGET / ".ai" / "assistant" / "help.md"
HELP_REFERENCE = TARGET / ".ai" / "assistant" / "help-reference.md"

ENTRY_HEADING = re.compile(r"^### Assistant Surface: `([^`]+)`\s*$", re.MULTILINE)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(read(path))
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return data


def matrix_entries(text: str) -> dict[str, str]:
    matches = list(ENTRY_HEADING.finditer(text))
    entries: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        entries[match.group(1)] = text[start:end]
    return entries


def main() -> int:
    failures: list[str] = []
    required_files = [
        RULE,
        CATALOG,
        INDEX,
        ROUTER,
        FLOW,
        PRESENTATION,
        MATRIX,
        CAPABILITIES,
        SURFACES,
        FIXTURE,
        MANIFEST,
        MODULE_PROFILE,
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

    for snippet in [
        "ALATYR-DIAGRAM-001",
        "## Discussion Diagram Contract",
        "Native inline rendering",
        "rendered visual artifact",
        "portable text fallback",
        "Discussion diagrams are `draft` by default.",
        "## Security, Privacy, And External Rendering",
        "stable diagram ID",
        "must bind to its",
    ]:
        if snippet not in read(RULE):
            failures.append(f"framework/diagram-guidance.md missing {snippet}")

    try:
        catalog = load_json(CATALOG)
        operation_index = load_json(INDEX)
        router = load_json(ROUTER)
        capabilities = load_json(CAPABILITIES)
        surfaces_data = load_json(SURFACES)
        fixture = load_json(FIXTURE)
    except (json.JSONDecodeError, ValueError) as exc:
        failures.append(str(exc))
        catalog = {}
        operation_index = {}
        router = {}
        capabilities = {}
        surfaces_data = {}
        fixture = {}

    operations = catalog.get("operations")
    operation = None
    if isinstance(operations, list):
        operation = next(
            (
                item
                for item in operations
                if isinstance(item, dict) and item.get("id") == "diagram-discussion"
            ),
            None,
        )
    if not isinstance(operation, dict):
        failures.append("operation catalog missing diagram-discussion")
    else:
        expected = {
            "required_module": "diagrams",
            "flow": ".ai/assistant/flows/diagram-discussion.flow.md",
            "preview": "never",
        }
        for field, value in expected.items():
            if operation.get(field) != value:
                failures.append(f"diagram-discussion.{field} must be {value}")
        actions = operation.get("allowed_actions")
        if actions != ["read-only", "docs-only"]:
            failures.append(
                "diagram-discussion.allowed_actions must be read-only and docs-only"
            )
        aliases = operation.get("aliases")
        if not isinstance(aliases, list) or "Alatyr diagram" not in aliases:
            failures.append("diagram-discussion aliases must include Alatyr diagram")

    diagram_overlay = router.get("intent_overlays", {}).get("diagram-request")
    if not isinstance(diagram_overlay, dict) or diagram_overlay.get(
        "operation_candidates"
    ) != ["diagram-discussion"]:
        failures.append("context router diagram intent overlay does not route diagram-discussion")
    if operation_index.get("aliases", {}).get("Alatyr diagram") != "diagram-discussion":
        failures.append("operation index does not route Alatyr diagram")

    for path, snippets in {
        FLOW: [
            "Allowed Actions",
            "`read-only`",
            "`docs-only`",
            "current assistant surface entry",
            "`text-fallback`",
            "Route the accepted fact",
            "stable diagram ID",
            "Classify data sensitivity",
            "Neither allowed action",
        ],
        PRESENTATION: [
            "Status: `{DRAFT_ACCEPTED_SOURCE_OR_DERIVED_VIEW}`",
            "Presentation mode:",
            "Capability evidence:",
            "Readable text fallback:",
            "Source revision or content hash:",
            "Diagram ID:",
            "Draft revision:",
            "Data classification:",
            "External renderer or network action:",
            "is not project source of truth",
        ],
    }.items():
        text = read(path)
        for snippet in snippets:
            if snippet not in text:
                failures.append(f"{path.relative_to(ROOT)} missing {snippet}")

    surface_items = surfaces_data.get("surfaces")
    expected_surfaces = (
        {
            item["id"]
            for item in surface_items
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if isinstance(surface_items, list)
        else set()
    )
    entries = matrix_entries(read(MATRIX))
    capability_surfaces = capabilities.get("surfaces")
    if capabilities.get("schema_version") != 2:
        failures.append("assistant capability index schema_version must be 2")
    if capabilities.get("capability_kind") != "target-assistant-capability-index":
        failures.append("assistant capabilities kind is invalid")
    if not isinstance(capability_surfaces, dict):
        failures.append("assistant capabilities surfaces must be an object")
        capability_surfaces = {}
    expected_capability_keys = {
        "route",
        "native_inline_syntaxes",
        "artifact_presentation",
        "readable_fallback",
        "verified_at",
        "expires_at",
        "review_triggers",
        "client_version",
        "evidence",
    }
    for surface_id in sorted(expected_surfaces):
        block = entries.get(surface_id)
        if block is None:
            failures.append(f"bridge matrix missing surface {surface_id}")
            continue
        expected_reference = (
            "Diagram capability record: "
            f"`.ai/assistant/assistant-capabilities/{surface_id}.json`"
        )
        if expected_reference not in block:
            failures.append(f"{surface_id} bridge matrix capability reference is invalid")
        entry = capability_surfaces.get(surface_id)
        expected_path = f".ai/assistant/assistant-capabilities/{surface_id}.json"
        if entry != expected_path:
            failures.append(f"assistant capability index path is invalid for {surface_id}")
            continue
        try:
            record = load_json(TARGET / expected_path)
        except AssertionError as exc:
            failures.append(str(exc))
            continue
        if record.get("capability_kind") != "target-assistant-surface-capabilities":
            failures.append(f"{surface_id} capability record kind is invalid")
        if record.get("assistant_surface") != surface_id:
            failures.append(f"{surface_id} capability record identity is invalid")
        diagram = record.get("diagram_discussion")
        if not isinstance(diagram, dict):
            failures.append(f"assistant capabilities missing {surface_id}")
            continue
        if set(diagram) != expected_capability_keys:
            failures.append(f"{surface_id} diagram capability fields are incomplete")
        expected_placeholders = {
            "route": "{SUPPORTED_UNSUPPORTED_OR_UNKNOWN}",
            "native_inline_syntaxes": ["{SYNTAX_NONE_OR_UNKNOWN}"],
            "artifact_presentation": "{LINK_ATTACHMENT_BOTH_UNSUPPORTED_OR_UNKNOWN}",
            "readable_fallback": "{TEXT_OR_ACCESSIBLE_EQUIVALENT}",
            "verified_at": "{ISO_DATE_OR_UNKNOWN_WITH_REASON}",
            "expires_at": "{ISO_DATE_OR_REVIEW_TRIGGER_WITH_REASON}",
            "review_triggers": [
                "client version changed",
                "assistant bridge changed",
                "{TARGET_CAPABILITY_REVIEW_TRIGGER}",
            ],
            "client_version": "{CLIENT_VERSION_OR_UNKNOWN_WITH_REASON}",
            "evidence": "{TARGET_EVIDENCE_OR_MANUAL_REVIEW}",
        }
        if diagram != expected_placeholders:
            failures.append(f"{surface_id} source capability must remain placeholder-based")

    if set(capability_surfaces) != expected_surfaces:
        failures.append("assistant capability surface IDs must match conformance surfaces")

    if fixture.get("fixture_kind") != "assistant-operation-conformance":
        failures.append("diagram operation conformance fixture kind is invalid")
    if fixture.get("operation") != "diagram-discussion":
        failures.append("diagram operation conformance fixture operation is invalid")
    if fixture.get("surface_source") != "conformance/runs/assistant-surfaces.json":
        failures.append("diagram operation fixture must bind to assistant surfaces")
    fixture_expectations = fixture.get("required_for_every_surface")
    if not isinstance(fixture_expectations, list) or len(fixture_expectations) < 8:
        failures.append("diagram operation fixture has insufficient surface expectations")

    manifest_text = read(MANIFEST)
    for value in [
        'diagram_discussion: ".ai/assistant/flows/diagram-discussion.flow.md"',
        'diagram_presentation: ".ai/assistant/templates/diagram-presentation.md"',
        'capabilities: ".ai/assistant/assistant-capabilities.json"',
    ]:
        if value not in manifest_text:
            failures.append(f"target manifest missing {value}")

    module_text = read(MODULE_PROFILE)
    for value in [
        "Module: `diagrams`",
        ".ai/assistant/flows/diagram-discussion.flow.md",
        ".ai/assistant/templates/diagram-presentation.md",
        ".ai/assistant/assistant-capabilities.json",
        ".ai/assistant/bridge-capability-matrix.md",
    ]:
        if value not in module_text:
            failures.append(f"module profile missing {value}")

    for path in [HELP, HELP_REFERENCE]:
        text = read(path)
        for value in ["diagram-discussion", "Alatyr diagram"]:
            if value not in text:
                failures.append(f"{path.relative_to(ROOT)} missing {value}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "OK: checked discussion diagram rule, compact routing, security, lineage, "
        f"and operation conformance for {len(expected_surfaces)} assistant surfaces"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

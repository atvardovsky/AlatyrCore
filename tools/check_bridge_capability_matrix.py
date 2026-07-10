#!/usr/bin/env python3
"""Validate the target bridge capability matrix template.

This checks the AlatyrCore source repository only. It is not a portable
validation requirement for target projects.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX = (
    ROOT
    / "templates"
    / "target"
    / ".ai"
    / "assistant"
    / "bridge-capability-matrix.md"
)
SURFACES = ROOT / "conformance" / "runs" / "assistant-surfaces.json"

REQUIRED_FIELDS = [
    "Assistant:",
    "Surface id:",
    "Bridge paths:",
    "Auto-load behavior:",
    "Instruction priority:",
    "Supported rule/prompt/skill surfaces:",
    "Tool permission model:",
    "Routes operation help:",
    "Routes `alatyr-ai-inventory`:",
    "Routes `alatyr-adaptation`:",
    "Routes `alatyr-add-ai`:",
    "Known limitations:",
    "Conformance check:",
]

PLACEHOLDER_FIELDS = [
    "Auto-load behavior:",
    "Instruction priority:",
    "Supported rule/prompt/skill surfaces:",
    "Tool permission model:",
    "Routes operation help:",
    "Routes `alatyr-ai-inventory`:",
    "Routes `alatyr-adaptation`:",
    "Routes `alatyr-add-ai`:",
    "Known limitations:",
    "Conformance check:",
]

ENTRY_HEADING = re.compile(r"^### Assistant Surface: `([^`]+)`\s*$", re.MULTILINE)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_surfaces() -> list[dict[str, object]]:
    data = json.loads(read_text(SURFACES))
    surfaces = data.get("surfaces")
    if not isinstance(surfaces, list):
        raise ValueError("assistant-surfaces.json must contain a surfaces list")
    return [surface for surface in surfaces if isinstance(surface, dict)]


def parse_entries(text: str) -> dict[str, str]:
    matches = list(ENTRY_HEADING.finditer(text))
    entries: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        entries[match.group(1)] = text[start:end]
    return entries


def field_line(block: str, field: str) -> str:
    return next((line for line in block.splitlines() if line.startswith(field)), "")


def main() -> int:
    failures: list[str] = []

    if not MATRIX.is_file():
        print(f"FAIL: missing {MATRIX.relative_to(ROOT)}")
        return 1
    if not SURFACES.is_file():
        print(f"FAIL: missing {SURFACES.relative_to(ROOT)}")
        return 1

    try:
        surfaces = load_surfaces()
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: invalid {SURFACES.relative_to(ROOT)}: {exc}")
        return 1

    text = read_text(MATRIX)
    heading_surface_ids = [
        match.group(1) for match in ENTRY_HEADING.finditer(text)
    ]
    entries = parse_entries(text)

    for surface in surfaces:
        surface_id = surface.get("id")
        label = surface.get("label")
        bridge_paths = surface.get("bridge_paths")
        if not isinstance(surface_id, str) or not surface_id:
            failures.append("assistant surface missing string id")
            continue
        if not isinstance(label, str) or not label:
            failures.append(f"{surface_id} missing string label")
        if not isinstance(bridge_paths, list) or not bridge_paths:
            failures.append(f"{surface_id} missing bridge_paths list")
            bridge_paths = []

        block = entries.get(surface_id)
        if block is None:
            failures.append(f"missing bridge capability entry for {surface_id}")
            continue

        for field in REQUIRED_FIELDS:
            if field not in block:
                failures.append(f"{surface_id} missing field {field}")

        if f"Surface id: `{surface_id}`" not in block:
            failures.append(f"{surface_id} heading and Surface id field disagree")
        if isinstance(label, str) and f"Assistant: `{label}`" not in block:
            failures.append(f"{surface_id} assistant label should be `{label}`")

        for bridge_path in bridge_paths:
            if not isinstance(bridge_path, str):
                failures.append(f"{surface_id} bridge path must be a string")
                continue
            if f"- `{bridge_path}`" not in block:
                failures.append(f"{surface_id} missing bridge path {bridge_path}")

        for field in PLACEHOLDER_FIELDS:
            line = field_line(block, field)
            if "{" not in line:
                failures.append(f"{surface_id} {field} should remain placeholder-based")

    duplicate_surface_ids = [
        surface_id
        for surface_id in heading_surface_ids
        if heading_surface_ids.count(surface_id) > 1
    ]
    for surface_id in sorted(set(duplicate_surface_ids)):
        failures.append(f"duplicate bridge capability entry for {surface_id}")

    known_surface_ids = {
        surface.get("id") for surface in surfaces if isinstance(surface.get("id"), str)
    }
    extra_surface_ids = sorted(set(entries) - known_surface_ids)
    for surface_id in extra_surface_ids:
        failures.append(f"bridge capability entry has unknown surface id: {surface_id}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(
        "OK: checked bridge capability matrix with "
        f"{len(known_surface_ids)} assistant surfaces"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

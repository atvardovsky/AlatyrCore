#!/usr/bin/env python3
"""Validate the source-of-truth registry template.

This checks the AlatyrCore source repository only. It is not a portable
validation requirement for target projects.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = (
    ROOT
    / "templates"
    / "target"
    / ".ai"
    / "project"
    / "source-of-truth-registry.md"
)

REQUIRED_FACT_TYPES = [
    "product behavior",
    "business rule",
    "architecture decision",
    "data model",
    "validation command",
    "security policy",
    "assistant operation",
    "AI infrastructure item",
]

REQUIRED_FIELDS = [
    "Fact type:",
    "Canonical owner:",
    "Consistency level:",
    "Project area:",
    "Consistency map node:",
    "Relationship coverage:",
    "Invariant and dependency constraints:",
    "Derived surfaces:",
    "Sync direction:",
    "Validation or manual review:",
    "Conflict resolver:",
    "Approval trigger:",
    "Final evidence:",
]

ENTRY_HEADING = re.compile(r"^### Fact Type: `([^`]+)`\s*$", re.MULTILINE)


def read_registry() -> str:
    return REGISTRY.read_text(encoding="utf-8")


def parse_entries(text: str) -> dict[str, str]:
    matches = list(ENTRY_HEADING.finditer(text))
    entries: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        entries[match.group(1)] = text[start:end]
    return entries


def main() -> int:
    failures: list[str] = []

    if not REGISTRY.is_file():
        print(f"FAIL: missing {REGISTRY.relative_to(ROOT)}")
        return 1

    text = read_registry()
    heading_fact_types = [match.group(1) for match in ENTRY_HEADING.finditer(text)]
    entries = parse_entries(text)

    for fact_type in REQUIRED_FACT_TYPES:
        block = entries.get(fact_type)
        if block is None:
            failures.append(f"missing registry entry for fact type: {fact_type}")
            continue

        for field in REQUIRED_FIELDS:
            if field not in block:
                failures.append(f"{fact_type} missing field {field}")

        if f"Fact type: `{fact_type}`" not in block:
            failures.append(f"{fact_type} heading and Fact type field disagree")

        if fact_type == "AI infrastructure item":
            for field in [
                "AI infrastructure router item:",
                "Adaptation record:",
            ]:
                line = next(
                    (line for line in block.splitlines() if line.startswith(field)),
                    "",
                )
                if "{" not in line:
                    failures.append(f"{fact_type} {field} should be placeholder-based")

        canonical_line = next(
            (line for line in block.splitlines() if line.startswith("Canonical owner:")),
            "",
        )
        if "{" not in canonical_line:
            failures.append(f"{fact_type} canonical owner should remain placeholder-based")

        if not re.search(r"Derived surfaces:\s*\n\s*-\s*`?\{[^}]+\}`?", block):
            failures.append(f"{fact_type} derived surfaces must include a placeholder bullet")

        for field in [
            "Consistency level:",
            "Project area:",
            "Consistency map node:",
            "Relationship coverage:",
            "Invariant and dependency constraints:",
            "Sync direction:",
            "Validation or manual review:",
            "Conflict resolver:",
            "Approval trigger:",
            "Final evidence:",
        ]:
            line = next((line for line in block.splitlines() if line.startswith(field)), "")
            if "{" not in line:
                failures.append(f"{fact_type} {field} should remain placeholder-based")

    duplicate_fact_types = [
        fact_type
        for fact_type in heading_fact_types
        if heading_fact_types.count(fact_type) > 1
    ]
    for fact_type in sorted(set(duplicate_fact_types)):
        failures.append(f"duplicate registry entry for fact type: {fact_type}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(
        "OK: checked source-of-truth registry template with "
        f"{len(REQUIRED_FACT_TYPES)} baseline fact types"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

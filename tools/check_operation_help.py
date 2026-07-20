#!/usr/bin/env python3
"""Validate installed-operation help template shape.

This validates AlatyrCore source templates only. It is not a portable
framework requirement for target projects.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
HELP = TARGET / ".ai" / "assistant" / "help.md"
REFERENCE = TARGET / ".ai" / "assistant" / "help-reference.md"

OPERATION_HEADING = re.compile(r"^Operation: `([^`]+)`\s*$", re.MULTILINE)

SHORT_HELP_REQUIRED = [
    "# Alatyr Help",
    "These aliases are chat/request shortcuts, not shell commands.",
    "Full operation reference: `.ai/assistant/help-reference.md`.",
    "Canonical operation catalog: `.ai/assistant/operation-catalog.json`.",
    "Alatyr status",
    "Default routing:",
    ".ai/assistant/context-profiles.md",
    ".ai/assistant/module-profile.md",
    "## Quick Operations",
    "## Minimal Request Shape",
    "Allowed actions:",
    "## When Unsure",
]

REFERENCE_REQUIRED = [
    "# Alatyr Help Reference",
    "## Supported Request Aliases",
    "## Operation Menu",
    "## Operation Type Aliases",
    "## Request Shape",
    "Allowed actions guide:",
    "## Target Notes",
    ".ai/assistant/operation-catalog.json",
    "Operation: `adapter-health`",
    "alatyr-ai-inventory",
    "alatyr-suggest-ai {RECOMMENDATION_SCOPE}",
    "alatyr-improve-ai {AI_INFRASTRUCTURE_ITEM_ID}",
    "alatyr-adaptation {AI_INFRASTRUCTURE_SOURCE}",
    "alatyr-add-ai {AI_INFRASTRUCTURE_SOURCE}",
]

OPERATION_FIELDS = [
    "Use when:",
    "Flow:",
    "Minimum input:",
]

ALLOWED_ACTIONS = [
    "`read-only`",
    "`docs-only`",
    "`adapter-only`",
    "`code-and-tests`",
    "`full-with-approval`",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_blocks(text: str) -> dict[str, str]:
    matches = list(OPERATION_HEADING.finditer(text))
    blocks: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[match.group(1)] = text[start:end]
    return blocks


def main() -> int:
    failures: list[str] = []

    help_text = read(HELP)
    reference_text = read(REFERENCE)

    if "| Operation |" in help_text:
        failures.append("help.md should use operation blocks, not a table")
    if len(help_text.splitlines()) > 150:
        failures.append("help.md should stay under 150 lines")

    for required_text in SHORT_HELP_REQUIRED:
        if required_text not in help_text:
            failures.append(f"help.md missing {required_text}")

    for required_text in REFERENCE_REQUIRED:
        if required_text not in reference_text:
            failures.append(f"help-reference.md missing {required_text}")

    reference_blocks = parse_blocks(reference_text)
    if not reference_blocks:
        failures.append("help-reference.md has no operation blocks")
    for operation, block in reference_blocks.items():
        for field in OPERATION_FIELDS:
            if field not in block:
                failures.append(
                    f"help-reference.md operation {operation} missing {field}"
                )

    for action in ALLOWED_ACTIONS:
        if action not in reference_text:
            failures.append(f"help-reference.md missing allowed action {action}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "OK: checked operation help shape with "
        f"{len(reference_blocks)} reference operations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

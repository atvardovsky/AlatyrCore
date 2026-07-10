#!/usr/bin/env python3
"""Validate the target maturity profile template.

This checks the AlatyrCore source repository only. It is not a portable
validation requirement for target projects.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE = (
    ROOT
    / "templates"
    / "target"
    / ".ai"
    / "assistant"
    / "maturity-profile.md"
)

REQUIRED_TASK_AREAS = [
    "documentation",
    "code-changes",
    "architecture",
    "data",
    "security",
    "ai-infrastructure",
    "framework-upgrade",
]

REQUIRED_FIELDS = [
    "Task area:",
    "Maturity:",
    "Supported work:",
    "Required context:",
    "Required owners present:",
    "Validation or manual review:",
    "Approval needs:",
    "Blocking criteria:",
    "Residual risks:",
    "Final evidence:",
]

ENTRY_HEADING = re.compile(r"^### Task Area: `([^`]+)`\s*$", re.MULTILINE)


def read_profile() -> str:
    return PROFILE.read_text(encoding="utf-8")


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

    if not PROFILE.is_file():
        print(f"FAIL: missing {PROFILE.relative_to(ROOT)}")
        return 1

    text = read_profile()
    heading_task_areas = [match.group(1) for match in ENTRY_HEADING.finditer(text)]
    entries = parse_entries(text)

    for task_area in REQUIRED_TASK_AREAS:
        block = entries.get(task_area)
        if block is None:
            failures.append(f"missing maturity entry for task area: {task_area}")
            continue

        for field in REQUIRED_FIELDS:
            if field not in block:
                failures.append(f"{task_area} missing field {field}")

        if f"Task area: `{task_area}`" not in block:
            failures.append(f"{task_area} heading and Task area field disagree")

        for field in [
            "Maturity:",
            "Supported work:",
            "Required owners present:",
            "Validation or manual review:",
            "Approval needs:",
            "Blocking criteria:",
            "Residual risks:",
            "Final evidence:",
        ]:
            line = next((line for line in block.splitlines() if line.startswith(field)), "")
            if "{" not in line:
                failures.append(f"{task_area} {field} should remain placeholder-based")

        if not re.search(r"Required context:\s*\n\s*-\s*`?\{[^}]+\}`?", block):
            failures.append(f"{task_area} required context must include a placeholder bullet")

    duplicate_task_areas = [
        task_area
        for task_area in heading_task_areas
        if heading_task_areas.count(task_area) > 1
    ]
    for task_area in sorted(set(duplicate_task_areas)):
        failures.append(f"duplicate maturity entry for task area: {task_area}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(
        "OK: checked maturity profile template with "
        f"{len(REQUIRED_TASK_AREAS)} task areas"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

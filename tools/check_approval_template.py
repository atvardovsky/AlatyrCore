#!/usr/bin/env python3
"""Validate the target approval-record template.

This checks the AlatyrCore source repository only. It is not a portable
validation requirement for target projects.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (
    ROOT
    / "templates"
    / "target"
    / ".ai"
    / "assistant"
    / "approvals"
    / "approval-template.md"
)

REQUIRED_FIELDS = [
    "Approval ID:",
    "Operation ID:",
    "Operation type:",
    "Plan version:",
    "Plan hash:",
    "Requested by:",
    "Approved by:",
    "Approved at:",
    "Approval source/message:",
    "Expires at or reuse policy:",
    "Scope invalidation rule:",
    "Allowed actions mode:",
    "Used by operation/change:",
    "Patch changed after approval:",
    "Implementation stayed within approved scope:",
    "Validation run:",
    "Result/evidence:",
    "Residual risk:",
]

REQUIRED_SECTIONS = [
    "## Approved Scope",
    "## Plan Evidence",
    "## Use Result",
]

REQUIRED_LIST_FIELDS = [
    "Allowed protected changes:",
    "Allowed files or surfaces:",
    "Excluded actions:",
    "Approved validation or manual review:",
]

REQUIRED_CODE_BLOCK_FIELDS = [
    "Approved plan summary:",
]


def read_template() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def field_line(text: str, field: str) -> str:
    return next((line for line in text.splitlines() if line.startswith(field)), "")


def has_placeholder_list(text: str, field: str) -> bool:
    pattern = rf"{re.escape(field)}\s*\n\s*\n\s*-\s*`?\{{[^}}]+\}}`?"
    return re.search(pattern, text) is not None


def main() -> int:
    failures: list[str] = []

    if not TEMPLATE.is_file():
        print(f"FAIL: missing {TEMPLATE.relative_to(ROOT)}")
        return 1

    text = read_template()

    for section in REQUIRED_SECTIONS:
        if section not in text:
            failures.append(f"missing section {section}")

    for field in REQUIRED_FIELDS:
        line = field_line(text, field)
        if not line:
            failures.append(f"missing field {field}")
            continue
        if "{" not in line:
            failures.append(f"{field} should remain placeholder-based")

    for field in REQUIRED_LIST_FIELDS:
        if field not in text:
            failures.append(f"missing list field {field}")
            continue
        if not has_placeholder_list(text, field):
            failures.append(f"{field} must include a placeholder bullet")

    for field in REQUIRED_CODE_BLOCK_FIELDS:
        if field not in text:
            failures.append(f"missing code block field {field}")
            continue
        pattern = rf"{re.escape(field)}\s*\n\s*\n```text\s*\n\{{[^}}]+\}}\s*\n```"
        if re.search(pattern, text) is None:
            failures.append(f"{field} must include a placeholder text block")

    if "Plan hash:" in text and "Scope invalidation rule:" not in text:
        failures.append("plan hash requires a scope invalidation rule")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(
        "OK: checked approval template with "
        f"{len(REQUIRED_FIELDS)} scalar fields"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

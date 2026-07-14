#!/usr/bin/env python3
"""Validate the target approval-record template.

This checks the AlatyrCore source repository only. It is not a portable
validation requirement for target projects.
"""

from __future__ import annotations

import json
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
MACHINE_TEMPLATE = TEMPLATE.with_name("approval-record-template.json")

REQUIRED_FIELDS = [
    "Approval ID:",
    "Operation ID:",
    "Operation type:",
    "Plan version:",
    "Plan hash:",
    "Approved plan file:",
    "Approved diff base:",
    "Patch hash:",
    "Requested by:",
    "Approved by:",
    "Approved at:",
    "Repository revision at approval:",
    "Approval source/message:",
    "Expires at or reuse policy:",
    "Scope invalidation rule:",
    "Machine-readable record:",
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
    "Excluded files or surfaces:",
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
    if "Evidence classification: `historical-record`" not in text:
        failures.append("approval template must classify itself as historical evidence")
    if "approval-record-template.json" not in text:
        failures.append("approval template must route to its machine-readable record")

    if not MACHINE_TEMPLATE.is_file():
        failures.append("missing machine-readable approval record template")
    else:
        try:
            data = json.loads(MACHINE_TEMPLATE.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"invalid machine-readable approval template: {exc}")
            data = {}
        if data.get("schema_version") != 1:
            failures.append("machine approval template schema_version must be 1")
        if data.get("record_kind") != "alatyr-approval-record":
            failures.append("machine approval template record_kind is invalid")
        if data.get("evidence_classification") != "historical-record":
            failures.append("machine approval template evidence class is invalid")
        for container in ["operation", "plan", "diff", "scope", "approval", "use_result"]:
            if not isinstance(data.get(container), dict):
                failures.append(f"machine approval template missing object {container}")
        scope = data.get("scope", {})
        if isinstance(scope, dict):
            for field in [
                "allowed_protected_changes",
                "allowed_files_or_surfaces",
                "excluded_files_or_surfaces",
                "excluded_actions",
            ]:
                values = scope.get(field)
                if not isinstance(values, list) or not values:
                    failures.append(f"machine approval template missing list scope.{field}")
                elif not all(isinstance(value, str) and "{" in value for value in values):
                    failures.append(f"machine approval template scope.{field} must use placeholders")
        serialized = json.dumps(data)
        for placeholder in [
            "{APPROVAL_ID}",
            "{APPROVED_GIT_DIFF_BASE}",
            "{TARGET_RELATIVE_FILE_OR_GLOB}",
            "{APPROVAL_INVALIDATION_RULE}",
        ]:
            if placeholder not in serialized:
                failures.append(f"machine approval template missing {placeholder}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(
        "OK: checked approval template with "
        f"{len(REQUIRED_FIELDS)} scalar fields and machine-readable scope"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

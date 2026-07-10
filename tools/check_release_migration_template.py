#!/usr/bin/env python3
"""Validate source release migration report template structure.

This validates the AlatyrCore source repository only. It is not a portable
framework requirement for target projects.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs" / "release-migration-report-template.md"
REPORTER = ROOT / "tools" / "report_migration_diff.py"

REQUIRED_TEMPLATE_TEXT = [
    "# Alatyr Release Migration Report",
    "not a target adapter migration note",
    "Report ID:",
    "Prepared by:",
    "Prepared at:",
    "## Version Scope",
    "From manifest:",
    "To manifest:",
    "From framework version:",
    "To framework version:",
    "From adapter schema version:",
    "To adapter schema version:",
    "From template version:",
    "To template version:",
    "## Rule Changes",
    "## Adapter Contract Impact",
    "Framework version:",
    "Adapter schema version:",
    "Template version:",
    "Rule registry:",
    "Rule ownership:",
    "Framework files:",
    "Target template surfaces:",
    "## Affected Rule Categories",
    "## Affected Task Profiles",
    "## Affected Canonical Sources",
    "## Migration Action Hints",
    "Added rules:",
    "Changed rules:",
    "Removed rules:",
    "Unchanged rules:",
    "## Rule Owner Changes",
    "Added rule owner categories:",
    "Changed rule owner categories:",
    "Removed rule owner categories:",
    "## Framework File Changes",
    "Added framework files:",
    "Changed framework files:",
    "Removed framework files:",
    "## Target Template Surface Changes",
    "Added target template surfaces:",
    "Changed target template surfaces:",
    "Removed target template surfaces:",
    "## Required Target Actions",
    "## Optional Target Actions",
    "## Approval Needs",
    "Approval needed:",
    "Approval scope:",
    "## Validation Run",
    "Source validation:",
    "Target validation:",
    "## Residual Risks",
    "## Safety",
    "evidence only",
]

REQUIRED_REPORTER_TEXT = [
    "Alatyr Release Migration Report",
    "Version Scope",
    "Rule Owner Changes",
    "Adapter Contract Impact",
    "Affected Rule Categories",
    "Affected Task Profiles",
    "Affected Canonical Sources",
    "Migration Action Hints",
    "Target Template Surface Changes",
    "Approval Needs",
    "Validation Run",
    "Residual Risks",
    "--from-template-dir",
    "--to-template-dir",
    "release-migration-report-template.md",
]


def validate() -> List[str]:
    failures: List[str] = []
    try:
        template_text = TEMPLATE.read_text(encoding="utf-8")
        reporter_text = REPORTER.read_text(encoding="utf-8")
    except OSError as exc:
        return [str(exc)]

    for required in REQUIRED_TEMPLATE_TEXT:
        if required not in template_text:
            failures.append(f"docs/release-migration-report-template.md missing {required}")
    for required in REQUIRED_REPORTER_TEXT:
        if required not in reporter_text:
            failures.append(f"tools/report_migration_diff.py missing {required}")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: checked release migration report template")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

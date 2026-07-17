#!/usr/bin/env python3
"""Validate the AI infrastructure inventory target template.

This validates AlatyrCore source templates only. It is not a portable
framework requirement for target projects.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (
    ROOT
    / "templates"
    / "target"
    / ".ai"
    / "assistant"
    / "templates"
    / "ai-infrastructure-inventory.md"
)
FLOW = (
    ROOT
    / "templates"
    / "target"
    / ".ai"
    / "assistant"
    / "flows"
    / "ai-infrastructure-inventory.flow.md"
)

REQUIRED_TEMPLATE_TEXT = [
    "# AI Infrastructure Inventory",
    "Inventory-only work must not import",
    "## Inventory Scope",
    "## Item Record",
    "## Summary",
    "Item id:",
    "Router route:",
    "Router item status:",
    "Item type:",
    "Path or reference:",
    "Owner:",
    "Source/provenance:",
    "Source type:",
    "Source hash or commit:",
    "License:",
    "Supported assistants:",
    "Declared purpose:",
    "Project-contour relevance:",
    "Observed usage or outcome evidence:",
    "Staleness or maintenance signal:",
    "Permission surface:",
    "Prompt-injection risk:",
    "Safety surface:",
    "Overlap or conflict:",
    "Validation or manual review:",
    "Approval status:",
    "Required gates and output contract:",
    "Preliminary disposition:",
    "Residual risk:",
    "Recommended next operation:",
    "Need evidence-based recommendation review:",
]

PLACEHOLDER_FIELDS = [
    "- Operation id:",
    "- Inventory date:",
    "- Allowed actions:",
    "- Target assistant surfaces:",
    "- Surfaces inspected:",
    "- Item id:",
    "- Router route:",
    "- Router item status:",
    "- Path or reference:",
    "- Source/provenance:",
    "- Source hash or commit:",
    "- License:",
    "- Supported assistants:",
    "- Declared purpose:",
    "- Project-contour relevance:",
    "- Staleness or maintenance signal:",
    "- Permission surface:",
    "- Prompt-injection risk:",
    "- Validation or manual review:",
    "- Approval status:",
    "- Required gates and output contract:",
    "- Preliminary disposition:",
    "- Residual risk:",
]

REQUIRED_FLOW_TEXT = [
    ".ai/assistant/templates/ai-infrastructure-inventory.md",
    ".ai/assistant/ai-infrastructure-router.json",
    "source hash, commit, version, license",
    "prompt-injection risk notes",
    "Do not import or normalize external infrastructure during inventory-only",
    ".ai/assistant/flows/ai-infrastructure-recommendation.flow.md",
    "`recommend` route",
]


def field_line(text: str, field: str) -> str:
    return next((line for line in text.splitlines() if line.startswith(field)), "")


def main() -> int:
    failures: list[str] = []

    if not TEMPLATE.is_file():
        print(f"FAIL: missing {TEMPLATE.relative_to(ROOT)}", file=sys.stderr)
        return 1
    if not FLOW.is_file():
        print(f"FAIL: missing {FLOW.relative_to(ROOT)}", file=sys.stderr)
        return 1

    template_text = TEMPLATE.read_text(encoding="utf-8")
    flow_text = FLOW.read_text(encoding="utf-8")

    for required_text in REQUIRED_TEMPLATE_TEXT:
        if required_text not in template_text:
            failures.append(
                f"{TEMPLATE.relative_to(ROOT)} missing {required_text}"
            )

    for field in PLACEHOLDER_FIELDS:
        line = field_line(template_text, field)
        if not line:
            failures.append(f"{TEMPLATE.relative_to(ROOT)} missing field {field}")
        elif "{" not in line:
            failures.append(
                f"{TEMPLATE.relative_to(ROOT)} field {field} must remain "
                "placeholder-based"
            )

    for required_text in REQUIRED_FLOW_TEXT:
        if required_text not in flow_text:
            failures.append(f"{FLOW.relative_to(ROOT)} missing {required_text}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("OK: checked AI infrastructure inventory template and flow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

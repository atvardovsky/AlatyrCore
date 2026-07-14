#!/usr/bin/env python3
"""Validate target adapter output contract templates.

This validates AlatyrCore source templates only. It is not a portable
framework requirement for target projects.
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
    / "templates"
    / "adapter-output-contracts.md"
)
INSTALL_FLOW = ROOT / "installer" / "assistant-installation.flow.md"
INSTALL_NOTE = (
    ROOT
    / "templates"
    / "target"
    / ".ai"
    / "assistant"
    / "templates"
    / "installation-note.md"
)

CONTRACT_HEADING = re.compile(r"^## Contract: `([^`]+)`\s*$", re.MULTILINE)

REQUIRED_CONTRACTS = {
    "installation-output",
    "framework-update-output",
    "adapter-recheck-output",
}

REQUIRED_FIELDS = [
    "Operation id:",
    "Operation type:",
    "Evidence basis:",
    "Observed at:",
    "Observed repository revision:",
    "Historical records used:",
    "Unverifiable historical claims:",
    "Framework version:",
    "Adapter schema version:",
    "Template version:",
    "Manifest path:",
    "Approval records used:",
    "Approval scope enforcement:",
    "Surfaces created:",
    "Surfaces updated:",
    "Surfaces skipped:",
    "Existing files preserved:",
    "Required core profile result:",
    "Optional module profile result:",
    "Context profiles result:",
    "Context receipt and cost evidence:",
    "Large-task orchestration result:",
    "Operation packet template result:",
    "Source-of-truth registry result:",
    "Consistency-map result:",
    "Logical integrity evidence:",
    "Task-specific maturity result:",
    "Bridge capability matrix result:",
    "Adapter drift checks result:",
    "Local path leakage result:",
    "Target-local checker status:",
    "AI infrastructure router result:",
    "AI infrastructure adaptation-record result:",
    "Validation run:",
    "Validation skipped or unresolved:",
    "Final evidence:",
    "Residual risk:",
]

REQUIRED_INSTALLATION_TEXT = [
    "Adapter output contracts:",
    ".ai/assistant/templates/adapter-output-contracts.md",
]

REQUIRED_FLOW_TEXT = [
    ".ai/assistant/templates/adapter-output-contracts.md",
    "output contract",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_blocks(text: str) -> dict[str, str]:
    matches = list(CONTRACT_HEADING.finditer(text))
    blocks: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[match.group(1)] = text[start:end]
    return blocks


def line_for(block: str, field: str) -> str:
    return next((line for line in block.splitlines() if field in line), "")


def main() -> int:
    failures: list[str] = []

    if not TEMPLATE.is_file():
        print(f"FAIL: missing {TEMPLATE.relative_to(ROOT)}", file=sys.stderr)
        return 1

    template_text = read(TEMPLATE)
    blocks = parse_blocks(template_text)

    missing_contracts = sorted(REQUIRED_CONTRACTS - set(blocks))
    if missing_contracts:
        failures.append(f"missing output contract(s): {missing_contracts}")

    for contract in sorted(REQUIRED_CONTRACTS):
        block = blocks.get(contract, "")
        for field in REQUIRED_FIELDS:
            if field not in block:
                failures.append(f"{contract} missing field {field}")
                continue
            line = line_for(block, field)
            if field != "Manifest path:" and "{" not in line:
                failures.append(
                    f"{contract} field {field} must remain placeholder-based"
                )

    for contract in ["framework-update-output", "adapter-recheck-output"]:
        if "Migration assessment result/path:" not in blocks.get(contract, ""):
            failures.append(f"{contract} missing migration assessment evidence")

    installation_note_text = read(INSTALL_NOTE)
    for required_text in REQUIRED_INSTALLATION_TEXT:
        if required_text not in installation_note_text:
            failures.append(
                f"{INSTALL_NOTE.relative_to(ROOT)} missing {required_text}"
            )

    install_flow_text = read(INSTALL_FLOW)
    for required_text in REQUIRED_FLOW_TEXT:
        if required_text not in install_flow_text:
            failures.append(
                f"{INSTALL_FLOW.relative_to(ROOT)} missing {required_text}"
            )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(f"OK: checked {len(blocks)} target adapter output contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

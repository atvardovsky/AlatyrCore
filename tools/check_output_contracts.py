#!/usr/bin/env python3
"""Validate target adapter output contract templates.

This validates AlatyrCore source templates only. It is not a portable
framework requirement for target projects.
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
COMPLETION_TEMPLATE = (
    ROOT
    / "templates"
    / "target"
    / ".ai"
    / "assistant"
    / "templates"
    / "operation-completion-evidence.json"
)
FINAL_EVIDENCE_GATE = (
    ROOT / "templates" / "target" / ".ai" / "assistant" / "gates" / "final-evidence.md"
)
CODE_AND_TESTS_GATE = (
    ROOT / "templates" / "target" / ".ai" / "assistant" / "gates" / "code-and-tests.md"
)
TESTING_GUIDANCE = ROOT / "framework" / "testing-guidance.md"

CONTRACT_HEADING = re.compile(r"^## Contract: `([^`]+)`\s*$", re.MULTILINE)

REQUIRED_CONTRACTS = {
    "operation-completion-evidence",
    "adapter-health-output",
    "installation-output",
    "framework-update-output",
    "adapter-recheck-output",
}

COMPLETION_CONTRACT_FIELDS = [
    "Template path:",
    "Operation id:",
    "Operation type:",
    "Operation status:",
    "Completion claim:",
    "Current user authorization:",
    "Context receipt result:",
    "Changed facts:",
    "Validation completion basis:",
    "Tests run:",
    "Required checks:",
    "Skipped or unavailable checks:",
    "Logical integrity result:",
    "Companion surfaces:",
    "Approval scope result:",
    "Residual risks:",
    "May claim complete:",
    "Blocking reasons:",
    "Next owner or action:",
]

COMPLETION_TEMPLATE_FIELDS = [
    "record_kind",
    "operation",
    "current_user_authorization",
    "context_receipt",
    "changed_facts",
    "validation",
    "consistency",
    "completion_gate",
]

FINAL_EVIDENCE_TEXT = [
    "operation-completion-evidence.json",
    "Completion semantics:",
    "Report `complete` only when current authorization covers performed phases",
    "Report `partial`, `blocked`, or `unverified`",
    "semantic scope it proves",
]

CODE_AND_TESTS_TEXT = [
    "Test evidence classes:",
    "`passed`",
    "`failed`",
    "`skipped`",
    "`unavailable`",
    "`not-applicable`",
    "Completion guard:",
    "Code changes without runnable or explicitly not-applicable target validation",
]

TESTING_GUIDANCE_TEXT = [
    "## Completion Evidence",
    "Testing evidence is scoped evidence.",
    "partial`, `blocked`, or `unverified`",
]

REQUIRED_FIELDS = [
    "Operation id:",
    "Operation type:",
    "Current user authorization:",
    "Evidence basis:",
    "Observed at:",
    "Observed repository revision:",
    "Historical records used:",
    "Unverifiable historical claims:",
    "Framework version:",
    "Adapter schema version:",
    "Template version:",
    "Manifest path:",
    "Installation state:",
    "Installation transition record:",
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
    "AI infrastructure recommendation result:",
    "Development-pattern evidence result:",
    "AI infrastructure adaptation-record result:",
    "Validation run:",
    "Validation skipped or unresolved:",
    "Final evidence:",
    "Residual risk:",
]

DELIVERY_FIELDS = {
    "installation-output": [
        "Post-install message result:",
        "Post-install delivery status:",
        "Post-install delivery mechanism:",
        "Post-install delivery reason:",
        "Post-install delivery observed at:",
    ],
    "framework-update-output": [
        "Post-update message result:",
        "Post-update delivery status:",
        "Post-update delivery mechanism:",
        "Post-update delivery reason:",
        "Post-update delivery observed at:",
    ],
}

HEALTH_REQUIRED_FIELDS = [
    "Operation id:",
    "Operation type:",
    "Current user authorization:",
    "Evidence basis:",
    "Observed at:",
    "Observed repository branch:",
    "Observed repository revision:",
    "Manifest path:",
    "Health state:",
    "Installation state:",
    "Installation transition record:",
    "Validation phase:",
    "Acceptance eligible:",
    "Required final strict rerun:",
    "Checks run:",
    "Checks unavailable:",
    "Finding counts:",
    "Blocking findings:",
    "Attention findings:",
    "Repair operations:",
    "Automatic repair performed:",
    "Files changed:",
    "Residual risk:",
]

REQUIRED_MESSAGE_TEXT = [
    "Adapter health:",
    "{READY_ATTENTION_BLOCKED_OR_UNVERIFIED",
    "Delivery status: `{SENT_SKIPPED_OR_BLOCKED}`",
    "Delivery mechanism: `{CHAT_SURFACE_OR_UNAVAILABLE}`",
    "Delivery reason: `{WHY_SENT_SKIPPED_OR_BLOCKED}`",
    "Delivery observed at: `{DELIVERY_TIMESTAMP_OR_NOT_OBSERVED}`",
    "The presence of this file never proves that a chat message reached a user.",
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

    completion_block = blocks.get("operation-completion-evidence", "")
    for field in COMPLETION_CONTRACT_FIELDS:
        if field not in completion_block:
            failures.append(f"operation-completion-evidence missing field {field}")
            continue
        line = line_for(completion_block, field)
        if field != "Template path:" and "{" not in line:
            failures.append(
                f"operation-completion-evidence field {field} must remain placeholder-based"
            )
    for required in [
        "Do not report `complete`",
        "current authorization is missing",
        "approval scope is required but unverified",
    ]:
        if required not in completion_block:
            failures.append(f"operation-completion-evidence missing {required}")

    try:
        completion_data = json.loads(read(COMPLETION_TEMPLATE))
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"invalid {COMPLETION_TEMPLATE.relative_to(ROOT)}: {exc}")
        completion_data = {}
    if not isinstance(completion_data, dict):
        failures.append(
            f"{COMPLETION_TEMPLATE.relative_to(ROOT)} must contain a JSON object"
        )
        completion_data = {}
    if completion_data.get("schema_version") != 1:
        failures.append("operation-completion evidence schema_version must be 1")
    if completion_data.get("record_kind") != "alatyr-operation-completion-evidence":
        failures.append("operation-completion evidence record_kind is invalid")
    for field in COMPLETION_TEMPLATE_FIELDS:
        if field not in completion_data:
            failures.append(f"operation-completion evidence missing {field}")
    if "{" not in read(COMPLETION_TEMPLATE):
        failures.append("operation-completion evidence template must remain placeholder-based")
    if completion_data.get("completion_gate", {}).get("may_claim_complete") != (
        "{TRUE_ONLY_WHEN_REQUIRED_EVIDENCE_PASSED_OR_IS_NOT_APPLICABLE}"
    ):
        failures.append("operation-completion evidence must gate complete claims")

    for contract in sorted(
        REQUIRED_CONTRACTS - {"adapter-health-output", "operation-completion-evidence"}
    ):
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
        for field in DELIVERY_FIELDS.get(contract, []):
            if field not in block:
                failures.append(f"{contract} missing delivery field {field}")

    health_block = blocks.get("adapter-health-output", "")
    for field in HEALTH_REQUIRED_FIELDS:
        if field not in health_block:
            failures.append(f"adapter-health-output missing field {field}")
            continue
        line = line_for(health_block, field)
        if field not in {"Manifest path:", "Operation type:", "Automatic repair performed:", "Files changed:"} and "{" not in line:
            failures.append(
                f"adapter-health-output field {field} must remain placeholder-based"
            )
    for required in [
        "adapter-health",
        "{READY_ATTENTION_BLOCKED_OR_UNVERIFIED}",
        "`false`",
        "`none`",
    ]:
        if required not in health_block:
            failures.append(f"adapter-health-output missing {required}")

    for contract in ["framework-update-output", "adapter-recheck-output"]:
        if "Migration assessment result/path:" not in blocks.get(contract, ""):
            failures.append(f"{contract} missing migration assessment evidence")

    for path, required_items in [
        (FINAL_EVIDENCE_GATE, FINAL_EVIDENCE_TEXT),
        (CODE_AND_TESTS_GATE, CODE_AND_TESTS_TEXT),
        (TESTING_GUIDANCE, TESTING_GUIDANCE_TEXT),
    ]:
        text = read(path)
        for required_text in required_items:
            if required_text not in text:
                failures.append(f"{path.relative_to(ROOT)} missing {required_text}")

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

    for filename in ["post-install-message.md", "post-update-message.md"]:
        message = TEMPLATE.parent / filename
        message_text = read(message)
        for required_text in REQUIRED_MESSAGE_TEXT:
            if required_text not in message_text:
                failures.append(f"{message.relative_to(ROOT)} missing {required_text}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(f"OK: checked {len(blocks)} target adapter output contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate the target module profile template.

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
    / "module-profile.md"
)

CORE_ITEMS = [
    "contours",
    "manifest-and-versioning",
    "adapter-ownership",
    "context-profiles",
    "source-of-truth-registry",
    "risk-approval-integrity",
    "validation-and-final-evidence",
]

OPTIONAL_MODULES = [
    "blueprint-change",
    "consistency-map",
    "architecture-knowledge",
    "diagrams",
    "ai-infrastructure",
    "multi-assistant-bridges",
    "installed-operations",
    "large-task-orchestration",
    "change-packages",
    "team-collaboration",
    "durable-approvals",
    "migration-diff",
    "effectiveness-metrics",
    "scaffolding",
]

CORE_FIELDS = [
    "State:",
    "Owner or file:",
    "Required files:",
    "Evidence:",
    "Validation or review:",
    "Approval needs:",
    "Residual risk:",
]

MODULE_FIELDS = [
    "State:",
    "Owner or file:",
    "Required files:",
    "Reason:",
    "Validation or review:",
    "Approval needs:",
    "Residual risk:",
    "Next action:",
]

CORE_HEADING = re.compile(r"^Core item: `([^`]+)`\s*$", re.MULTILINE)
MODULE_HEADING = re.compile(r"^Module: `([^`]+)`\s*$", re.MULTILINE)


def read_profile() -> str:
    return PROFILE.read_text(encoding="utf-8")


def parse_blocks(text: str, pattern: re.Pattern[str]) -> dict[str, str]:
    matches = list(pattern.finditer(text))
    blocks: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[match.group(1)] = text[start:end]
    return blocks


def line_for(block: str, field: str) -> str:
    return next((line for line in block.splitlines() if line.startswith(field)), "")


def has_required_file_bullet(block: str) -> bool:
    return re.search(r"Required files:\s*\n\s*-\s+`?[^`\n]+`?", block) is not None


def check_block(
    failures: list[str],
    block_name: str,
    block: str,
    fields: list[str],
    placeholder_fields: set[str],
) -> None:
    for field in fields:
        if field not in block:
            failures.append(f"{block_name} missing field {field}")
            continue
        if field in placeholder_fields:
            line = line_for(block, field)
            if "{" not in line:
                failures.append(f"{block_name} {field} should remain placeholder-based")
    if "Required files:" in fields and not has_required_file_bullet(block):
        failures.append(f"{block_name} Required files must include a bullet")


def main() -> int:
    failures: list[str] = []

    if not PROFILE.is_file():
        print(f"FAIL: missing {PROFILE.relative_to(ROOT)}")
        return 1

    text = read_profile()
    core_blocks = parse_blocks(text, CORE_HEADING)
    module_blocks = parse_blocks(text, MODULE_HEADING)

    for core_item in CORE_ITEMS:
        block = core_blocks.get(core_item)
        if block is None:
            failures.append(f"missing core item {core_item}")
            continue
        check_block(
            failures,
            f"core item {core_item}",
            block,
            CORE_FIELDS,
            {"State:", "Evidence:", "Validation or review:", "Approval needs:", "Residual risk:"},
        )

    for module in OPTIONAL_MODULES:
        block = module_blocks.get(module)
        if block is None:
            failures.append(f"missing optional module {module}")
            continue
        check_block(
            failures,
            f"module {module}",
            block,
            MODULE_FIELDS,
            {
                "State:",
                "Reason:",
                "Validation or review:",
                "Approval needs:",
                "Residual risk:",
                "Next action:",
            },
        )

    durable = module_blocks.get("durable-approvals", "")
    for required in [
        ".ai/assistant/approvals/approval-template.md",
        ".ai/assistant/approvals/approval-record-template.json",
    ]:
        if required not in durable:
            failures.append(f"module durable-approvals missing required file {required}")

    packages = module_blocks.get("change-packages", "")
    for required in [
        ".ai/framework/change-packages.md",
        ".ai/assistant/change-packages/index.json",
        ".ai/assistant/context/task-scales/change-package.json",
        ".ai/assistant/flows/change-package.flow.md",
        ".ai/assistant/templates/change-package-record.json",
        ".ai/assistant/templates/change-package-report.md",
    ]:
        if required not in packages:
            failures.append(f"module change-packages missing required file {required}")

    ai_infrastructure = module_blocks.get("ai-infrastructure", "")
    for required in [
        ".ai/assistant/ai-infrastructure-router.json",
        ".ai/assistant/flows/ai-infrastructure-inventory.flow.md",
        ".ai/assistant/flows/ai-infrastructure-recommendation.flow.md",
        ".ai/assistant/flows/development-evidence-capture.flow.md",
        ".ai/assistant/flows/skill-adaptation.flow.md",
        ".ai/assistant/templates/ai-infrastructure-recommendation.md",
        ".ai/assistant/templates/ai-infrastructure-adaptation-record.md",
        ".ai/project/development-evidence.json",
    ]:
        if required not in ai_infrastructure:
            failures.append(f"module ai-infrastructure missing required file {required}")

    diagrams = module_blocks.get("diagrams", "")
    for required in [
        ".ai/assistant/flows/diagram-discussion.flow.md",
        ".ai/assistant/templates/diagram-presentation.md",
        ".ai/assistant/templates/ascii-diagram.md",
        ".ai/assistant/assistant-capabilities.json",
        ".ai/assistant/bridge-capability-matrix.md",
    ]:
        if required not in diagrams:
            failures.append(f"module diagrams missing required file {required}")

    architecture = module_blocks.get("architecture-knowledge", "")
    for required in [
        ".ai/project/architecture/README.md",
        ".ai/project/architecture/catalog.json",
        ".ai/assistant/flows/architecture-assistance.flow.md",
        ".ai/assistant/templates/architecture-pattern.md",
        ".ai/assistant/templates/architecture-area.md",
        ".ai/assistant/templates/architecture-discussion-result.md",
    ]:
        if required not in architecture:
            failures.append(
                f"module architecture-knowledge missing required file {required}"
            )

    installed_operations = module_blocks.get("installed-operations", "")
    for required in [
        ".ai/assistant/operation-index.json",
        ".ai/assistant/operation-catalog.json",
    ]:
        if required not in installed_operations:
            failures.append(
                f"module installed-operations missing required file {required}"
            )

    team_collaboration = module_blocks.get("team-collaboration", "")
    for required in [
        ".ai/project/team-operating-model.md",
        ".ai/assistant/team/context-overlay.json",
        ".ai/assistant/team/work-registry.json",
        ".ai/assistant/gates/team-collaboration.md",
    ]:
        if required not in team_collaboration:
            failures.append(f"module team-collaboration missing required file {required}")

    duplicate_core = [
        item
        for item in CORE_HEADING.findall(text)
        if CORE_HEADING.findall(text).count(item) > 1
    ]
    duplicate_modules = [
        module
        for module in MODULE_HEADING.findall(text)
        if MODULE_HEADING.findall(text).count(module) > 1
    ]
    for item in sorted(set(duplicate_core)):
        failures.append(f"duplicate core item {item}")
    for module in sorted(set(duplicate_modules)):
        failures.append(f"duplicate optional module {module}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(
        "OK: checked module profile template with "
        f"{len(CORE_ITEMS)} core items and {len(OPTIONAL_MODULES)} modules"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

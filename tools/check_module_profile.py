#!/usr/bin/env python3
"""Validate target module-profile structure against the capability catalog."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "templates" / "target" / ".ai" / "assistant" / "module-profile.md"
CATALOG = ROOT / "framework" / "capabilities.json"

PROFILE_ITEMS = [
    "contours",
    "manifest-and-versioning",
    "adapter-ownership",
    "context-profiles",
    "source-of-truth-registry",
    "risk-approval-integrity",
    "current-scope-action-authorization",
    "validation-and-final-evidence",
    "durable-engineering-evidence",
    "project-knowledge-delivery",
    "support-information-state",
]
PROFILE_ITEM_FIELDS = [
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
PROFILE_ITEM_HEADING = re.compile(
    r"^(?:Kernel item|Core profile addition): `([^`]+)`\s*$", re.MULTILINE
)
MODULE_HEADING = re.compile(r"^Module: `([^`]+)`\s*$", re.MULTILINE)


def parse_blocks(text: str, pattern: re.Pattern[str]) -> dict[str, str]:
    matches = list(pattern.finditer(text))
    return {
        match.group(1): text[
            match.end() : matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        ]
        for index, match in enumerate(matches)
    }


def line_for(block: str, field: str) -> str:
    return next((line for line in block.splitlines() if line.startswith(field)), "")


def check_block(
    failures: list[str],
    name: str,
    block: str,
    fields: list[str],
    placeholder_fields: set[str],
) -> None:
    for field in fields:
        if field not in block:
            failures.append(f"{name} missing field {field}")
        elif field in placeholder_fields and "{" not in line_for(block, field):
            failures.append(f"{name} {field} should remain placeholder-based")
    if "Required files:" in fields and not re.search(
        r"Required files:\s*\n\s*-\s+`?[^`\n]+`?", block
    ):
        failures.append(f"{name} Required files must include a bullet")


def duplicate_values(values: list[str]) -> set[str]:
    return {value for value in values if values.count(value) > 1}


def main() -> int:
    failures: list[str] = []
    try:
        text = PROFILE.read_text(encoding="utf-8")
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        modules = catalog["modules"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    profile_blocks = parse_blocks(text, PROFILE_ITEM_HEADING)
    module_blocks = parse_blocks(text, MODULE_HEADING)

    for required_text in [
        "## Module State Evidence",
        "Manifest/profile agreement:",
        "Unknown or stale module evidence:",
        "## Shared Capability Surfaces",
        "## Kernel And Core Profiles",
        ".ai/framework/capabilities.json",
        "preserve_on_disable",
        "another enabled producer",
    ]:
        if required_text not in text:
            failures.append(f"module profile missing shared-surface rule: {required_text}")

    for profile_item in PROFILE_ITEMS:
        block = profile_blocks.get(profile_item)
        if block is None:
            failures.append(f"missing profile item {profile_item}")
            continue
        check_block(
            failures,
            f"profile item {profile_item}",
            block,
            PROFILE_ITEM_FIELDS,
            {
                "State:",
                "Evidence:",
                "Validation or review:",
                "Approval needs:",
                "Residual risk:",
            },
        )

    if set(module_blocks) != set(modules):
        failures.append(
            "module profile/catalog mismatch: "
            f"missing={sorted(set(modules) - set(module_blocks))} "
            f"extra={sorted(set(module_blocks) - set(modules))}"
        )
    for module_id, contract in modules.items():
        block = module_blocks.get(module_id)
        if block is None:
            continue
        check_block(
            failures,
            f"module {module_id}",
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
        for required in contract["target_files"]:
            if required not in block:
                failures.append(f"module {module_id} missing required file {required}")

    for item in sorted(duplicate_values(PROFILE_ITEM_HEADING.findall(text))):
        failures.append(f"duplicate profile item {item}")
    for module in sorted(duplicate_values(MODULE_HEADING.findall(text))):
        failures.append(f"duplicate optional module {module}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "OK: checked module profile template with "
        f"{len(PROFILE_ITEMS)} profile items and {len(modules)} catalog modules"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate installed-operation help contracts in target templates.

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
HELP_REFERENCE = TARGET / ".ai" / "assistant" / "help-reference.md"
FLOWS = TARGET / ".ai" / "assistant" / "flows"
INSTALLED_OPERATIONS = ROOT / "framework" / "installed-operations.md"
OPERATION_REQUEST_SURFACES = [
    INSTALLED_OPERATIONS,
    ROOT / "installer" / "installed-operation-request-template.md",
    TARGET / ".ai" / "assistant" / "templates" / "operation-request.md",
    HELP_REFERENCE,
]

OPERATION_RE = re.compile(r"^Operation: `([^`]+)`", re.MULTILINE)
FLOW_RE = re.compile(r"^(?:Flow|Companion flow):\s*`([^`]+)`", re.MULTILINE)
ROUTE_RE = re.compile(r"(?:route to|Route to:)\s+`([^`]+)`")
BACKTICK_RE = re.compile(r"`([^`]+)`")
ORDERED_STEP_RE = re.compile(r"^(\d+)\.\s", re.MULTILINE)

ADAPTER_ONLY_REQUIRED_TEXT = [
    "normalized project-process or adapter-effectiveness evidence",
    "accepted business, domain, architecture, data, runtime, or "
    "product-behavior facts",
]

REQUIRED_OPERATIONS = {
    "help",
    "adapter-health",
    "create-project-blueprint",
    "recheck-after-installation",
    "recheck-after-framework-update",
    "product-change",
    "large-task",
    "logical-integrity-review",
    "ai-infrastructure-inventory",
    "ai-infrastructure-recommendation",
    "skill-adaptation",
    "drift-review",
    "documentation-sync",
    "adapter-maturity-review",
}
REQUIRED_ALIAS_TARGETS = {
    "help",
    "adapter-health",
    "recheck-after-framework-update",
    "recheck-after-installation",
    "adapter-maturity-review",
    "create-project-blueprint",
    "logical-integrity-review",
    "product-change",
    "large-task",
    "ai-infrastructure-inventory",
    "ai-infrastructure-recommendation",
    "skill-adaptation",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def operations(text: str) -> list[str]:
    return OPERATION_RE.findall(text)


def duplicate_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def target_flow_path(flow_ref: str) -> Path | None:
    if not flow_ref.startswith(".ai/"):
        return None
    return TARGET / flow_ref


def flow_references(text: str) -> list[str]:
    return FLOW_RE.findall(text)


def alias_route_targets(text: str, known_operations: set[str]) -> set[str]:
    targets = set(ROUTE_RE.findall(text))

    in_alias_section = False
    for line in text.splitlines():
        if line.startswith("## ") and "Alias" in line:
            in_alias_section = True
            continue
        if line.startswith("AI infrastructure shortcuts:") or line.startswith(
            "Common aliases:"
        ):
            in_alias_section = True
            continue
        if line.startswith("## ") and in_alias_section:
            in_alias_section = False
        if not in_alias_section:
            continue
        for token in BACKTICK_RE.findall(line):
            if token in known_operations:
                targets.add(token)
    return targets


def section(text: str, heading: str) -> str:
    start_marker = f"## {heading}\n"
    start = text.find(start_marker)
    if start == -1:
        return ""
    start += len(start_marker)
    end = text.find("\n## ", start)
    return text[start:] if end == -1 else text[start:end]


def normalized_markdown(text: str) -> str:
    joined_words = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "-", text)
    return " ".join(joined_words.split())


def main() -> int:
    failures: list[str] = []
    help_text = read(HELP)
    reference_text = read(HELP_REFERENCE)

    help_operations = operations(help_text)
    reference_operations = operations(reference_text)
    all_operations = set(reference_operations)

    for label, values in [
        ("help.md", help_operations),
        ("help-reference.md", reference_operations),
    ]:
        duplicates = duplicate_values(values)
        if duplicates:
            failures.append(f"{label} has duplicate operation(s): {duplicates}")

    missing_required = sorted(REQUIRED_OPERATIONS - all_operations)
    if missing_required:
        failures.append(f"help-reference.md missing operation(s): {missing_required}")

    missing_from_reference = sorted(set(help_operations) - all_operations)
    if missing_from_reference:
        failures.append(
            f"help.md operation(s) missing from help-reference.md: "
            f"{missing_from_reference}"
        )

    for source, text in [
        (HELP, help_text),
        (HELP_REFERENCE, reference_text),
    ]:
        for flow_ref in flow_references(text):
            flow_path = target_flow_path(flow_ref)
            if flow_path is None:
                failures.append(
                    f"{source.relative_to(ROOT)} has non-target flow ref: {flow_ref}"
                )
                continue
            if not flow_path.is_file():
                failures.append(
                    f"{source.relative_to(ROOT)} points to missing flow: {flow_ref}"
                )

    referenced_flows = set(flow_references(reference_text))
    for flow_path in sorted(FLOWS.glob("*.flow.md")):
        flow_ref = f".ai/assistant/flows/{flow_path.name}"
        if flow_ref not in referenced_flows:
            failures.append(f"help-reference.md does not reference {flow_ref}")

    for source, text in [
        (HELP, help_text),
        (HELP_REFERENCE, reference_text),
    ]:
        targets = alias_route_targets(text, all_operations)
        unknown_targets = sorted(target for target in targets if target not in all_operations)
        if unknown_targets:
            failures.append(
                f"{source.relative_to(ROOT)} has unknown alias target(s): "
                f"{unknown_targets}"
            )

    reference_alias_targets = alias_route_targets(reference_text, all_operations)
    missing_alias_targets = sorted(REQUIRED_ALIAS_TARGETS - reference_alias_targets)
    if missing_alias_targets:
        failures.append(
            "help-reference.md missing required alias route target(s): "
            f"{missing_alias_targets}"
        )

    installed_operations_text = read(INSTALLED_OPERATIONS)
    required_flow = section(installed_operations_text, "Required Flow")
    step_numbers = [int(value) for value in ORDERED_STEP_RE.findall(required_flow)]
    expected_step_numbers = list(range(1, len(step_numbers) + 1))
    if not step_numbers:
        failures.append("framework/installed-operations.md has no Required Flow steps")
    elif step_numbers != expected_step_numbers:
        failures.append(
            "framework/installed-operations.md Required Flow steps are not "
            f"sequential: {step_numbers}"
        )

    for source in OPERATION_REQUEST_SURFACES:
        text = normalized_markdown(read(source))
        for required_text in ADAPTER_ONLY_REQUIRED_TEXT:
            if required_text not in text:
                failures.append(
                    f"{source.relative_to(ROOT)} adapter-only contract missing: "
                    f"{required_text}"
                )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "OK: checked operation contracts, allowed-action boundaries, and "
        f"sequential routing for {len(reference_operations)} operations and "
        f"{len(referenced_flows)} flows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

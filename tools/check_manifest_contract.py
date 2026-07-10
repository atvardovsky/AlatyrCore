#!/usr/bin/env python3
"""Validate the target adapter manifest template contract.

This validates the AlatyrCore source manifest template only. It is not a
portable framework requirement for target projects.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
MANIFEST = TARGET / ".ai" / "alatyr.yaml"

PathKey = Tuple[str, ...]


@dataclass(frozen=True)
class Frame:
    indent: int
    key: str


@dataclass(frozen=True)
class Scalar:
    value: str
    line: int


REQUIRED_CONTAINERS: set[PathKey] = {
    ("framework",),
    ("installation",),
    ("owner",),
    ("contours",),
    ("source_of_truth",),
    ("modules",),
    ("validation",),
    ("operations",),
    ("maturity",),
    ("bridges",),
    ("approvals",),
    ("policies",),
}

REQUIRED_LISTS: set[PathKey] = {
    ("owner", "review_triggers"),
    ("supported_assistants",),
    ("source_of_truth", "project_sources"),
    ("modules", "enabled"),
    ("modules", "deferred"),
    ("modules", "blocked"),
    ("validation", "commands"),
    ("validation", "commands", "[]", "required_for"),
    ("known_gaps",),
    ("local_deviations",),
}

REQUIRED_SCALARS: set[PathKey] = {
    ("schema_version",),
    ("framework", "name"),
    ("framework", "version"),
    ("framework", "source"),
    ("framework", "template_version"),
    ("framework", "rule_registry"),
    ("installation", "id"),
    ("installation", "date"),
    ("installation", "mode"),
    ("owner", "responsible_team"),
    ("owner", "technical_owner"),
    ("owner", "backup_owner"),
    ("owner", "last_review_date"),
    ("owner", "review_cadence"),
    ("owner", "codeowners"),
    ("contours", "framework"),
    ("contours", "project"),
    ("contours", "assistant"),
    ("source_of_truth", "project_contour"),
    ("source_of_truth", "registry"),
    ("source_of_truth", "assistant_contour"),
    ("source_of_truth", "context_profiles"),
    ("source_of_truth", "module_profile"),
    ("modules", "core_profile"),
    ("validation", "commands", "[]", "name"),
    ("validation", "commands", "[]", "command"),
    ("operations", "help"),
    ("operations", "help_reference"),
    ("operations", "operation_request"),
    ("operations", "installation_note"),
    ("operations", "output_contracts"),
    ("operations", "ai_infrastructure_inventory"),
    ("operations", "migration_note"),
    ("operations", "effectiveness_report"),
    ("maturity", "profile"),
    ("bridges", "capability_matrix"),
    ("approvals", "directory"),
    ("approvals", "template"),
    ("policies", "source_access"),
    ("policies", "prompt_injection"),
}

PLACEHOLDER_SCALARS: set[PathKey] = {
    ("schema_version",),
    ("framework", "version"),
    ("framework", "source"),
    ("framework", "template_version"),
    ("installation", "id"),
    ("installation", "date"),
    ("installation", "mode"),
    ("owner", "responsible_team"),
    ("owner", "technical_owner"),
    ("owner", "backup_owner"),
    ("owner", "last_review_date"),
    ("owner", "review_cadence"),
    ("owner", "codeowners"),
    ("modules", "core_profile"),
    ("validation", "commands", "[]", "name"),
    ("validation", "commands", "[]", "command"),
}

PLACEHOLDER_LISTS: set[PathKey] = {
    ("owner", "review_triggers"),
    ("supported_assistants",),
    ("source_of_truth", "project_sources"),
    ("modules", "enabled"),
    ("modules", "deferred"),
    ("modules", "blocked"),
    ("validation", "commands", "[]", "required_for"),
    ("known_gaps",),
    ("local_deviations",),
}

PATH_SCALARS: set[PathKey] = {
    ("framework", "rule_registry"),
    ("contours", "framework"),
    ("contours", "project"),
    ("contours", "assistant"),
    ("source_of_truth", "project_contour"),
    ("source_of_truth", "registry"),
    ("source_of_truth", "assistant_contour"),
    ("source_of_truth", "context_profiles"),
    ("source_of_truth", "module_profile"),
    ("operations", "help"),
    ("operations", "help_reference"),
    ("operations", "operation_request"),
    ("operations", "installation_note"),
    ("operations", "output_contracts"),
    ("operations", "ai_infrastructure_inventory"),
    ("operations", "migration_note"),
    ("operations", "effectiveness_report"),
    ("maturity", "profile"),
    ("bridges", "capability_matrix"),
    ("approvals", "directory"),
    ("approvals", "template"),
    ("policies", "source_access"),
    ("policies", "prompt_injection"),
}


def strip_quotes(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in "'\"":
        return stripped[1:-1]
    return stripped


def parse_key_value(content: str, line_number: int) -> tuple[str, str]:
    if ":" not in content:
        raise AssertionError(f"line {line_number}: expected key/value syntax")
    key, value = content.split(":", 1)
    key = key.strip()
    if not key:
        raise AssertionError(f"line {line_number}: empty key")
    return key, strip_quotes(value)


def parse_manifest() -> tuple[set[PathKey], dict[PathKey, Scalar], dict[PathKey, list[Scalar]], list[str]]:
    containers: set[PathKey] = set()
    scalars: dict[PathKey, Scalar] = {}
    lists: dict[PathKey, list[Scalar]] = {}
    failures: list[str] = []
    stack: list[Frame] = []

    for line_number, raw_line in enumerate(MANIFEST.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "\t" in raw_line:
            failures.append(f"line {line_number}: tabs are not allowed")
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2:
            failures.append(f"line {line_number}: indentation must use two spaces")
            continue

        content = raw_line[indent:]
        stack = [frame for frame in stack if frame.indent < indent]
        parent = tuple(frame.key for frame in stack)

        try:
            if content.startswith("- "):
                item = content[2:].strip()
                lists.setdefault(parent, [])
                if ":" in item:
                    key, value = parse_key_value(item, line_number)
                    lists[parent].append(Scalar("<mapping>", line_number))
                    stack.append(Frame(indent, "[]"))
                    path = parent + ("[]", key)
                    if value:
                        scalars[path] = Scalar(value, line_number)
                    else:
                        containers.add(path)
                        stack.append(Frame(indent, key))
                else:
                    lists[parent].append(Scalar(strip_quotes(item), line_number))
                continue

            key, value = parse_key_value(content, line_number)
            path = parent + (key,)
            if value:
                scalars[path] = Scalar(value, line_number)
            else:
                containers.add(path)
                stack.append(Frame(indent, key))
        except AssertionError as exc:
            failures.append(str(exc))

    return containers, scalars, lists, failures


def has_placeholder(value: str) -> bool:
    return "{" in value and "}" in value


def target_reference_exists(value: str) -> bool:
    if value == ".ai/framework":
        return (ROOT / "framework").is_dir()
    if value == ".ai/framework/rule-registry.json":
        return (ROOT / "framework" / "rule-registry.json").is_file()
    return (TARGET / value).exists()


def dotted(path: PathKey) -> str:
    return ".".join(path)


def main() -> int:
    failures: list[str] = []

    containers, scalars, lists, parse_failures = parse_manifest()
    failures.extend(parse_failures)

    for path in sorted(REQUIRED_CONTAINERS):
        if path not in containers:
            failures.append(f"missing container: {dotted(path)}")

    for path in sorted(REQUIRED_LISTS):
        if path not in lists:
            failures.append(f"missing list: {dotted(path)}")
        elif not lists[path]:
            failures.append(f"empty list: {dotted(path)}")

    for path in sorted(REQUIRED_SCALARS):
        if path not in scalars:
            failures.append(f"missing scalar: {dotted(path)}")
        elif not scalars[path].value:
            failures.append(f"empty scalar: {dotted(path)}")

    for path in sorted(PLACEHOLDER_SCALARS):
        scalar = scalars.get(path)
        if scalar and not has_placeholder(scalar.value):
            failures.append(
                f"line {scalar.line}: {dotted(path)} must remain placeholder-based"
            )

    for path in sorted(PLACEHOLDER_LISTS):
        for scalar in lists.get(path, []):
            if not has_placeholder(scalar.value):
                failures.append(
                    f"line {scalar.line}: {dotted(path)} item must remain placeholder-based"
                )

    for path in sorted(PATH_SCALARS):
        scalar = scalars.get(path)
        if not scalar:
            continue
        value = scalar.value
        if not value.startswith(".ai/"):
            failures.append(f"line {scalar.line}: {dotted(path)} must be a .ai path")
            continue
        if not target_reference_exists(value):
            failures.append(
                f"line {scalar.line}: {dotted(path)} points to missing template path: "
                f"{value}"
            )

    framework_name = scalars.get(("framework", "name"))
    if framework_name and framework_name.value != "Alatyr Core":
        failures.append("framework.name must be Alatyr Core")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "OK: checked manifest contract with "
        f"{len(scalars)} scalars and {len(lists)} lists"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

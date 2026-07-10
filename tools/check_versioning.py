#!/usr/bin/env python3
"""Validate AlatyrCore source versioning and release-process structure.

This validates the AlatyrCore source repository only. It is not a portable
framework requirement for target projects.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List


ROOT = Path(__file__).resolve().parents[1]
VERSION = ROOT / "VERSION"
ADAPTER_SCHEMA_VERSION = ROOT / "ADAPTER_SCHEMA_VERSION"
TEMPLATE_VERSION = ROOT / "TEMPLATE_VERSION"
CHANGELOG = ROOT / "CHANGELOG.md"
RELEASE_PROCESS = ROOT / "docs" / "release-process.md"

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
    r"(?:\+[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$"
)
VERSION_HEADING_RE = re.compile(
    r"^## (?!Unreleased\b)(?P<version>v?\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)(?: - (?P<date>\d{4}-\d{2}-\d{2}))?$",
    re.MULTILINE,
)


def read_single_line(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) != 1:
        raise AssertionError(f"{path.relative_to(ROOT)} must contain exactly one line")
    value = lines[0].strip()
    if value != lines[0]:
        raise AssertionError(f"{path.relative_to(ROOT)} must not have surrounding whitespace")
    if not value:
        raise AssertionError(f"{path.relative_to(ROOT)} must be non-empty")
    return value


def require_positive_integer(value: str, relpath: str) -> None:
    if not re.fullmatch(r"[1-9]\d*", value):
        raise AssertionError(f"{relpath} must be a positive integer")


def unreleased_body(changelog: str) -> str:
    marker = "## Unreleased"
    if marker not in changelog:
        raise AssertionError("CHANGELOG.md missing ## Unreleased")
    after = changelog.split(marker, 1)[1]
    match = re.search(r"^## ", after, flags=re.MULTILINE)
    return after[: match.start()] if match else after


def validate_changelog(changelog: str) -> List[str]:
    failures: List[str] = []
    if not changelog.startswith("# Changelog\n"):
        failures.append("CHANGELOG.md must start with # Changelog")
    try:
        body = unreleased_body(changelog)
    except AssertionError as exc:
        failures.append(str(exc))
        body = ""
    if body and "- " not in body:
        failures.append("CHANGELOG.md ## Unreleased must contain bullet entries or a release placeholder")

    for match in VERSION_HEADING_RE.finditer(changelog):
        version = match.group("version")
        normalized = version[1:] if version.startswith("v") else version
        if not SEMVER_RE.fullmatch(normalized):
            failures.append(f"CHANGELOG.md version heading is not SemVer-like: {version}")
    return failures


def validate_release_process(text: str) -> List[str]:
    failures: List[str] = []
    required_text = [
        "not an installed target adapter requirement",
        "VERSION",
        "ADAPTER_SCHEMA_VERSION",
        "TEMPLATE_VERSION",
        "CHANGELOG.md",
        "docs/release-migration-report-template.md",
        "framework/rule-registry.json",
        "framework/rule-ownership.md",
        "tools/report_migration_diff.py",
        "tools/check_release_migration_template.py",
        "tools/check_versioning.py",
        "docs/framework-maintenance.md",
        "v<VERSION>",
        "recheck-after-framework-update",
    ]
    for item in required_text:
        if item not in text:
            failures.append(f"docs/release-process.md missing {item}")
    return failures


def main() -> int:
    failures: List[str] = []
    try:
        version = read_single_line(VERSION)
        adapter_schema_version = read_single_line(ADAPTER_SCHEMA_VERSION)
        template_version = read_single_line(TEMPLATE_VERSION)
        changelog = CHANGELOG.read_text(encoding="utf-8")
        release_process = RELEASE_PROCESS.read_text(encoding="utf-8")
    except (OSError, AssertionError) as exc:
        failures.append(str(exc))
    else:
        if not SEMVER_RE.fullmatch(version):
            failures.append("VERSION must be SemVer-like")
        try:
            require_positive_integer(adapter_schema_version, "ADAPTER_SCHEMA_VERSION")
        except AssertionError as exc:
            failures.append(str(exc))
        try:
            require_positive_integer(template_version, "TEMPLATE_VERSION")
        except AssertionError as exc:
            failures.append(str(exc))
        failures.extend(validate_changelog(changelog))
        failures.extend(validate_release_process(release_process))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "OK: checked source versioning "
        f"VERSION={version} ADAPTER_SCHEMA_VERSION={adapter_schema_version} "
        f"TEMPLATE_VERSION={template_version}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

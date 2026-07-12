#!/usr/bin/env python3
"""Validate the target context router template.

This validates AlatyrCore source templates only. It is not a portable
framework requirement for target projects.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
ROUTER = TARGET / ".ai" / "assistant" / "context-router.json"
PROFILES_MD = TARGET / ".ai" / "assistant" / "context-profiles.md"

CANONICAL_PROFILES = [
    "docs-local",
    "code-local",
    "business-change",
    "architecture-change",
    "data-change",
    "security-sensitive",
    "ai-infrastructure",
    "framework-upgrade",
]

REQUIRED_BOOTSTRAP = [
    "AGENTS.md",
    ".ai/alatyr.yaml",
    ".ai/README.md",
    ".ai/assistant/context-router.json",
    ".ai/assistant/context-profiles.md",
    ".ai/assistant/module-profile.md",
    ".ai/project/contour.md",
    ".ai/project/source-of-truth-registry.md",
    ".ai/assistant/contour.md",
]

PROFILE_FIELDS = [
    "use_when",
    "required_context",
    "expand_when",
    "approval_gates",
    "validation",
    "final_evidence",
]


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AssertionError(f"missing {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(data, dict):
        raise AssertionError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return data


def markdown_profiles() -> set[str]:
    text = PROFILES_MD.read_text(encoding="utf-8")
    return set(re.findall(r"^## Profile: `([^`]+)`", text, flags=re.MULTILINE))


def require_string_list(
    data: dict[str, Any],
    key: str,
    label: str,
    failures: list[str],
) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        failures.append(f"{label} must contain non-empty list {key}")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            failures.append(f"{label}.{key}[{index}] must be a non-empty string")
            continue
        result.append(item)
    return result


def duplicate_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def target_reference_exists(value: str) -> bool:
    if value.startswith("{"):
        return True
    if value == ".ai/framework":
        return (ROOT / "framework").is_dir()
    if value.startswith(".ai/framework/"):
        suffix = value[len(".ai/framework/") :]
        return (ROOT / "framework" / suffix).is_file()
    if value.startswith(".ai/"):
        return (TARGET / value).exists()
    if value == "AGENTS.md":
        return (TARGET / "AGENTS.md").is_file()
    if value == "AI_ASSISTANTS.md":
        return (TARGET / "AI_ASSISTANTS.md").is_file()
    return True


def main() -> int:
    failures: list[str] = []
    try:
        router = load_json(ROUTER)
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if router.get("schema_version") != 1:
        failures.append("context-router.json schema_version must be 1")
    if router.get("router_kind") != "target-context-router":
        failures.append("context-router.json router_kind must be target-context-router")
    if router.get("human_reference") != ".ai/assistant/context-profiles.md":
        failures.append(
            "context-router.json human_reference must be .ai/assistant/context-profiles.md"
        )

    bootstrap = require_string_list(router, "bootstrap_context", "router", failures)
    duplicate_bootstrap = duplicate_values(bootstrap)
    if duplicate_bootstrap:
        failures.append(
            f"bootstrap_context has duplicate path(s): {duplicate_bootstrap}"
        )
    for required in REQUIRED_BOOTSTRAP:
        if required not in bootstrap:
            failures.append(f"bootstrap_context missing {required}")

    routing_order = require_string_list(router, "routing_order", "router", failures)
    if routing_order != CANONICAL_PROFILES:
        failures.append("routing_order must match canonical profile order")

    profiles = router.get("profiles")
    if not isinstance(profiles, dict):
        failures.append("profiles must be an object")
        profiles = {}

    markdown_profile_names = markdown_profiles()
    for profile in CANONICAL_PROFILES:
        if profile not in markdown_profile_names:
            failures.append(f"context-profiles.md missing profile {profile}")
        profile_data = profiles.get(profile)
        if not isinstance(profile_data, dict):
            failures.append(f"profiles.{profile} must be an object")
            continue
        for field in PROFILE_FIELDS:
            values = require_string_list(profile_data, field, f"profiles.{profile}", failures)
            duplicate_profile_values = duplicate_values(values)
            if duplicate_profile_values:
                failures.append(
                    f"profiles.{profile}.{field} has duplicate value(s): "
                    f"{duplicate_profile_values}"
                )
            if field in {"required_context", "validation"}:
                for value in values:
                    if not target_reference_exists(value):
                        failures.append(
                            f"profiles.{profile}.{field} points to missing path: {value}"
                        )

    extra_profiles = sorted(set(profiles) - set(CANONICAL_PROFILES))
    if extra_profiles:
        failures.append(f"context-router.json has unexpected profile(s): {extra_profiles}")

    framework_paths = {
        f".ai/framework/{path.name}"
        for path in (ROOT / "framework").glob("*.md")
        if path.is_file()
    }
    routed_framework_paths = {
        value
        for profile_data in profiles.values()
        if isinstance(profile_data, dict)
        for value in profile_data.get("required_context", [])
        if isinstance(value, str) and value.startswith(".ai/framework/")
    }
    missing_framework_paths = sorted(framework_paths - routed_framework_paths)
    if missing_framework_paths:
        failures.append(
            "context-router.json does not route framework file(s): "
            f"{missing_framework_paths}"
        )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "OK: checked context router template with "
        f"{len(CANONICAL_PROFILES)} profiles"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

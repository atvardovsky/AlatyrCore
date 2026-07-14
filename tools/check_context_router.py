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

REQUIRED_PRELOADED = [
    "AGENTS.md",
]

REQUIRED_BOOTSTRAP = [
    ".ai/alatyr.yaml",
    ".ai/README.md",
    ".ai/assistant/context-router.json",
]

FORBIDDEN_BOOTSTRAP = {
    "AGENTS.md",
    ".ai/assistant/context-profiles.md",
    ".ai/assistant/module-profile.md",
    ".ai/project/contour.md",
    ".ai/project/source-of-truth-registry.md",
    ".ai/assistant/contour.md",
}

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

    if router.get("schema_version") != 2:
        failures.append("context-router.json schema_version must be 2")
    if router.get("router_kind") != "target-context-router":
        failures.append("context-router.json router_kind must be target-context-router")
    if router.get("human_reference") != ".ai/assistant/context-profiles.md":
        failures.append(
            "context-router.json human_reference must be .ai/assistant/context-profiles.md"
        )

    preloaded = require_string_list(router, "preloaded_context", "router", failures)
    for required in REQUIRED_PRELOADED:
        if required not in preloaded:
            failures.append(f"preloaded_context missing {required}")

    bootstrap = require_string_list(router, "bootstrap_context", "router", failures)
    duplicate_bootstrap = duplicate_values(bootstrap)
    if duplicate_bootstrap:
        failures.append(
            f"bootstrap_context has duplicate path(s): {duplicate_bootstrap}"
        )
    for required in REQUIRED_BOOTSTRAP:
        if required not in bootstrap:
            failures.append(f"bootstrap_context missing {required}")
    forbidden = sorted(set(bootstrap) & FORBIDDEN_BOOTSTRAP)
    if forbidden:
        failures.append(f"bootstrap_context contains deferred context: {forbidden}")
    if len(bootstrap) > 4:
        failures.append("bootstrap_context must contain at most 4 files")

    budgets = router.get("context_budgets")
    if not isinstance(budgets, dict):
        failures.append("context_budgets must be an object")
    else:
        for name in ["bootstrap", "profile_default"]:
            budget = budgets.get(name)
            if not isinstance(budget, dict):
                failures.append(f"context_budgets.{name} must be an object")
                continue
            for field in ["max_files", "max_words"]:
                value = budget.get(field)
                if not isinstance(value, int) or value <= 0:
                    failures.append(
                        f"context_budgets.{name}.{field} must be a positive integer"
                    )
        if not isinstance(budgets.get("on_exceed"), str) or not budgets.get("on_exceed"):
            failures.append("context_budgets.on_exceed must be a non-empty string")

    receipt = router.get("context_receipt")
    if not isinstance(receipt, dict):
        failures.append("context_receipt must be an object")
    else:
        require_string_list(receipt, "required_for", "context_receipt", failures)
        receipt_fields = require_string_list(receipt, "fields", "context_receipt", failures)
        for required in [
            "selected profiles",
            "selected task scale overlay",
            "selected project areas",
            "loaded files and reasons",
            "approximate context volume",
            "expansion triggers",
            "residual risk",
        ]:
            if required not in receipt_fields:
                failures.append(f"context_receipt.fields missing {required}")

    scale_overlays = router.get("task_scale_overlays")
    if not isinstance(scale_overlays, dict):
        failures.append("task_scale_overlays must be an object")
    else:
        large_task = scale_overlays.get("large-or-resumable")
        if not isinstance(large_task, dict):
            failures.append(
                "task_scale_overlays.large-or-resumable must be an object"
            )
        else:
            for field in ["use_when", "required_context", "expand_when", "final_evidence"]:
                values = require_string_list(
                    large_task,
                    field,
                    "task_scale_overlays.large-or-resumable",
                    failures,
                )
                if field == "required_context":
                    for value in values:
                        if not target_reference_exists(value):
                            failures.append(
                                "task_scale_overlays.large-or-resumable."
                                f"required_context points to missing path: {value}"
                            )
            budget_behavior = large_task.get("budget_behavior")
            if not isinstance(budget_behavior, str) or not budget_behavior:
                failures.append(
                    "task_scale_overlays.large-or-resumable.budget_behavior "
                    "must be a non-empty string"
                )

    overlays = router.get("area_overlays")
    if not isinstance(overlays, dict) or not overlays:
        failures.append("area_overlays must be a non-empty object")
    else:
        for area, data in overlays.items():
            if not isinstance(data, dict):
                failures.append(f"area_overlays.{area} must be an object")
                continue
            for field in ["use_when", "required_context", "expand_when"]:
                require_string_list(data, field, f"area_overlays.{area}", failures)

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
    if isinstance(scale_overlays, dict):
        for overlay in scale_overlays.values():
            if not isinstance(overlay, dict):
                continue
            routed_framework_paths.update(
                value
                for value in overlay.get("required_context", [])
                if isinstance(value, str) and value.startswith(".ai/framework/")
            )
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

#!/usr/bin/env python3
"""Validate the source-owned installation discovery contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from installer_stage_model import load_installer_stage_plan


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "installer" / "discovery-contract.json"
ROUTER = ROOT / "installer" / "context-router.json"
CAPABILITIES = ROOT / "framework" / "capabilities.json"
PROSE_SURFACES = [
    ROOT / "INSTALL.md",
    ROOT / "installer" / "assistant-installation.flow.md",
    ROOT / "installer" / "readiness-checklist.md",
    ROOT / "installer" / "installation-plan-template.md",
]


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return data


def main() -> int:
    failures: list[str] = []
    try:
        contract = load(CONTRACT)
        capabilities = load(CAPABILITIES)
        router = load(ROUTER)
        stage_plan = load_installer_stage_plan(ROUTER)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if contract.get("schema_version") != 1:
        failures.append("discovery contract schema_version must be 1")
    if contract.get("contract_kind") != "alatyr-installation-discovery-contract":
        failures.append("discovery contract kind is invalid")

    stages = router.get("stages")
    if not isinstance(stages, dict):
        failures.append("installer context router must define stages")
        stages = {}
    discovery = stages.get("discovery")
    scope_selection = stages.get("scope-selection")
    for stage_id, stage in [
        ("discovery", discovery),
        ("scope-selection", scope_selection),
    ]:
        if not isinstance(stage, dict):
            failures.append(f"installer context router misses {stage_id} stage")
            continue
        if "installer/discovery-contract.json" not in stage.get("required_context", []):
            failures.append(
                f"installer {stage_id} stage must require installer/discovery-contract.json"
            )
        evidence = stage.get("required_evidence")
        if not isinstance(evidence, list) or not evidence or not all(
            isinstance(item, str) and item for item in evidence
        ):
            failures.append(f"installer {stage_id} stage must require evidence")
    if isinstance(scope_selection, dict) and "discovery" not in scope_selection.get(
        "depends_on", []
    ):
        failures.append("installer scope-selection stage must depend on discovery")
    if [stage.stage_id for stage in stage_plan.stages] != router.get("routing_order"):
        failures.append("installer stage read model differs from routing_order")

    profile_selection = contract.get("profile_selection")
    expected_profiles = ["kernel", "core", "standard", "full"]
    if not isinstance(profile_selection, dict):
        failures.append("discovery contract must define profile_selection")
    else:
        if profile_selection.get("default_profile") != "kernel":
            failures.append("profile_selection.default_profile must be kernel")
        expansion_rule = profile_selection.get("expansion_rule")
        if not isinstance(expansion_rule, str) or "optional modules" not in expansion_rule:
            failures.append("profile_selection.expansion_rule must cover optional modules")
        profiles = profile_selection.get("profiles")
        if not isinstance(profiles, list):
            failures.append("profile_selection.profiles must be a list")
        else:
            observed_profiles: list[str] = []
            for index, profile in enumerate(profiles):
                if not isinstance(profile, dict):
                    failures.append(f"profile_selection.profiles[{index}] must be an object")
                    continue
                profile_id = profile.get("id")
                observed_profiles.append(profile_id if isinstance(profile_id, str) else "")
                if not isinstance(profile.get("tier"), str) or not profile["tier"]:
                    failures.append(f"profile_selection.profiles[{index}].tier is invalid")
                use_when = profile.get("use_when")
                if not isinstance(use_when, str) or len(use_when.split()) < 8:
                    failures.append(
                        f"profile_selection.profiles[{index}].use_when is too thin"
                    )
            if observed_profiles != expected_profiles:
                failures.append(
                    "profile_selection.profiles must be kernel, core, standard, full"
                )

    categories = contract.get("base_categories")
    if not isinstance(categories, list) or not categories:
        failures.append("discovery contract must define base_categories")
        category_ids: set[str] = set()
    else:
        category_ids = set()
        for index, category in enumerate(categories):
            if not isinstance(category, dict):
                failures.append(f"base_categories[{index}] must be an object")
                continue
            category_id = category.get("id")
            summary = category.get("summary")
            if not isinstance(category_id, str) or not category_id:
                failures.append(f"base_categories[{index}].id is invalid")
            elif category_id in category_ids:
                failures.append(f"duplicate discovery category: {category_id}")
            else:
                category_ids.add(category_id)
            if not isinstance(summary, str) or len(summary.split()) < 5:
                failures.append(f"base_categories[{index}].summary is too thin")

    module_categories = contract.get("module_categories")
    if not isinstance(module_categories, dict):
        failures.append("discovery contract must define module_categories")
        module_categories = {}

    modules = capabilities.get("modules")
    if not isinstance(modules, dict):
        failures.append("capability catalog must define modules")
        modules = {}

    missing_modules = sorted(set(modules) - set(module_categories))
    extra_modules = sorted(set(module_categories) - set(modules))
    if missing_modules:
        failures.append(f"discovery contract misses modules: {missing_modules}")
    if extra_modules:
        failures.append(f"discovery contract has unknown modules: {extra_modules}")

    for module_id, values in module_categories.items():
        if not isinstance(values, list) or not values:
            failures.append(f"module {module_id} discovery categories must be a non-empty list")
            continue
        unknown = sorted(set(values) - category_ids)
        if unknown:
            failures.append(f"module {module_id} uses unknown discovery categories: {unknown}")

    declared_surfaces = contract.get("prose_surfaces")
    expected_surfaces = [path.relative_to(ROOT).as_posix() for path in PROSE_SURFACES]
    if declared_surfaces != expected_surfaces:
        failures.append(
            "discovery contract prose_surfaces must match installer prose surfaces"
        )

    for path in PROSE_SURFACES:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            failures.append(f"cannot read {path.relative_to(ROOT)}: {exc}")
            continue
        if "installer/discovery-contract.json" not in text:
            failures.append(
                f"{path.relative_to(ROOT)} must reference installer/discovery-contract.json"
            )
        if "`kernel`" not in text:
            failures.append(
                f"{path.relative_to(ROOT)} must mention the kernel support profile"
            )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "OK: installer discovery contract covers "
        f"{len(modules)} modules and {len(category_ids)} base categories"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

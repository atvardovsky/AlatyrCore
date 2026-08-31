#!/usr/bin/env python3
"""Validate the source-owned installation discovery contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "installer" / "discovery-contract.json"
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
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if contract.get("schema_version") != 1:
        failures.append("discovery contract schema_version must be 1")
    if contract.get("contract_kind") != "alatyr-installation-discovery-contract":
        failures.append("discovery contract kind is invalid")

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

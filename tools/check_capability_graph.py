#!/usr/bin/env python3
"""Validate optional-module dependency, pack, file, rule, and check closure."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import jsonschema

from check_all import load_manifest
from capability_catalog import dependency_closure
from framework_packaging import resolve_framework_files


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "framework" / "capabilities.json"
SCHEMA = ROOT / "schemas" / "alatyr-capabilities.schema.json"
TARGET = ROOT / "templates" / "target"
PACK_ORDER = {"core": 0, "standard": 1, "complete": 2}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return value


def main() -> int:
    failures: list[str] = []
    modules: dict[str, Any] = {}
    surfaces: dict[str, Any] = {}
    try:
        catalog = load_object(CATALOG)
        schema = load_object(SCHEMA)
        schema_errors = sorted(
            jsonschema.Draft7Validator(schema).iter_errors(catalog),
            key=lambda error: list(error.absolute_path),
        )
        failures.extend(
            "schema "
            + (".".join(str(item) for item in error.absolute_path) or "root")
            + f": {error.message}"
            for error in schema_errors
        )
        raw_modules = catalog.get("modules", {})
        if not isinstance(raw_modules, dict):
            raise ValueError("capability catalog modules must be an object")
        modules = raw_modules
        raw_surfaces = catalog.get("surfaces", {})
        if not isinstance(raw_surfaces, dict):
            raise ValueError("capability catalog surfaces must be an object")
        surfaces = raw_surfaces

        registry = load_object(ROOT / "framework" / "rule-registry.json")
        rule_ids = {
            rule.get("id") for rule in registry.get("rules", []) if isinstance(rule, dict)
        }
        check_ids = {check["id"] for check in load_manifest()}
        known_modules = set(modules)

        for module_id, module in modules.items():
            if not isinstance(module, dict):
                continue
            unknown_dependencies = sorted(set(module.get("requires", [])) - known_modules)
            if unknown_dependencies:
                failures.append(
                    f"{module_id} has unknown dependencies {unknown_dependencies}"
                )
            unknown_rules = sorted(set(module.get("rule_ids", [])) - rule_ids)
            if unknown_rules:
                failures.append(f"{module_id} has unknown rule IDs {unknown_rules}")
            unknown_checks = sorted(set(module.get("check_ids", [])) - check_ids)
            if unknown_checks:
                failures.append(f"{module_id} has unknown check IDs {unknown_checks}")

            pack = module.get("min_framework_pack")
            if pack not in PACK_ORDER:
                continue
            selected = resolve_framework_files(pack)
            for filename in module.get("framework_files", []):
                if not (ROOT / "framework" / filename).is_file():
                    failures.append(f"{module_id} references missing framework file {filename}")
                elif filename not in selected:
                    failures.append(
                        f"{module_id} file {filename} is absent from minimum pack {pack}"
                    )
            for relpath in module.get("target_files", []):
                if not (TARGET / relpath).is_file():
                    failures.append(f"{module_id} references missing target file {relpath}")

        producers_by_path: dict[str, set[str]] = {}
        for module_id, module in modules.items():
            if not isinstance(module, dict):
                continue
            for relpath in module.get("target_files", []):
                if isinstance(relpath, str):
                    producers_by_path.setdefault(relpath, set()).add(module_id)

        shared_paths = {
            relpath: producers
            for relpath, producers in producers_by_path.items()
            if len(producers) > 1
        }
        if set(surfaces) != set(shared_paths):
            failures.append(
                "shared surface catalog mismatch: "
                f"missing={sorted(set(shared_paths) - set(surfaces))} "
                f"extra={sorted(set(surfaces) - set(shared_paths))}"
            )
        for relpath, contract in surfaces.items():
            if not isinstance(contract, dict):
                continue
            declared_producers = set(contract.get("producers", []))
            actual_producers = shared_paths.get(relpath, set())
            if declared_producers != actual_producers:
                failures.append(
                    f"shared surface {relpath} producers mismatch: "
                    f"declared={sorted(declared_producers)} "
                    f"actual={sorted(actual_producers)}"
                )
            if contract.get("ownership") != "target-adapter-shared":
                failures.append(f"shared surface {relpath} has invalid ownership")
            if not isinstance(contract.get("preserve_on_disable"), bool):
                failures.append(
                    f"shared surface {relpath} lacks preserve_on_disable policy"
                )
            if not isinstance(contract.get("merge_strategy"), str):
                failures.append(f"shared surface {relpath} lacks merge strategy")

        if not failures:
            for module_id in modules:
                closure = dependency_closure([module_id], modules)
                module_pack = modules[module_id]["min_framework_pack"]
                for dependency in closure - {module_id}:
                    dependency_pack = modules[dependency]["min_framework_pack"]
                    if PACK_ORDER[dependency_pack] > PACK_ORDER[module_pack]:
                        failures.append(
                            f"{module_id} minimum pack {module_pack} cannot satisfy "
                            f"dependency {dependency} pack {dependency_pack}"
                        )
    except (OSError, ValueError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        f"OK: checked closure for {len(modules)} optional capabilities and "
        f"{len(surfaces)} shared surfaces"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

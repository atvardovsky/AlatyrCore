"""Resolve optional Alatyr capability dependencies and scaffold surfaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "framework" / "capabilities.json"
PACK_ORDER = {"core": 0, "standard": 1, "complete": 2}


def load_modules(path: Path = CATALOG_PATH) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    modules = data.get("modules") if isinstance(data, dict) else None
    if data.get("schema_version") != 1 or not isinstance(modules, dict):
        raise ValueError("invalid capability catalog")
    if not all(isinstance(key, str) and isinstance(value, dict) for key, value in modules.items()):
        raise ValueError("capability catalog modules must be objects")
    return modules


def dependency_closure(
    selected: Iterable[str], modules: dict[str, dict[str, Any]] | None = None
) -> set[str]:
    catalog = modules if modules is not None else load_modules()
    closure: set[str] = set()
    visiting: set[str] = set()

    def visit(module_id: str) -> None:
        if module_id not in catalog:
            raise ValueError(f"unknown capability: {module_id}")
        if module_id in visiting:
            raise ValueError(f"capability dependency cycle includes {module_id}")
        if module_id in closure:
            return
        visiting.add(module_id)
        requires = catalog[module_id].get("requires", [])
        if not isinstance(requires, list) or not all(isinstance(item, str) for item in requires):
            raise ValueError(f"capability {module_id} has invalid dependencies")
        for dependency in requires:
            visit(dependency)
        visiting.remove(module_id)
        closure.add(module_id)

    for module_id in selected:
        visit(module_id)
    return closure


def target_files(selected: Iterable[str]) -> set[Path]:
    modules = load_modules()
    paths: set[Path] = set()
    for module_id in dependency_closure(selected, modules):
        values = modules[module_id].get("target_files", [])
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            raise ValueError(f"capability {module_id} has invalid target_files")
        paths.update(Path(value) for value in values)
    return paths


def minimum_pack(selected: Iterable[str]) -> str:
    modules = load_modules()
    required = "core"
    for module_id in dependency_closure(selected, modules):
        pack = modules[module_id].get("min_framework_pack")
        if pack not in PACK_ORDER:
            raise ValueError(f"capability {module_id} has invalid minimum pack")
        if PACK_ORDER[pack] > PACK_ORDER[required]:
            required = pack
    return required

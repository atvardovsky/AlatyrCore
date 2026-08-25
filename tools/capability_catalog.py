"""Resolve optional Alatyr capability dependencies and scaffold surfaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "framework" / "capabilities.json"
PACK_ORDER = {"core": 0, "standard": 1, "complete": 2}


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("invalid capability catalog")
    return data


def load_modules(path: Path = CATALOG_PATH) -> dict[str, dict[str, Any]]:
    modules = load_catalog(path).get("modules")
    if not isinstance(modules, dict):
        raise ValueError("invalid capability catalog")
    if not all(isinstance(key, str) and isinstance(value, dict) for key, value in modules.items()):
        raise ValueError("capability catalog modules must be objects")
    return modules


def load_surfaces(path: Path = CATALOG_PATH) -> dict[str, dict[str, Any]]:
    surfaces = load_catalog(path).get("surfaces")
    if not isinstance(surfaces, dict):
        raise ValueError("capability catalog surfaces must be an object")
    if not all(isinstance(key, str) and isinstance(value, dict) for key, value in surfaces.items()):
        raise ValueError("capability catalog surfaces must be objects")
    return surfaces


def shared_surface_contract(
    path: Path | str,
    surfaces: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Return lifecycle metadata for one catalog-managed shared target path."""

    lifecycle = surfaces if surfaces is not None else load_surfaces()
    contract = lifecycle.get(Path(path).as_posix())
    return contract if isinstance(contract, dict) else None


def shared_surface_merge_requirement(
    path: Path | str,
    surfaces: dict[str, dict[str, Any]] | None = None,
) -> str | None:
    """Return the adapter-aware merge strategy required for an existing path."""

    contract = shared_surface_contract(path, surfaces)
    if contract is None:
        return None
    strategy = contract.get("merge_strategy")
    if not isinstance(strategy, str) or not strategy:
        raise ValueError(f"shared surface {Path(path).as_posix()} has no merge strategy")
    return strategy


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


def target_files(
    selected: Iterable[str], modules: dict[str, dict[str, Any]] | None = None
) -> set[Path]:
    catalog = modules if modules is not None else load_modules()
    paths: set[Path] = set()
    for module_id in dependency_closure(selected, catalog):
        values = catalog[module_id].get("target_files", [])
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            raise ValueError(f"capability {module_id} has invalid target_files")
        paths.update(Path(value) for value in values)
    return paths


def removable_target_files(
    previously_enabled: Iterable[str],
    next_enabled: Iterable[str],
    modules: dict[str, dict[str, Any]] | None = None,
    surfaces: dict[str, dict[str, Any]] | None = None,
) -> set[Path]:
    """Return files eligible for pruning after a capability-state change.

    Shared target-owned surfaces are retained when another producer remains
    enabled. A surface marked ``preserve_on_disable`` also survives removal of
    its final producer so target-authored merged content is not destroyed by a
    module toggle.
    """

    catalog = modules if modules is not None else load_modules()
    lifecycle = surfaces if surfaces is not None else load_surfaces()
    previous_closure = dependency_closure(previously_enabled, catalog)
    next_closure = dependency_closure(next_enabled, catalog)
    candidates = target_files(previous_closure, catalog) - target_files(
        next_closure, catalog
    )
    removable: set[Path] = set()
    for path in candidates:
        contract = lifecycle.get(path.as_posix())
        if contract is None:
            removable.add(path)
            continue
        producers = set(contract.get("producers", []))
        if producers & next_closure:
            continue
        if contract.get("preserve_on_disable") is True:
            continue
        removable.add(path)
    return removable


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

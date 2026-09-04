#!/usr/bin/env python3
"""Run focused unit tests for AlatyrCore source tooling."""

from __future__ import annotations

import json
import os
import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = ROOT / "tests"


CRITICAL_UNIT_SELECTION_PATHS = {
    "tools/check_source_unit_tests.py",
    "tools/check_all.py",
    "tools/source_state.py",
}


def _environment_changed_paths() -> list[str]:
    raw = os.environ.get("ALATYR_CHANGED_PATHS_JSON", "[]")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [
        item.replace("\\", "/")
        for item in data
        if isinstance(item, str) and item and not Path(item).is_absolute()
    ]


def _test_module_name(path: Path, *, root: Path = ROOT) -> str:
    relpath = path.relative_to(root).with_suffix("")
    return ".".join(relpath.parts)


def _module_name(path: Path, *, root: Path) -> str:
    relpath = path.relative_to(root / "tools")
    parts = relpath.with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _local_module_paths(root: Path) -> dict[str, Path]:
    modules: dict[str, Path] = {}
    for path in sorted((root / "tools").rglob("*.py")):
        modules[_module_name(path, root=root)] = path
    return modules


def _local_imports(path: Path, modules: dict[str, Path]) -> set[Path] | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError):
        return None
    imported: set[Path] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
            names.extend(f"{node.module}.{alias.name}" for alias in node.names)
        for name in names:
            candidate = modules.get(name)
            if candidate is not None:
                imported.add(candidate)
    return imported


def _all_test_paths(root: Path = ROOT) -> list[Path]:
    return sorted((root / "tests").glob("test_*.py"))


def focused_test_paths(changed_paths: list[str], *, root: Path = ROOT) -> list[Path] | None:
    """Return selected test files, `[]` to skip, or `None` for full fallback."""

    selected: set[Path] = set()
    requires_full = False
    changed_tools: set[Path] = set()

    for relpath in changed_paths:
        path = Path(relpath)
        if relpath in CRITICAL_UNIT_SELECTION_PATHS:
            requires_full = True
            continue
        if relpath.startswith("tests/"):
            if path.name.startswith("test_") and path.suffix == ".py":
                test_path = root / path
                if test_path.is_file():
                    selected.add(test_path)
                else:
                    requires_full = True
            else:
                requires_full = True
            continue
        if relpath.startswith("tools/") and path.suffix == ".py":
            tool_path = root / path
            if not tool_path.is_file():
                requires_full = True
                continue
            changed_tools.add(tool_path)
            direct_name = path.with_suffix("").name
            direct_test = root / "tests" / f"test_{direct_name}.py"
            if direct_test.is_file():
                selected.add(direct_test)
            continue
        if relpath.endswith(".py"):
            requires_full = True

    if changed_tools:
        modules = _local_module_paths(root)
        dependency_graph: dict[Path, set[Path]] = {}
        for tool_path in modules.values():
            imports = _local_imports(tool_path, modules)
            if imports is None:
                requires_full = True
                continue
            dependency_graph[tool_path] = imports
        impacted = set(changed_tools)
        changed = True
        while changed:
            changed = False
            for importer, dependencies in dependency_graph.items():
                if importer not in impacted and dependencies & impacted:
                    impacted.add(importer)
                    changed = True
        for test_path in _all_test_paths(root):
            imports = _local_imports(test_path, modules)
            if imports is None:
                requires_full = True
            elif imports & impacted:
                selected.add(test_path)
        if not selected:
            requires_full = True

    if requires_full:
        return None
    return sorted(selected)


def load_suite(paths: list[Path] | None, *, root: Path = ROOT) -> unittest.TestSuite:
    loader = unittest.defaultTestLoader
    if paths is None:
        return loader.discover(str(root / "tests"), pattern="test_*.py")
    suite = unittest.TestSuite()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    for path in paths:
        suite.addTests(loader.loadTestsFromName(_test_module_name(path, root=root)))
    return suite


def main() -> int:
    profile = os.environ.get("ALATYR_SOURCE_CHECK_PROFILE")
    changed_paths = _environment_changed_paths()
    selected_paths = (
        focused_test_paths(changed_paths)
        if profile in {"micro", "fast"} and changed_paths
        else None
    )
    if selected_paths == []:
        print("OK: no focused source unit tests required for changed paths")
        return 0
    suite = load_suite(selected_paths)
    if selected_paths is not None:
        relpaths = ", ".join(path.relative_to(ROOT).as_posix() for path in selected_paths)
        print(f"INFO: running focused source unit tests: {relpaths}")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

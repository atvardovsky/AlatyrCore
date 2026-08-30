#!/usr/bin/env python3
"""Run focused unit tests for AlatyrCore source tooling."""

from __future__ import annotations

import json
import os
import re
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


def _tool_import_names(relpath: str) -> set[str]:
    if not relpath.startswith("tools/") or not relpath.endswith(".py"):
        return set()
    parts = Path(relpath).with_suffix("").parts
    if len(parts) == 2:
        return {parts[1]}
    if len(parts) >= 3:
        return {parts[1], ".".join(parts[1:])}
    return set()


def _test_imports_any(path: Path, import_names: set[str]) -> bool:
    if not import_names:
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    for name in import_names:
        root_name = name.split(".", 1)[0]
        patterns = [
            rf"^\s*import\s+{re.escape(name)}(?:\s|$|,)",
            rf"^\s*from\s+{re.escape(name)}\s+import\s+",
            rf"^\s*from\s+{re.escape(root_name)}\s+import\s+",
        ]
        if any(re.search(pattern, text, flags=re.MULTILINE) for pattern in patterns):
            return True
    return False


def _all_test_paths(root: Path = ROOT) -> list[Path]:
    return sorted((root / "tests").glob("test_*.py"))


def focused_test_paths(changed_paths: list[str], *, root: Path = ROOT) -> list[Path] | None:
    """Return selected test files, `[]` to skip, or `None` for full fallback."""

    selected: set[Path] = set()
    requires_full = False
    tool_imports: set[str] = set()

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
            imports = _tool_import_names(relpath)
            tool_imports.update(imports)
            direct_name = path.with_suffix("").name
            direct_test = root / "tests" / f"test_{direct_name}.py"
            if direct_test.is_file():
                selected.add(direct_test)
            continue
        if relpath.endswith(".py"):
            requires_full = True

    if tool_imports:
        for test_path in _all_test_paths(root):
            if _test_imports_any(test_path, tool_imports):
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
        if profile == "fast" and changed_paths
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

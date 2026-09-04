#!/usr/bin/env python3
"""Run focused unit tests for AlatyrCore source tooling."""

from __future__ import annotations

import argparse
import ast
import io
import json
import math
import os
import sys
import time
import unittest
from pathlib import Path

from parallel_execution import child_capacity, run_commands


ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = ROOT / "tests"


CRITICAL_UNIT_SELECTION_PATHS = {
    "tools/check_source_unit_tests.py",
    "tools/check_all.py",
    "tools/source_state.py",
}

DEFAULT_SHARD_MULTIPLIER = 4
MIN_SHARD_MULTIPLIER = 2
MAX_SHARD_MULTIPLIER = 4
DURATION_HINTS_ENV = "ALATYR_TEST_DURATION_HINTS_JSON"


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


def load_duration_hints(raw: str | None = None) -> dict[str, float]:
    """Load optional scheduling hints without making them validation inputs."""

    value = os.environ.get(DURATION_HINTS_ENV, "{}") if raw is None else raw
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    hints: dict[str, float] = {}
    for path, duration in data.items():
        if not isinstance(path, str) or not path or isinstance(duration, bool):
            continue
        try:
            normalized_duration = float(duration)
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(normalized_duration) and normalized_duration > 0:
            hints[path.replace("\\", "/")] = normalized_duration
    return hints


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
    current_module = next(
        (name for name, candidate in modules.items() if candidate == path), None
    )
    current_package = ""
    if current_module:
        current_package = (
            current_module
            if path.name == "__init__.py"
            else current_module.rpartition(".")[0]
        )

    def resolve_relative(module: str | None, level: int) -> str | None:
        if level == 0:
            return module or ""
        package_parts = current_package.split(".") if current_package else []
        remove = level - 1
        if remove > len(package_parts):
            return None
        base = package_parts[: len(package_parts) - remove]
        if module:
            base.extend(module.split("."))
        return ".".join(base)

    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = resolve_relative(node.module, node.level)
            if base is None:
                return None
            if base:
                names.append(base)
            names.extend(
                f"{base}.{alias.name}" if base else alias.name
                for alias in node.names
                if alias.name != "*"
            )
        elif isinstance(node, ast.Call):
            is_dynamic = (
                isinstance(node.func, ast.Name) and node.func.id == "__import__"
            ) or (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "import_module"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "importlib"
            )
            if is_dynamic:
                if (
                    not node.args
                    or not isinstance(node.args[0], ast.Constant)
                    or not isinstance(node.args[0].value, str)
                ):
                    return None
                names.append(node.args[0].value)
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


def test_shards(
    paths: list[Path],
    capacity: int,
    *,
    duration_hints: dict[str, float] | None = None,
    shard_multiplier: int = DEFAULT_SHARD_MULTIPLIER,
) -> list[list[Path]]:
    """Partition every test file once into dynamically queued, weighted shards."""

    multiplier = min(
        MAX_SHARD_MULTIPLIER,
        max(MIN_SHARD_MULTIPLIER, shard_multiplier),
    )
    shard_count = min(max(1, capacity * multiplier), len(paths))
    shards: list[list[Path]] = [[] for _ in range(shard_count)]
    weights = [0.0] * shard_count
    hints = duration_hints or {}

    def weight(path: Path) -> float:
        candidates = [path.as_posix()]
        try:
            candidates.append(path.relative_to(ROOT).as_posix())
        except ValueError:
            pass
        hinted = next((hints[key] for key in candidates if key in hints), None)
        if (
            isinstance(hinted, (int, float))
            and not isinstance(hinted, bool)
            and math.isfinite(float(hinted))
            and hinted > 0
        ):
            return float(hinted)
        return float(max(1, path.stat().st_size))

    ordered = sorted(paths, key=lambda path: (-weight(path), path.as_posix()))
    for path in ordered:
        index = min(range(shard_count), key=lambda item: (weights[item], item))
        shards[index].append(path)
        weights[index] += weight(path)
    return [sorted(shard) for shard in shards if shard]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--test-file", action="append", default=[], help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every successful unit-test case instead of a concise summary.",
    )
    parser.add_argument(
        "--duration-hints",
        type=Path,
        help=(
            "Optional JSON object mapping test-file paths to historical seconds; "
            "invalid or missing hints fall back to file size."
        ),
    )
    args = parser.parse_args()
    args.verbose = args.verbose or os.environ.get("ALATYR_CHECK_VERBOSE") == "1"
    profile = os.environ.get("ALATYR_SOURCE_CHECK_PROFILE")
    changed_paths = _environment_changed_paths()
    selected_paths = (
        [ROOT / path for path in args.test_file]
        if args.test_file
        else (
            focused_test_paths(changed_paths)
            if profile in {"micro", "fast"} and changed_paths
            else None
        )
    )
    if selected_paths == []:
        print("OK: no focused source unit tests required for changed paths")
        return 0
    all_paths = _all_test_paths() if selected_paths is None else selected_paths
    capacity = child_capacity()
    if not args.test_file and capacity > 1 and len(all_paths) > 1:
        hint_payload: str | None = None
        if args.duration_hints is not None:
            try:
                hint_payload = args.duration_hints.read_text(encoding="utf-8")
            except OSError as exc:
                hint_payload = "{}"
                print(
                    f"WARN: cannot read duration hints ({exc}); using file sizes",
                    file=sys.stderr,
                )
        shards = test_shards(
            all_paths,
            capacity,
            duration_hints=load_duration_hints(hint_payload),
        )
        flattened = [path for shard in shards for path in shard]
        if sorted(flattened) != sorted(all_paths) or len(flattened) != len(
            set(flattened)
        ):
            print(
                "FAIL: unit-test shard coverage is incomplete or duplicated",
                file=sys.stderr,
            )
            return 1
        commands = [
            (
                f"shard-{index + 1}",
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    *(["--verbose"] if args.verbose else []),
                    *[
                        argument
                        for path in shard
                        for argument in ("--test-file", path.relative_to(ROOT).as_posix())
                    ],
                ],
            )
            for index, shard in enumerate(shards)
        ]
        started = time.monotonic()
        results = run_commands(commands, cwd=ROOT, capacity=capacity)
        failed = False
        for result in results:
            index = int(result.item_id.split("-")[1]) - 1
            if args.verbose or result.returncode != 0:
                print(
                    f"INFO: {result.item_id} ({len(shards[index])} files, "
                    f"{result.duration_seconds:.3f}s)"
                )
                if result.stdout:
                    print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
                if result.stderr:
                    print(
                        result.stderr,
                        end="" if result.stderr.endswith("\n") else "\n",
                        file=sys.stderr,
                    )
            failed = failed or result.returncode != 0
        if not failed and not args.verbose:
            print(
                f"OK: source unit tests passed for {len(all_paths)} files in "
                f"{len(shards)} shards ({time.monotonic() - started:.3f}s; "
                f"slowest shard {max(result.duration_seconds for result in results):.3f}s)"
            )
        return 1 if failed else 0
    suite = load_suite(selected_paths)
    if selected_paths is not None:
        relpaths = ", ".join(path.relative_to(ROOT).as_posix() for path in selected_paths)
        print(f"INFO: running focused source unit tests: {relpaths}")
    if args.verbose:
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    else:
        stream = io.StringIO()
        started = time.monotonic()
        result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
        if result.wasSuccessful():
            print(
                f"OK: {result.testsRun} source unit tests passed "
                f"({time.monotonic() - started:.3f}s)"
            )
        else:
            print(stream.getvalue(), end="", file=sys.stderr)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

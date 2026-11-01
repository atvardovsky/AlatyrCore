#!/usr/bin/env python3
"""Run focused unit tests for AlatyrCore source tooling."""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import sys
import time
import unittest
import statistics
from pathlib import Path, PureWindowsPath

from parallel_execution import CommandResult, child_capacity, run_commands
from local_python_import_graph import LocalPythonImportGraph
from source_test_timing import timed_suite, observation, positive_seconds


ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = ROOT / "tests"


CRITICAL_UNIT_SELECTION_PATHS = {
    "tools/check_source_unit_tests.py",
    "tools/check_all.py",
    "tools/source_state.py",
}

CENTRAL_DATA_TESTS = {
    "tools/check_manifest.json": (
        "tests/test_check_manifest_contract.py",
        "tests/test_source_check_manifest.py",
        "tests/test_check_all.py",
    ),
    "tools/source_context_router.json": (
        "tests/test_plan_minimum_work.py",
        "tests/test_task_classification_contract.py",
    ),
    "tools/source_worker_policy.json": (
        "tests/test_source_worker_contract.py",
        "tests/test_plan_minimum_work.py",
    ),
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
    if not isinstance(data, list) or any(not isinstance(item, str) or not item for item in data):
        return []
    return [item.replace("\\", "/") for item in data]


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


def _all_test_paths(root: Path = ROOT) -> list[Path]:
    return sorted((root / "tests").glob("test_*.py"))


def explicit_test_modules(modules: list[str], *, root: Path = ROOT) -> list[Path]:
    """Resolve an exact portable subset without changed-path inference."""
    if len(modules) != len(set(modules)):
        raise ValueError("duplicate --test-module arguments")
    paths = []
    for module in modules:
        if re.fullmatch(r"tests\.test_[A-Za-z0-9_]+", module) is None:
            raise ValueError(f"--test-module requires an exact tests.test_* module: {module}")
        path = root / (module.replace(".", "/") + ".py")
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"--test-module is missing or symlinked: {module}")
        paths.append(path)
    return paths


def focused_test_paths(changed_paths: list[str], *, root: Path = ROOT) -> list[Path] | None:
    """Return selected test files, `[]` to skip, or `None` for full fallback."""

    selected: set[Path] = set()
    requires_full = False
    changed_tools: set[Path] = set()
    directly_covered_tools: set[Path] = set()

    for relpath in changed_paths:
        path = Path(relpath.replace("\\", "/"))
        if path.is_absolute() or PureWindowsPath(relpath).anchor or ".." in path.parts:
            return None
        relpath = path.as_posix()
        if relpath in CRITICAL_UNIT_SELECTION_PATHS:
            requires_full = True
            continue
        if relpath in CENTRAL_DATA_TESTS:
            mapped = [root / test for test in CENTRAL_DATA_TESTS[relpath]]
            if all(test.is_file() for test in mapped):
                selected.update(mapped)
            else:
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
            changed_tools.add(tool_path.resolve())
            direct_name = path.with_suffix("").name
            direct_test = root / "tests" / f"test_{direct_name}.py"
            if direct_test.is_file():
                selected.add(direct_test)
                directly_covered_tools.add(tool_path.resolve())
            continue
        if relpath.startswith("tools/") and path.suffix == ".json":
            # Central tool data is executable policy. Unknown contracts fail
            # closed to the full suite instead of silently selecting no tests.
            requires_full = True
            continue
        if relpath.endswith(".py"):
            requires_full = True

    if changed_tools:
        graph = LocalPythonImportGraph(root)
        if any(not graph.scan(path).complete for path in graph.modules.values()):
            requires_full = True
        impacted = graph.reverse_dependents(changed_tools)
        uncovered_tools = changed_tools - directly_covered_tools
        for test_path in _all_test_paths(root):
            scan = graph.scan(test_path)
            if not scan.complete:
                requires_full = True
            elif scan.dependencies & impacted:
                selected.add(test_path)
                if uncovered_tools:
                    uncovered_tools.difference_update(graph.transitive_dependencies(test_path))
        # Another changed test or covered tool cannot discharge this obligation.
        if uncovered_tools:
            requires_full = True

    if requires_full:
        return None
    return sorted(selected)


def load_suite(paths: list[Path] | None, *, root: Path = ROOT) -> unittest.TestSuite:
    loader = unittest.defaultTestLoader
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if paths is None:
        return loader.discover(str(root / "tests"), pattern="test_*.py")
    suite = unittest.TestSuite()
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
    hints = {k: seconds for k, v in (duration_hints or {}).items() if (seconds := positive_seconds(v)) is not None}
    fallback = statistics.median(hints.values()) if hints else None

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
        return float(fallback if fallback is not None else max(1, path.stat().st_size))

    def hint_priority(path: Path) -> int:
        try:
            relative = path.relative_to(ROOT).as_posix()
        except ValueError:
            relative = path.as_posix()
        return 0 if path.as_posix() in hints or relative in hints else 1
    ordered = sorted(paths, key=lambda path: (-weight(path), hint_priority(path), path.as_posix()))
    for path in ordered:
        index = min(range(shard_count), key=lambda item: (weights[item], item))
        shards[index].append(path)
        weights[index] += weight(path)
    return [sorted(shard) for shard in shards if shard]


def checked_shard_results(
    results: list[CommandResult], expected_ids: list[str]
) -> list[CommandResult]:
    """Require one well-formed completion per planned shard before success."""
    if not isinstance(results, list):
        raise ValueError("shard results must be a list")
    by_id: dict[str, CommandResult] = {}
    for result in results:
        if not isinstance(result, CommandResult) or not isinstance(result.item_id, str):
            raise ValueError("malformed shard result identity")
        if result.item_id in by_id:
            raise ValueError(f"duplicate shard result: {result.item_id}")
        if (not isinstance(result.returncode, int) or isinstance(result.returncode, bool)
                or not isinstance(result.stdout, str) or not isinstance(result.stderr, str)
                or not isinstance(result.duration_seconds, (int, float))
                or (positive_seconds(result.duration_seconds) is None and result.duration_seconds != 0)
                or isinstance(result.duration_seconds, bool)):
            raise ValueError(f"malformed shard result fields: {result.item_id}")
        by_id[result.item_id] = result
    missing = sorted(set(expected_ids) - by_id.keys())
    unexpected = sorted(by_id.keys() - set(expected_ids))
    if missing or unexpected:
        raise ValueError(f"incomplete shard results: missing={missing}; unexpected={unexpected}")
    return [by_id[item_id] for item_id in expected_ids]


def run_shards(
    paths: list[Path], capacity: int, *, hints: dict[str, float], verbose: bool
) -> int:
    if not paths:
        print("FAIL: no files selected for sharded execution", file=sys.stderr)
        return 1
    shards = test_shards(paths, capacity, duration_hints=hints)
    flattened = [path for shard in shards for path in shard]
    if sorted(flattened) != sorted(paths) or len(flattened) != len(set(flattened)):
        print("FAIL: unit-test shard coverage is incomplete or duplicated", file=sys.stderr)
        return 1
    by_id = {f"shard-{index + 1}": shard for index, shard in enumerate(shards)}
    commands = [
        (item_id, [sys.executable, str(Path(__file__).resolve()),
                   *(["--verbose"] if verbose else []),
                   *[argument for path in shard
                     for argument in ("--test-file", path.relative_to(ROOT).as_posix())]])
        for item_id, shard in by_id.items()
    ]
    for item_id, shard in by_id.items():
        names = ", ".join(path.relative_to(ROOT).as_posix() for path in shard)
        print(f"PLAN: {item_id} ({len(shard)} files): {names}", flush=True)
    reported: set[str] = set()

    def report(result: CommandResult) -> None:
        checked_shard_results([result], [result.item_id])
        if result.item_id not in by_id or result.item_id in reported:
            raise ValueError(f"unexpected or repeated shard notification: {result.item_id}")
        reported.add(result.item_id)
        state = "PASS" if result.returncode == 0 else "FAIL"
        print(f"{state}: {result.item_id} ({len(by_id[result.item_id])} files, "
              f"{result.duration_seconds:.3f}s)", flush=True)
        if verbose or result.returncode != 0:
            if result.stdout:
                print(result.stdout, end="" if result.stdout.endswith("\n") else "\n", flush=True)
            if result.stderr:
                print(result.stderr, end="" if result.stderr.endswith("\n") else "\n",
                      file=sys.stderr, flush=True)

    started = time.monotonic()
    try:
        results = checked_shard_results(
            run_commands(commands, cwd=ROOT, capacity=capacity, on_complete=report), list(by_id)
        )
        for result in results:
            if result.item_id not in reported:
                report(result)
    except KeyboardInterrupt:
        print("FAIL: unit-test execution interrupted; no success evidence", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"FAIL: unit-test execution did not converge: {exc}", file=sys.stderr)
        return 1
    if any(result.returncode != 0 for result in results):
        return 1
    if not verbose:
        print(f"OK: source unit tests passed for {len(paths)} files in {len(shards)} shards "
              f"({time.monotonic() - started:.3f}s; "
              f"slowest shard {max(result.duration_seconds for result in results):.3f}s)")
    return 0


def main() -> int:
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--test-file", action="append", default=[], help=argparse.SUPPRESS
    )
    selection.add_argument(
        "--test-module", nargs="+", action="extend", default=[],
        help="Exact tests.test_* modules to run with the bounded shard executor.",
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
    try:
        module_paths = explicit_test_modules(args.test_module)
    except ValueError as exc:
        parser.error(str(exc))
    if len(args.test_file) != len({(ROOT / p).resolve() for p in args.test_file}):
        parser.error("duplicate --test-file arguments")
    args.verbose = args.verbose or os.environ.get("ALATYR_CHECK_VERBOSE") == "1"
    profile = os.environ.get("ALATYR_SOURCE_CHECK_PROFILE")
    changed_paths = _environment_changed_paths()
    selected_paths = (
        [ROOT / path for path in args.test_file]
        if args.test_file
        else module_paths if args.test_module else (
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
        return run_shards(all_paths, capacity, hints=load_duration_hints(hint_payload),
                          verbose=args.verbose)
    durations: dict[str, float] = {}
    timing_warnings: list[str] = []
    suite = timed_suite(load_suite(selected_paths), durations, ROOT, warnings=timing_warnings)
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
    for warning in timing_warnings:
        print(f"WARN: {warning}", file=sys.stderr)
    if result.wasSuccessful() and not timing_warnings and os.environ.get("ALATYR_CONFORMANCE_ARTIFACT_ROOT"):
        import hashlib
        artifact_root = Path(os.environ["ALATYR_CONFORMANCE_ARTIFACT_ROOT"])
        if artifact_root.is_absolute():
            key = hashlib.sha256("\0".join(str(p) for p in all_paths).encode()).hexdigest()
            try:
                artifact_root.mkdir(parents=True, exist_ok=True)
                (artifact_root / f"unit-timing-{key}.json").write_text(
                    json.dumps(observation(ROOT, durations)), encoding="utf-8"
                )
            except (OSError, ValueError) as exc:
                print(f"WARN: timing observations unavailable: {exc}", file=sys.stderr)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

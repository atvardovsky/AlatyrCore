"""Non-authoritative, content-bound unit-suite scheduling observations."""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
import time
import unittest
from pathlib import Path
from typing import Any


def identity(root: Path) -> dict[str, str]:
    return {"runtime": platform.python_implementation() + ":" + platform.python_version(),
            "platform": sys.platform,
            "runner": hashlib.sha256((root / "tools/check_source_unit_tests.py").read_bytes()
                                     + Path(__file__).read_bytes()).hexdigest()}


def observation(root: Path, durations: dict[str, float]) -> dict[str, Any]:
    return {"schema_version": 1, "identity": identity(root), "files": {
        path: {"seconds": seconds, "sha256": hashlib.sha256((root / path).read_bytes()).hexdigest()}
        for path, seconds in sorted(durations.items())}}


def positive_seconds(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        seconds = float(value)
    except (ValueError, OverflowError):
        return None
    return seconds if math.isfinite(seconds) and seconds > 0 else None


def report_hints(report: Any, root: Path) -> dict[str, float]:
    timing = report.get("timing") if isinstance(report, dict) else None
    return hints(timing.get("unit_test_durations"), root) if isinstance(timing, dict) else {}


def hints(value: Any, root: Path) -> dict[str, float]:
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        return {}
    try:
        if value.get("identity") != identity(root):
            return {}
    except OSError:
        return {}
    result = {}
    files = value.get("files")
    if not isinstance(files, dict):
        return {}
    for path, item in files.items():
        if not isinstance(path, str) or not path.startswith("tests/test_") or Path(path).name != path[len("tests/"):]:
            continue
        if not isinstance(item, dict):
            continue
        seconds = positive_seconds(item.get("seconds"))
        if seconds is None:
            continue
        candidate = root / path
        if candidate.is_symlink() or not candidate.is_file():
            continue
        try:
            if hashlib.sha256(candidate.read_bytes()).hexdigest() == item.get("sha256"):
                result[path] = float(seconds)
        except OSError:
            continue
    return result


class _ModuleClock:
    def __init__(self, durations, root, clock, warnings):
        self.durations, self.root, self.clock, self.warnings = durations, root.resolve(), clock, warnings
        self.module, self.started = None, None

    def transition(self, module):
        if self.clock is None:
            return
        try:
            now = self.clock()
            source = getattr(sys.modules.get(self.module), "__file__", None)
            if isinstance(source, str) and self.started is not None:
                path = Path(source).resolve()
                if path.parent == self.root / "tests" and path.name.startswith("test_"):
                    key = "tests/" + path.name
                    self.durations[key] = self.durations.get(key, 0.0) + now - self.started
            self.module, self.started = module, now
        except Exception as exc:
            self.clock = None
            self.durations.clear()
            self.warnings.append(f"unit timing disabled: {exc}")


class _TimedSuite(unittest.TestSuite):
    def __init__(self, tests, timer):
        super().__init__(tests)
        self.timer, self.next_module = timer, None

    def _handleModuleFixture(self, test, result):
        self.next_module = test.__class__.__module__
        try:
            return super()._handleModuleFixture(test, result)
        finally:
            self.next_module = None

    def _handleModuleTearDown(self, result):
        try:
            return super()._handleModuleTearDown(result)
        finally:
            # Called after old class/module cleanup, before the next module setup.
            self.timer.transition(self.next_module)


def timed_suite(suite: unittest.TestSuite, durations: dict[str, float], root: Path,
                *, clock=None, warnings=None) -> unittest.TestSuite:
    def standard(group):
        return not isinstance(group, unittest.TestSuite) or (
            type(group) is unittest.TestSuite and all(standard(child) for child in group))
    if not standard(suite):
        return suite
    timer = _ModuleClock(durations, root, clock or time.perf_counter, warnings if warnings is not None else [])
    def wrap(group):
        if not isinstance(group, unittest.TestSuite):
            return group
        result = _TimedSuite([wrap(child) for child in group], timer)
        result._cleanup = group._cleanup
        return result
    return wrap(suite)


def collect(directory: Path, root: Path) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for path in sorted(directory.glob("unit-timing-*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            valid = hints(value, root)
        except (OSError, ValueError, UnicodeError, RecursionError):
            continue
        for key in valid:
            if key in files:
                return {}
            files[key] = value["files"][key]
    try:
        return {"schema_version": 1, "identity": identity(root), "files": files}
    except OSError:
        return {}

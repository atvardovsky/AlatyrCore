from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from toolchain import (  # noqa: E402
    MINIMUM_PYTHON,
    ToolchainError,
    git_failure,
    missing_packages,
    package_failure,
    preflight,
    python_failure,
    require_supported_python,
    toolchain_failure,
)


class ToolchainUnitTests(unittest.TestCase):
    def test_python_failure_is_actionable_and_version_bound(self) -> None:
        failure = python_failure(version=(3, 9, 18))
        self.assertIn("Python 3.10+ is required", failure)
        self.assertIn("3.9.18", failure)
        self.assertIsNone(python_failure(version=MINIMUM_PYTHON + (0,)))
        self.assertIsNone(python_failure(version=(3, 13, 0)))

    def test_missing_packages_report_only_declared_names(self) -> None:
        available = {"yaml"}

        def find_spec(name: str):
            return object() if name in available else None

        self.assertEqual(missing_packages(("yaml", "jsonschema"), find_spec=find_spec),
                         ("jsonschema",))
        failure = package_failure(("yaml", "jsonschema"), find_spec=find_spec)
        self.assertIn("jsonschema", failure)
        self.assertIn("requirements-dev.txt", failure)
        self.assertNotIn("yaml,", failure)

    def test_missing_package_probe_errors_are_fail_closed(self) -> None:
        def broken(name: str):
            raise ModuleNotFoundError(name)

        self.assertEqual(missing_packages(("yaml",), find_spec=broken), ("yaml",))

    def test_git_failure_is_actionable(self) -> None:
        self.assertIn("Git is required", git_failure(which=lambda name: None))
        self.assertIsNone(git_failure(which=lambda name: "/usr/bin/git"))

    def test_toolchain_failure_orders_python_before_packages_and_git(self) -> None:
        failure = toolchain_failure(
            version=(3, 8, 10),
            packages=("yaml",),
            require_git=True,
            find_spec=lambda name: None,
            which=lambda name: None,
        )
        self.assertIn("Python 3.10+", failure)

    def test_preflight_raises_one_toolchain_error(self) -> None:
        with self.assertRaisesRegex(ToolchainError, "missing source-tooling"):
            preflight(
                version=(3, 10, 0),
                packages=("yaml",),
                require_git=False,
                find_spec=lambda name: None,
            )

    def test_require_supported_python_exits_two_with_one_message(self) -> None:
        error = io.StringIO()
        with redirect_stderr(error), self.assertRaises(SystemExit) as raised:
            require_supported_python(version=(3, 8, 10))
        self.assertEqual(raised.exception.code, 2)
        message = error.getvalue()
        self.assertEqual(message.count("FAIL:"), 1)
        self.assertIn("Python 3.10+", message)


class ToolchainCliTests(unittest.TestCase):
    def test_cli_json_reports_available_environment(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "tools/check_toolchain.py"), "--json", "--require-git"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["minimum_python"], "3.10")
        self.assertIsNone(report["failure"])

    def test_python_38_guard_precedes_dependency_imports(self) -> None:
        candidates = [shutil.which("python3.8"), "/usr/bin/python3.8", "/usr/bin/python3"]
        executable = next(
            (candidate for candidate in candidates
             if candidate and Path(candidate).exists()
             and subprocess.run([candidate, "-c", "import sys; print(sys.version_info[:2])"],
                                capture_output=True, text=True).stdout.strip() == "(3, 8)"),
            None,
        )
        if executable is None:
            self.skipTest("no Python 3.8 interpreter available")
        completed = subprocess.run(
            [executable, str(ROOT / "tools/check_all.py"), "--list"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 2, completed.stderr + completed.stdout)
        self.assertIn("Python 3.10+ is required", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()

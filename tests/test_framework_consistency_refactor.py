from __future__ import annotations

import ast
import io
import sys
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import check_framework_consistency as checker  # noqa: E402
from framework_consistency import CheckContext  # noqa: E402


GROUPS = (
    "check_target_operation_surfaces",
    "check_target_governance_surfaces",
    "check_rule_registry_contract",
    "check_core_source_tools",
    "check_context_source_tools",
    "check_operation_source_tools",
    "check_release_tools",
    "check_conformance_tools",
    "check_evidence_and_messages",
    "check_target_runtime_policies",
    "check_bridges_and_git_visibility",
)


class FrameworkConsistencyRefactorTests(unittest.TestCase):
    def test_success_output_and_exit_semantics_are_stable(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = checker.main()

        self.assertEqual(result, 0)
        self.assertEqual(
            stdout.getvalue(),
            "OK: checked 50 framework docs and target templates\n",
        )
        self.assertEqual(stderr.getvalue(), "")

    def test_explicit_groups_preserve_failure_order_and_exit_semantics(self) -> None:
        expected = [f"group-{index}" for index in range(len(GROUPS))]
        stdout = io.StringIO()
        stderr = io.StringIO()

        with ExitStack() as stack:
            for name, failure in zip(GROUPS, expected):
                stack.enter_context(patch.object(checker, name, return_value=[failure]))
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = checker.main()

        self.assertEqual(result, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            stderr.getvalue(),
            "".join(f"FAIL: {failure}\n" for failure in expected),
        )

    def test_context_is_immutable_and_rejects_invalid_surface_shape(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            surface_path = root / "conformance" / "runs" / "assistant-surfaces.json"
            surface_path.parent.mkdir(parents=True)
            surface_path.write_text('{"surfaces": {}}', encoding="utf-8")
            context = CheckContext(root, (), (), ())

            with self.assertRaises(FrozenInstanceError):
                context.root = ROOT  # type: ignore[misc]
            with self.assertRaisesRegex(ValueError, "must contain a surfaces list"):
                context.assistant_surfaces()

    def test_extracted_functions_stay_within_complexity_threshold(self) -> None:
        helper_paths = sorted((TOOLS / "framework_consistency").glob("*.py"))
        observed: dict[str, int] = {}
        for path in helper_paths:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    observed[node.name] = node.end_lineno - node.lineno + 1

        context_methods = {
            "read_text",
            "line_count",
            "assistant_surfaces",
            "git_ignored_no_index",
        }
        self.assertEqual(set(observed) - context_methods, set(GROUPS))
        self.assertLessEqual(max(observed.values()), 300)


if __name__ == "__main__":
    unittest.main()

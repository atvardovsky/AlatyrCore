from __future__ import annotations

import json
import io
import os
import subprocess
import sys
import tempfile
import unittest
from itertools import permutations
from contextlib import redirect_stdout
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_source_unit_tests import (  # noqa: E402
    _environment_changed_paths,
    focused_test_paths,
    load_duration_hints,
    test_shards,
    load_suite,
)


class SourceUnitTestSelectionTests(unittest.TestCase):
    def test_direct_runner_prevents_nested_bytecode_writes(self):
        import check_source_unit_tests as runner
        def check_environment():
            self.assertTrue(sys.dont_write_bytecode)
            self.assertEqual(os.environ["PYTHONDONTWRITEBYTECODE"], "1")
            child = subprocess.run([sys.executable, "-c", "import sys; print(sys.dont_write_bytecode)"], capture_output=True, text=True)
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertEqual(child.stdout.strip(), "True")
        suite = unittest.TestSuite([unittest.FunctionTestCase(check_environment)])
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, "dont_write_bytecode", False), patch.object(sys, "argv", ["source-unit-tests"]), patch.object(runner, "_all_test_paths", return_value=[]), patch.object(runner, "load_suite", return_value=suite), patch.object(runner, "child_capacity", return_value=1), redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(), 0)

    def test_serial_discovery_has_repository_root_for_shared_fixtures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(unittest.defaultTestLoader, "discover", side_effect=lambda *a, **k: unittest.TestSuite() if str(root) in sys.path else self.fail("root missing")):
                try:
                    load_suite(None, root=root)
                finally:
                    sys.path.remove(str(root))
    def test_docs_only_change_selects_no_unit_tests(self) -> None:
        self.assertEqual(focused_test_paths(["README.md"], root=ROOT), [])

    def test_changed_test_file_selects_itself(self) -> None:
        selected = focused_test_paths(["tests/test_check_all.py"], root=ROOT)

        self.assertEqual(selected, [ROOT / "tests" / "test_check_all.py"])

    def test_deleted_test_file_falls_back_to_full_suite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tests").mkdir()

            self.assertIsNone(
                focused_test_paths(["tests/test_removed.py"], root=root)
            )

    def test_unmapped_tool_change_falls_back_to_full_suite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            (root / "tests").mkdir()
            (root / "tools" / "new_tool.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "tests" / "test_other.py").write_text(
                "import unittest\n\nclass Other(unittest.TestCase):\n    pass\n",
                encoding="utf-8",
            )

            self.assertIsNone(
                focused_test_paths(["tools/new_tool.py"], root=root)
            )

    def test_unrelated_changes_cannot_suppress_an_unmapped_tool_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "tools").mkdir()
            (root / "tests").mkdir()
            (root / "tools/uncovered.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "tools/covered.py").write_text("VALUE = 2\n", encoding="utf-8")
            (root / "tests/test_other.py").write_text("import unittest\n", encoding="utf-8")
            (root / "tests/test_covered.py").write_text("from covered import VALUE\n", encoding="utf-8")
            for added in [(), ("tests/test_other.py",), ("tools/covered.py",),
                          ("tools/covered.py", "tests/test_other.py")]:
                for changes in permutations(("tools/uncovered.py", *added)):
                    with self.subTest(changes=changes):
                        self.assertIsNone(focused_test_paths(list(changes), root=root))

    def test_multiple_covered_tools_retain_focused_transitive_selection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "tools").mkdir()
            (root / "tests").mkdir()
            (root / "tools/core.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "tools/wrapper.py").write_text("from core import VALUE\n", encoding="utf-8")
            selected = root / "tests/test_wrapper.py"
            selected.write_text("from wrapper import VALUE\n", encoding="utf-8")
            unrelated = root / "tests/test_other.py"
            unrelated.write_text("import unittest\n", encoding="utf-8")
            for changes in permutations(("tools/core.py", "tools/wrapper.py", "tests/test_other.py")):
                with self.subTest(changes=changes):
                    self.assertEqual(focused_test_paths(list(changes), root=root),
                                     [unrelated, selected])

    def test_central_json_contract_selects_its_mapped_tests(self) -> None:
        selected = focused_test_paths(
            ["tools/source_context_router.json"], root=ROOT
        )

        self.assertEqual(
            selected,
            [
                ROOT / "tests/test_plan_minimum_work.py",
                ROOT / "tests/test_task_classification_contract.py",
            ],
        )

    def test_equivalent_changed_path_spellings_preserve_selection(self) -> None:
        for canonical in ("tools/source_context_router.json", "tools/unknown-policy.json",
                          "tools/check_source_unit_tests.py", "tests/test_check_all.py"):
            for spelling in (canonical, "./" + canonical, ".//" + canonical,
                             canonical.replace("/", "\\")):
                for extra in ([], ["tests/test_source_unit_tests.py"]):
                    with self.subTest(spelling=spelling, extra=extra):
                        with patch.dict("os.environ", {"ALATYR_CHANGED_PATHS_JSON": json.dumps([spelling, *extra])}):
                            changes = _environment_changed_paths()
                        self.assertEqual(focused_test_paths(changes),
                                         focused_test_paths([canonical, *extra]))

    def test_escaping_changed_paths_fail_closed(self) -> None:
        for path in ("../tools/policy.json", "tools/../policy.json", "/tmp/policy.json",
                     "C:/tools/policy.json", "C:tools/policy.json", r"\\server\share\policy.json"):
            with self.subTest(path=path):
                self.assertIsNone(focused_test_paths([path, "tests/test_check_all.py"]))

    def test_invalid_environment_paths_cannot_leave_a_docs_only_selection(self) -> None:
        for value in (None, 1, {}, [], ""):
            with self.subTest(value=value):
                with patch.dict("os.environ", {"ALATYR_CHANGED_PATHS_JSON": json.dumps(["README.md", value])}):
                    self.assertEqual(_environment_changed_paths(), [])
        with patch.dict("os.environ", {"ALATYR_CHANGED_PATHS_JSON": json.dumps(["README.md", "/tmp/policy.json"])}):
            self.assertIsNone(focused_test_paths(_environment_changed_paths()))

    def test_unknown_tool_json_falls_back_to_full_suite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            (root / "tests").mkdir()
            (root / "tools/new_contract.json").write_text("{}\n", encoding="utf-8")

            self.assertIsNone(
                focused_test_paths(["tools/new_contract.json"], root=root)
            )

    def test_tool_change_selects_importing_tests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            (root / "tests").mkdir()
            (root / "tools" / "demo_tool.py").write_text("VALUE = 1\n", encoding="utf-8")
            expected = root / "tests" / "test_selected.py"
            expected.write_text(
                "import unittest\nfrom demo_tool import VALUE\n\n"
                "class Selected(unittest.TestCase):\n"
                "    def test_value(self):\n"
                "        self.assertEqual(VALUE, 1)\n",
                encoding="utf-8",
            )
            (root / "tests" / "test_other.py").write_text(
                "import unittest\n\nclass Other(unittest.TestCase):\n    pass\n",
                encoding="utf-8",
            )

            self.assertEqual(
                focused_test_paths(["tools/demo_tool.py"], root=root),
                [expected],
            )

    def test_tool_change_selects_tests_through_reverse_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            (root / "tests").mkdir()
            (root / "tools/core.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "tools/wrapper.py").write_text(
                "from core import VALUE\n", encoding="utf-8"
            )
            expected = root / "tests/test_wrapper.py"
            expected.write_text(
                "from wrapper import VALUE\n", encoding="utf-8"
            )

            self.assertEqual(
                focused_test_paths(["tools/core.py"], root=root),
                [expected],
            )

    def test_relative_import_selects_tests_through_package_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools/pkg").mkdir(parents=True)
            (root / "tests").mkdir()
            (root / "tools/pkg/__init__.py").write_text("", encoding="utf-8")
            (root / "tools/pkg/core.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "tools/pkg/wrapper.py").write_text(
                "from .core import VALUE\n", encoding="utf-8"
            )
            expected = root / "tests/test_wrapper.py"
            expected.write_text("from pkg.wrapper import VALUE\n", encoding="utf-8")

            self.assertEqual(
                focused_test_paths(["tools/pkg/core.py"], root=root),
                [expected],
            )

    def test_non_literal_dynamic_import_falls_back_to_full_suite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            (root / "tests").mkdir()
            (root / "tools/core.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "tools/wrapper.py").write_text(
                "import importlib\nname = 'core'\nmodule = importlib.import_module(name)\n",
                encoding="utf-8",
            )
            (root / "tests/test_wrapper.py").write_text(
                "import wrapper\n", encoding="utf-8"
            )

            self.assertIsNone(focused_test_paths(["tools/core.py"], root=root))

    def test_test_shards_cover_every_file_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for index, size in enumerate([10, 50, 20, 40, 30]):
                path = root / f"test_{index}.py"
                path.write_text("x" * size, encoding="utf-8")
                paths.append(path)

            shards = test_shards(paths, 3)
            flattened = [path for shard in shards for path in shard]

            self.assertEqual(sorted(flattened), sorted(paths))
            self.assertEqual(len(flattened), len(set(flattened)))

    def test_test_shards_overdecompose_for_dynamic_queueing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for index in range(12):
                path = root / f"test_{index}.py"
                path.write_text("x", encoding="utf-8")
                paths.append(path)

            shards = test_shards(paths, 2)

            self.assertEqual(len(shards), 8)
            self.assertEqual(
                sorted(path for shard in shards for path in shard), sorted(paths)
            )

    def test_test_shards_cap_overdecomposition_at_four_per_worker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for index in range(20):
                path = Path(directory) / f"test_{index}.py"
                path.write_text("x", encoding="utf-8")
                paths.append(path)

            self.assertEqual(len(test_shards(paths, 2, shard_multiplier=10)), 8)

    def test_test_shards_prefer_duration_hints_over_file_size(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            slow = root / "test_slow.py"
            large = root / "test_large.py"
            small = root / "test_small.py"
            slow.write_text("x", encoding="utf-8")
            large.write_text("x" * 100, encoding="utf-8")
            small.write_text("x", encoding="utf-8")

            shards = test_shards(
                [large, small, slow],
                2,
                duration_hints={slow.as_posix(): 1000.0},
                shard_multiplier=1,
            )

            self.assertIn(slow, shards[0])
            self.assertIn(large, shards[1])

    def test_duration_hints_ignore_invalid_or_non_positive_values(self) -> None:
        self.assertEqual(
            load_duration_hints(
                '{"tests/slow.py": 2.5, "zero": 0, "bool": true, '
                '"nan": "NaN", "negative": -1}'
            ),
            {"tests/slow.py": 2.5},
        )

    def test_invalid_duration_hint_payload_falls_back_safely(self) -> None:
        self.assertEqual(load_duration_hints("not-json"), {})


if __name__ == "__main__":
    unittest.main()

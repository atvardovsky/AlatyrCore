from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_source_unit_tests import (  # noqa: E402
    focused_test_paths,
    load_duration_hints,
    test_shards,
)


class SourceUnitTestSelectionTests(unittest.TestCase):
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

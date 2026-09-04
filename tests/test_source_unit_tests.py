from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_source_unit_tests import focused_test_paths  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()

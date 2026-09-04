from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_tool_complexity import iter_functions, load_allowlist  # noqa: E402


class ToolComplexityTests(unittest.TestCase):
    def test_allowlist_contract_loads_known_large_functions(self) -> None:
        threshold, allowlist = load_allowlist()

        self.assertGreaterEqual(threshold, 1)
        self.assertIn(
            (
                "tools/target_adapter_validation/team_collaboration.py",
                "validate_team_collaboration",
            ),
            allowlist,
        )

    def test_iter_functions_reports_nested_class_qualnames(self) -> None:
        tree = ast.parse(
            "class Example:\n"
            "    def method(self):\n"
            "        def nested():\n"
            "            return 1\n"
            "        return nested()\n"
        )

        self.assertEqual(
            [name for name, _node in iter_functions(tree)],
            ["Example.method", "Example.method.nested"],
        )


if __name__ == "__main__":
    unittest.main()

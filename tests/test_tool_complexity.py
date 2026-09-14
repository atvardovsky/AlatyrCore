from __future__ import annotations

import ast
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_tool_complexity import (  # noqa: E402
    allowlist_cap_failure,
    iter_functions,
    load_allowlist,
    version_key,
)


class ToolComplexityTests(unittest.TestCase):
    def test_allowlist_caps_reject_growth_and_excessive_slack(self) -> None:
        self.assertIsNone(allowlist_cap_failure("tools/a.py", "main", 306, 306))
        self.assertIsNone(allowlist_cap_failure("tools/a.py", "main", 306, 331))
        self.assertIn(
            "grew",
            allowlist_cap_failure("tools/a.py", "main", 307, 306) or "",
        )
        self.assertIn(
            "stale",
            allowlist_cap_failure("tools/a.py", "main", 306, 332) or "",
        )

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

    def test_allowlist_declares_owner_review_and_aggregate_cap(self) -> None:
        data = json.loads(
            (ROOT / "tools/tool_complexity_allowlist.json").read_text(encoding="utf-8")
        )

        self.assertTrue(data["debt_owner"])
        self.assertTrue(data["review_by_version"])
        self.assertGreaterEqual(
            data["max_known_large_functions"], len(data["known_large_functions"])
        )

    def test_review_milestones_have_semantic_prerelease_order(self) -> None:
        self.assertLess(
            version_key("0.1.0-alpha.64"),
            version_key("0.1.0-beta.1"),
        )
        self.assertLess(version_key("0.1.0-rc.1"), version_key("0.1.0"))
        with self.assertRaisesRegex(ValueError, "unsupported source version"):
            version_key("next")


if __name__ == "__main__":
    unittest.main()

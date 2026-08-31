from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from report_support_costs import build_scaffold_report  # noqa: E402


class SupportCostReportTests(unittest.TestCase):
    def test_cached_expensive_summaries_can_be_injected(self) -> None:
        assistant_surface_report = {
            "known_surfaces": 99,
            "declared_bridge_paths": 88,
            "capability_template_files": 77,
            "unique_capability_payloads_without_identity": 66,
        }
        optional_module_cost_report = [
            {
                "module": "fixture",
                "min_framework_pack": "kernel",
                "dependency_closure": ["fixture"],
                "target_files": 1,
                "target_words": 2,
                "target_bytes": 3,
                "required_pack_with_dependencies": "kernel",
            }
        ]

        with patch(
            "report_support_costs.assistant_surface_summary"
        ) as assistant_summary, patch("report_support_costs.module_costs") as modules:
            report = build_scaffold_report(
                "kernel",
                assistant_surface_report=assistant_surface_report,
                optional_module_cost_report=optional_module_cost_report,
            )

        assistant_summary.assert_not_called()
        modules.assert_not_called()
        self.assertEqual(report["assistant_surfaces"], assistant_surface_report)
        self.assertEqual(report["optional_module_costs"], optional_module_cost_report)


if __name__ == "__main__":
    unittest.main()

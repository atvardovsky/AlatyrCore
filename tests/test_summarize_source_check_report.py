from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from summarize_source_check_report import (  # noqa: E402
    render_summary,
    selected_blocked_checks,
    selected_failure_checks,
    status_counts,
)


class SourceCheckReportSummaryTests(unittest.TestCase):
    def test_render_summary_surfaces_failures_blockers_and_slowest_checks(self) -> None:
        report = {
            "profile": "platform",
            "source": {
                "source_commit": "abc123",
                "source_tree_dirty": False,
            },
            "timing": {
                "wall_seconds": 12.345,
                "slowest_checks": [
                    {"id": "portable", "duration_seconds": 9.1},
                    {"id": "links", "duration_seconds": 2.4},
                ],
            },
            "selection": {
                "fell_back_to_full": True,
                "unmatched_changed_paths": ["new/path.md"],
            },
            "checks": [
                {"id": "ok", "status": "passed"},
                {
                    "id": "bad",
                    "status": "failed",
                    "exit_code": 1,
                    "stderr": "line 1\nline 2",
                },
                {"id": "late", "status": "failed", "exit_code": 124, "timed_out": True},
                {"id": "blocked", "status": "blocked", "blocked_by": ["bad"]},
            ],
        }

        rendered = render_summary(report, source_label="tmp/report.json")

        self.assertIn("Profile: `platform`", rendered)
        self.assertIn("Status counts: blocked=1, failed=2, passed=1", rendered)
        self.assertIn("Focused selection fell back to the full profile", rendered)
        self.assertIn("`bad` exit=1", rendered)
        self.assertIn("line 1 line 2", rendered)
        self.assertIn("`late` exit=124; timed out", rendered)
        self.assertIn("`blocked` blocked by bad", rendered)
        self.assertIn("`portable` 9.10s", rendered)

    def test_status_helpers_ignore_malformed_entries(self) -> None:
        checks = [
            {"status": "passed"},
            {"status": "passed"},
            {"status": "failed", "id": "bad"},
            {"status": "blocked", "id": "blocked"},
            {"id": "missing"},
        ]

        self.assertEqual(status_counts(checks), {"blocked": 1, "failed": 1, "passed": 2})
        self.assertEqual(
            [check["id"] for check in selected_failure_checks(checks)], ["bad"]
        )
        self.assertEqual(
            [check["id"] for check in selected_blocked_checks(checks)], ["blocked"]
        )


if __name__ == "__main__":
    unittest.main()

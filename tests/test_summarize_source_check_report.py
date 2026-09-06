from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from summarize_source_check_report import (  # noqa: E402
    main,
    render_summary,
    selected_blocked_checks,
    selected_failure_checks,
    status_counts,
)


class SourceCheckReportSummaryTests(unittest.TestCase):
    def test_render_summary_surfaces_failures_blockers_and_slowest_checks(self) -> None:
        report = {
            "schema_version": 3,
            "report_kind": "alatyr-source-check-run",
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

    def test_status_helpers_count_supported_entries(self) -> None:
        checks = [
            {"status": "passed"},
            {"status": "passed"},
            {"status": "failed", "id": "bad"},
            {"status": "blocked", "id": "blocked"},
        ]

        self.assertEqual(status_counts(checks), {"blocked": 1, "failed": 1, "passed": 2})
        self.assertEqual(
            [check["id"] for check in selected_failure_checks(checks)], ["bad"]
        )
        self.assertEqual(
            [check["id"] for check in selected_blocked_checks(checks)], ["blocked"]
        )

    def test_render_summary_rejects_unsupported_check_status(self) -> None:
        report = {"checks": [{"id": "bad", "status": "unknown"}]}

        with self.assertRaisesRegex(ValueError, "unsupported status"):
            render_summary(report, source_label="report.json")

    def test_cli_rejects_unsupported_schema_even_with_allow_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.json"
            report_path.write_text(
                json.dumps(
                    {
                        "schema_version": 99,
                        "report_kind": "alatyr-source-check-run",
                        "checks": [],
                    }
                ),
                encoding="utf-8",
            )
            stderr = io.StringIO()
            with patch.object(
                sys, "argv", ["summarize", str(report_path), "--allow-missing"]
            ), contextlib.redirect_stderr(stderr):
                result = main()

        self.assertEqual(result, 1)
        self.assertIn("only schema 2 or 3", stderr.getvalue())

    def test_cli_rejects_wrong_kind_and_unsupported_status(self) -> None:
        invalid_reports = [
            {
                "schema_version": 3,
                "report_kind": "wrong-kind",
                "checks": [],
            },
            {
                "schema_version": 3,
                "report_kind": "alatyr-source-check-run",
                "checks": [{"id": "bad", "status": "unknown"}],
            },
        ]
        for report in invalid_reports:
            with self.subTest(report=report):
                with tempfile.TemporaryDirectory() as directory:
                    report_path = Path(directory) / "report.json"
                    report_path.write_text(json.dumps(report), encoding="utf-8")
                    stderr = io.StringIO()
                    with patch.object(
                        sys,
                        "argv",
                        ["summarize", str(report_path), "--allow-missing"],
                    ), contextlib.redirect_stderr(stderr):
                        result = main()

                self.assertEqual(result, 1)
                self.assertIn("FAIL: cannot read source-check report", stderr.getvalue())

    def test_cli_allow_missing_tolerates_absent_path_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = root / "missing.json"
            with patch.object(
                sys, "argv", ["summarize", str(missing), "--allow-missing"]
            ), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)

            stderr = io.StringIO()
            with patch.object(
                sys, "argv", ["summarize", str(root), "--allow-missing"]
            ), contextlib.redirect_stderr(stderr):
                self.assertEqual(main(), 1)
            self.assertIn("is not a file", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

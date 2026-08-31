from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from compare_source_check_reports import load_report, render_comparison  # noqa: E402


def report(wall: float, commit: str = "abc") -> dict[str, object]:
    return {
        "schema_version": 2,
        "report_kind": "alatyr-source-check-run",
        "profile": "quick",
        "source": {
            "source_commit": commit,
            "source_tree_dirty": False,
            "manifest_sha256": "0" * 64,
        },
        "timing": {
            "wall_seconds": wall,
            "sum_check_duration_seconds": wall * 2,
        },
        "checks": [{"id": "example", "status": "passed"}],
    }


class SourceCheckReportComparisonTests(unittest.TestCase):
    def test_rejects_legacy_report_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.json"
            path.write_text(
                json.dumps({"schema_version": 1, "report_kind": "alatyr-source-check-run"}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "only schema 2"):
                load_report(path)

    def test_render_comparison_reports_timing_delta(self) -> None:
        text = render_comparison(report(10.0), report(7.5))

        self.assertIn("Selected checks: 1 -> 1", text)
        self.assertIn("Wall seconds: 10.000 -> 7.500 (-2.500)", text)
        self.assertIn("Comparability: same source identity", text)


if __name__ == "__main__":
    unittest.main()

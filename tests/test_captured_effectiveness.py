from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_captured_effectiveness_results import (  # noqa: E402
    MODES,
    QUALITY_METRICS,
    validate_aggregate_eligibility,
)


def accepted_reports() -> dict[str, dict[str, object]]:
    return {
        mode: {
            "outcome": "accepted",
            "acceptance_criteria_results": [{"status": "pass"}],
            **{metric: 0 for metric in QUALITY_METRICS},
        }
        for mode in MODES
    }


class CapturedEffectivenessTests(unittest.TestCase):
    def test_reviewed_narrow_result_can_qualify_for_aggregate_coverage(self) -> None:
        validate_aggregate_eligibility(
            Path("result.json"),
            {"class_id": "docs", "task_profile": "docs-local", "repetition": 1},
            {"aggregate_coverage_eligible": True, "all_modes_accepted": True},
            accepted_reports(),
            {"docs": "docs-local"},
        )

    def test_quality_regression_blocks_aggregate_coverage(self) -> None:
        reports = accepted_reports()
        reports["full"]["rework_count"] = 1

        with self.assertRaisesRegex(AssertionError, "regresses rework_count"):
            validate_aggregate_eligibility(
                Path("result.json"),
                {
                    "class_id": "docs",
                    "task_profile": "docs-local",
                    "repetition": 1,
                },
                {"aggregate_coverage_eligible": True, "all_modes_accepted": True},
                reports,
                {"docs": "docs-local"},
            )

    def test_task_profile_must_match_declared_class(self) -> None:
        with self.assertRaisesRegex(AssertionError, "task profile drifted"):
            validate_aggregate_eligibility(
                Path("result.json"),
                {"class_id": "docs", "task_profile": "code-local", "repetition": 1},
                {"aggregate_coverage_eligible": True, "all_modes_accepted": True},
                accepted_reports(),
                {"docs": "docs-local"},
            )

    def test_ineligible_result_preserves_narrow_claim_without_aggregate_fields(self) -> None:
        validate_aggregate_eligibility(
            Path("result.json"),
            {},
            {"aggregate_coverage_eligible": False},
            {},
            {"docs": "docs-local"},
        )


if __name__ == "__main__":
    unittest.main()

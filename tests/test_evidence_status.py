from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from render_evidence_status import benchmark_coverage, evidence_state  # noqa: E402


class EvidenceStatusTests(unittest.TestCase):
    def test_broad_coverage_requires_every_class_and_unique_repetitions(self) -> None:
        benchmarks = [
            {
                "task_class_id": task_class,
                "source_contract_digest": "current-contract",
                "repetition": repetition,
                "all_modes_accepted": True,
                "aggregate_coverage_eligible": True,
            }
            for task_class in ["docs", "code"]
            for repetition in [1, 2, 3]
        ]
        benchmarks.append(dict(benchmarks[0]))

        repetitions, complete = benchmark_coverage(
            ["docs", "code"], 3, "current-contract", benchmarks
        )

        self.assertEqual(repetitions, {"docs": 3, "code": 3})
        self.assertTrue(complete)

    def test_wrong_version_or_unaccepted_evidence_does_not_count(self) -> None:
        benchmarks = [
            {
                "task_class_id": "docs",
                "source_contract_digest": "old-contract",
                "repetition": 1,
                "all_modes_accepted": True,
                "aggregate_coverage_eligible": True,
            },
            {
                "task_class_id": "docs",
                "source_contract_digest": "current-contract",
                "repetition": 2,
                "all_modes_accepted": False,
                "aggregate_coverage_eligible": True,
            },
        ]

        repetitions, complete = benchmark_coverage(
            ["docs"], 1, "current-contract", benchmarks
        )

        self.assertEqual(repetitions, {"docs": 0})
        self.assertFalse(complete)

    def test_same_version_with_changed_contract_is_stale(self) -> None:
        self.assertEqual(
            evidence_state("1.0.0", "old-contract", "1.0.0", "current-contract"),
            "same-version-stale-contract",
        )

    def test_matching_contract_is_current(self) -> None:
        self.assertEqual(
            evidence_state("0.9.0", "contract", "1.0.0", "contract"),
            "current-contract",
        )


if __name__ == "__main__":
    unittest.main()

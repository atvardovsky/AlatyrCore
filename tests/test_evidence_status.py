from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from render_evidence_status import benchmark_coverage  # noqa: E402


class EvidenceStatusTests(unittest.TestCase):
    def test_broad_coverage_requires_every_class_and_unique_repetitions(self) -> None:
        benchmarks = [
            {
                "task_class_id": task_class,
                "source_version": "1.0.0",
                "repetition": repetition,
                "all_modes_accepted": True,
                "broad_cost_claim_supported": True,
            }
            for task_class in ["docs", "code"]
            for repetition in [1, 2, 3]
        ]
        benchmarks.append(dict(benchmarks[0]))

        repetitions, complete = benchmark_coverage(
            ["docs", "code"], 3, "1.0.0", benchmarks
        )

        self.assertEqual(repetitions, {"docs": 3, "code": 3})
        self.assertTrue(complete)

    def test_wrong_version_or_unaccepted_evidence_does_not_count(self) -> None:
        benchmarks = [
            {
                "task_class_id": "docs",
                "source_version": "old",
                "repetition": 1,
                "all_modes_accepted": True,
                "broad_cost_claim_supported": True,
            },
            {
                "task_class_id": "docs",
                "source_version": "current",
                "repetition": 2,
                "all_modes_accepted": False,
                "broad_cost_claim_supported": True,
            },
        ]

        repetitions, complete = benchmark_coverage(
            ["docs"], 1, "current", benchmarks
        )

        self.assertEqual(repetitions, {"docs": 0})
        self.assertFalse(complete)


if __name__ == "__main__":
    unittest.main()

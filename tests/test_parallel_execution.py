from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from parallel_execution import child_capacity, run_commands  # noqa: E402


class ParallelExecutionTests(unittest.TestCase):
    def test_invalid_parent_capacity_fails_closed_to_one(self) -> None:
        with patch.dict(os.environ, {"ALATYR_CHILD_CAPACITY": "invalid"}):
            self.assertEqual(child_capacity(default=4), 1)

    def test_results_retain_declaration_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            results = run_commands(
                [
                    ("slow", [sys.executable, "-c", "import time; time.sleep(.05); print('slow')"]),
                    ("fast", [sys.executable, "-c", "print('fast')"]),
                ],
                cwd=Path(directory),
                capacity=2,
            )

        self.assertEqual([result.item_id for result in results], ["slow", "fast"])
        self.assertEqual([result.stdout.strip() for result in results], ["slow", "fast"])
        self.assertTrue(all(result.returncode == 0 for result in results))
        self.assertTrue(all(result.duration_seconds >= 0 for result in results))

    def test_duplicate_item_ids_are_rejected_before_dispatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be unique"):
            run_commands(
                [("same", [sys.executable, "-V"]), ("same", [sys.executable, "-V"])],
                cwd=ROOT,
                capacity=2,
            )


if __name__ == "__main__":
    unittest.main()

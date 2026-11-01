from __future__ import annotations

import os
import sys
import tempfile
import threading
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

    def test_completion_notifications_do_not_wait_for_declaration_order(self) -> None:
        release = threading.Event()
        observed = []
        collector = threading.get_ident()

        def execute(command, **kwargs):
            self.assertEqual(kwargs["env"]["ALATYR_CHILD_CAPACITY"], "1")
            self.assertNotIn("start_new_session", kwargs)
            self.assertNotIn("creationflags", kwargs)
            if command[0] == "slow":
                self.assertTrue(release.wait(5), "fast completion was hidden behind slow work")
            return type("Completed", (), {"returncode": 0, "stdout": command[0], "stderr": ""})()

        def completed(result):
            self.assertEqual(threading.get_ident(), collector)
            observed.append(result.item_id)
            if result.item_id == "fast":
                release.set()

        with patch("parallel_execution.subprocess.run", side_effect=execute):
            results = run_commands([("slow", ["slow"]), ("fast", ["fast"])],
                                   cwd=ROOT, capacity=2, on_complete=completed)
        self.assertEqual(observed, ["fast", "slow"])
        self.assertEqual([result.item_id for result in results], ["slow", "fast"])

    def test_all_results_notify_once_including_failures_and_spawn_errors(self) -> None:
        observed = []

        def execute(command, **kwargs):
            if command[0] == "missing":
                raise OSError("fixture executable missing")
            return type("Completed", (), {"returncode": int(command[0]), "stdout": "", "stderr": ""})()

        for capacity in (1, 2, 8):
            observed.clear()
            with self.subTest(capacity=capacity), patch("parallel_execution.subprocess.run", side_effect=execute):
                results = run_commands([("ok", ["0"]), ("failed", ["7"]), ("spawn", ["missing"])],
                                       cwd=ROOT, capacity=capacity, on_complete=observed.append)
            self.assertCountEqual([result.item_id for result in observed], ["ok", "failed", "spawn"])
            self.assertEqual([result.returncode for result in results], [0, 7, 127])

    def test_observer_and_worker_errors_never_become_successful_commands(self) -> None:
        observed = []
        completed = type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()

        def observer(result):
            observed.append(result.item_id)
            raise OSError("observer failure")

        with patch("parallel_execution.subprocess.run", return_value=completed):
            with self.assertRaisesRegex(OSError, "observer failure"):
                run_commands([("one", ["one"]), ("two", ["two"])], cwd=ROOT,
                             capacity=2, on_complete=observer)
        self.assertCountEqual(observed, ["one", "two"])

        observed.clear()
        def execute(command, **kwargs):
            if command[0] == "bad":
                raise UnicodeError("invalid child output")
            return completed
        with patch("parallel_execution.subprocess.run", side_effect=execute):
            with self.assertRaisesRegex(UnicodeError, "invalid child output"):
                run_commands([("bad", ["bad"]), ("ok", ["ok"])], cwd=ROOT,
                             capacity=2, on_complete=observed.append)
        self.assertEqual([result.item_id for result in observed], ["ok"])

    def test_empty_execution_does_not_notify(self) -> None:
        observed = []
        self.assertEqual(run_commands([], cwd=ROOT, on_complete=observed.append), [])
        self.assertEqual(observed, [])

    def test_ready_batch_order_does_not_change_returns_or_error_precedence(self) -> None:
        import concurrent.futures
        observed = []
        completed = type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        def ready_batch(futures):
            batch = list(futures)
            concurrent.futures.wait(batch)
            return iter(reversed(batch))
        with patch("parallel_execution.subprocess.run", return_value=completed), \
                patch("parallel_execution.concurrent.futures.as_completed", side_effect=ready_batch):
            results = run_commands([("one", ["one"]), ("two", ["two"])], cwd=ROOT,
                                   capacity=2, on_complete=lambda result: observed.append(result.item_id))
            self.assertEqual(observed, ["two", "one"])
            self.assertEqual([result.item_id for result in results], ["one", "two"])
            def rejected(result):
                raise ValueError(result.item_id)
            with self.assertRaisesRegex(ValueError, "^one$"):
                run_commands([("one", ["one"]), ("two", ["two"])], cwd=ROOT,
                             capacity=2, on_complete=rejected)


if __name__ == "__main__":
    unittest.main()

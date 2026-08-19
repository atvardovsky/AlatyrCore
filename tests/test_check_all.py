from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_all import execute_checks, select_checks  # noqa: E402


def check(check_id: str, *dependencies: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "command": [f"tools/{check_id}.py"],
        "depends_on": list(dependencies),
    }


class CheckGraphTests(unittest.TestCase):
    def test_profile_selection_respects_platform_contract(self) -> None:
        checks = [
            {
                **check("portable"),
                "profiles": ["platform"],
                "platforms": ["all"],
            },
            {
                **check("linux-only"),
                "profiles": ["platform"],
                "platforms": ["linux"],
            },
        ]

        selected, _fell_back = select_checks(
            checks, "platform", None, platform="windows"
        )

        self.assertEqual([item["id"] for item in selected], ["portable"])

    def test_dependency_runs_only_after_successful_prerequisite(self) -> None:
        completed: list[str] = []

        def runner(item: dict[str, Any], _baseline: str | None):
            if item["id"] == "dependent":
                self.assertIn("prerequisite", completed)
            completed.append(item["id"])
            return 0, "", "", [item["id"]]

        results, blocked = execute_checks(
            [check("prerequisite"), check("dependent", "prerequisite")],
            None,
            2,
            runner=runner,
        )

        self.assertEqual(set(results), {"prerequisite", "dependent"})
        self.assertEqual(blocked, {})

    def test_failed_prerequisite_blocks_transitive_dependents(self) -> None:
        executed: list[str] = []

        def runner(item: dict[str, Any], _baseline: str | None):
            executed.append(item["id"])
            return (1 if item["id"] == "first" else 0), "", "", [item["id"]]

        results, blocked = execute_checks(
            [check("first"), check("second", "first"), check("third", "second")],
            None,
            3,
            runner=runner,
        )

        self.assertEqual(executed, ["first"])
        self.assertEqual(set(results), {"first"})
        self.assertEqual(blocked["second"], ["first"])
        self.assertEqual(blocked["third"], ["second"])

    def test_independent_checks_remain_runnable_after_other_failure(self) -> None:
        executed: list[str] = []

        def runner(item: dict[str, Any], _baseline: str | None):
            executed.append(item["id"])
            return (1 if item["id"] == "failed" else 0), "", "", [item["id"]]

        results, blocked = execute_checks(
            [check("failed"), check("independent"), check("blocked", "failed")],
            None,
            2,
            runner=runner,
        )

        self.assertEqual(set(executed), {"failed", "independent"})
        self.assertEqual(results["independent"][0], 0)
        self.assertEqual(blocked["blocked"], ["failed"])


if __name__ == "__main__":
    unittest.main()

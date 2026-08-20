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
        "trigger_paths": [f"area/{check_id}/**"],
        "owned_paths": [f"area/{check_id}/**"],
        "always_for_changed": False,
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

    def test_changed_fast_profile_selects_invariants_and_matching_routes(self) -> None:
        checks = [
            {
                **check("invariant"),
                "profiles": ["fast", "full"],
                "platforms": ["all"],
                "always_for_changed": True,
            },
            {
                **check("matched"),
                "profiles": ["fast", "full"],
                "platforms": ["all"],
            },
            {
                **check("unrelated"),
                "profiles": ["fast", "full"],
                "platforms": ["all"],
            },
        ]

        from unittest.mock import patch

        with patch("check_all.git_changed_paths", return_value=["area/matched/file.md"]):
            selected, fell_back = select_checks(
                checks, "fast", "HEAD~1", platform="linux"
            )

        self.assertFalse(fell_back)
        self.assertEqual([item["id"] for item in selected], ["invariant", "matched"])

    def test_trigger_paths_can_be_narrower_than_owned_paths(self) -> None:
        item = {
            **check("broad-owner"),
            "profiles": ["full"],
            "platforms": ["all"],
            "owned_paths": ["area/**"],
            "trigger_paths": ["area/contracts/**"],
        }
        fallback = {
            **check("fallback"),
            "profiles": ["full"],
            "platforms": ["all"],
            "owned_paths": ["**"],
            "trigger_paths": ["**"],
        }

        from unittest.mock import patch

        with patch("check_all.git_changed_paths", return_value=["area/docs/note.md"]):
            selected, _fell_back = select_checks(
                [item, fallback], "fast", "HEAD~1", platform="linux"
            )

        self.assertEqual([entry["id"] for entry in selected], ["fallback"])

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

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_all import (  # noqa: E402
    execute_checks,
    render_report,
    resolve_report_path,
    select_checks,
)
from source_state import snapshot_changes, source_snapshot  # noqa: E402


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

    def test_source_snapshot_detects_changes_to_already_dirty_files(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            path = root / "tracked.txt"
            path.write_text("accepted\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
            path.write_text("dirty before checks\n", encoding="utf-8")
            before = source_snapshot(root)

            path.write_text("changed by checker\n", encoding="utf-8")
            changes = snapshot_changes(before, source_snapshot(root))

            self.assertEqual(changes, ["modified tracked.txt"])

    def test_source_snapshot_detects_non_ignored_created_files(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            before = source_snapshot(root)

            (root / "created.txt").write_text("unexpected\n", encoding="utf-8")

            self.assertEqual(
                snapshot_changes(before, source_snapshot(root)),
                ["created created.txt"],
            )

    def test_machine_report_preserves_exact_failure_evidence(self) -> None:
        selected = [{**check("failed"), "write_scope": "none"}]
        report = render_report(
            profile="full",
            selected=selected,
            results={"failed": (7, "partial output\n", "failure detail\n", ["python", "failed.py"])},
            blocked={},
            source_changes=["modified tracked.txt"],
        )

        self.assertEqual(report["checks"][0]["status"], "failed")
        self.assertEqual(report["checks"][0]["exit_code"], 7)
        self.assertEqual(report["checks"][0]["stderr"], "failure detail\n")
        self.assertFalse(report["source_write_scope"]["preserved"])

    def test_report_output_cannot_bypass_source_write_scope(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / ".gitignore").write_text("tmp/\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "outside the source tree"):
                resolve_report_path(root / "source-check-report.json", root=root)
            self.assertEqual(
                resolve_report_path(root / "tmp" / "source-check-report.json", root=root),
                (root / "tmp" / "source-check-report.json").resolve(),
            )

    def test_report_output_rejects_tracked_file_under_ignored_tmp(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / ".gitignore").write_text("tmp/\n", encoding="utf-8")
            report = root / "tmp" / "report.json"
            report.parent.mkdir()
            report.write_text("tracked\n", encoding="utf-8")
            subprocess.run(["git", "add", "-f", "tmp/report.json"], cwd=root, check=True)

            with self.assertRaisesRegex(ValueError, "tracked source file"):
                resolve_report_path(report, root=root)

    def test_report_output_rejects_unignored_tmp_path(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)

            with self.assertRaisesRegex(ValueError, "ignored by Git"):
                resolve_report_path(root / "tmp" / "report.json", root=root)


if __name__ == "__main__":
    unittest.main()

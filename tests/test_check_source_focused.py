from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import run_focused_source_checks  # noqa: E402


class CheckSourceFocusedTests(unittest.TestCase):
    def test_default_changed_from_prefers_origin_main(self) -> None:
        with patch("run_focused_source_checks.git_ref_exists", return_value=True):
            self.assertEqual(run_focused_source_checks.default_changed_from(), "origin/main")

    def test_default_changed_from_falls_back_to_head(self) -> None:
        with patch("run_focused_source_checks.git_ref_exists", return_value=False):
            self.assertEqual(run_focused_source_checks.default_changed_from(), "HEAD")

    def test_check_all_command_uses_fast_changed_path_profile(self) -> None:
        args = argparse.Namespace(
            changed_from="main",
            from_ref="v0.1.0",
            jobs=2,
            report=Path("tmp/focused.json"),
            list=True,
        )

        baseline, command = run_focused_source_checks.check_all_command(args)

        self.assertEqual(baseline, "main")
        self.assertEqual(
            command,
            [
                sys.executable,
                str(ROOT / "tools" / "check_all.py"),
                "--profile",
                "fast",
                "--changed-from",
                "main",
                "--from-ref",
                "v0.1.0",
                "--jobs",
                "2",
                "--report",
                "tmp/focused.json",
                "--list",
            ],
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.harness_scenarios.common import validator  # noqa: E402


class TargetValidatorLiveScanTests(unittest.TestCase):
    def test_git_inventory_keeps_untracked_and_excludes_ignored_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            (target / ".gitignore").write_text(".ai/.runtime/\n", encoding="utf-8")
            active = target / ".ai/assistant/contour.md"
            active.parent.mkdir(parents=True)
            active.write_text("active\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=target, check=True)
            untracked = target / ".ai/assistant/help.md"
            untracked.write_text("untracked\n", encoding="utf-8")
            ignored = target / ".ai/.runtime/session.md"
            ignored.parent.mkdir(parents=True)
            ignored.write_text("ignored\n", encoding="utf-8")

            scanned = {
                instance.rel(path)
                for instance in [validator(target)]
                for path in instance.scan_text_files()
            }

        self.assertIn(".ai/assistant/contour.md", scanned)
        self.assertIn(".ai/assistant/help.md", scanned)
        self.assertNotIn(".ai/.runtime/session.md", scanned)

    def test_live_scan_excludes_historical_evidence_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            active = target / ".ai/assistant/contour.md"
            active.parent.mkdir(parents=True)
            active.write_text("active\n", encoding="utf-8")
            historical = target / ".ai/assistant/approvals/archive/2026-09/a.md"
            historical.parent.mkdir(parents=True)
            historical.write_text("historical\n", encoding="utf-8")
            instance = validator(target)
            scanned = {
                instance.rel(path)
                for path in instance.scan_live_text_files()
            }

        self.assertIn(".ai/assistant/contour.md", scanned)
        self.assertNotIn(
            ".ai/assistant/approvals/archive/2026-09/a.md", scanned
        )


if __name__ == "__main__":
    unittest.main()

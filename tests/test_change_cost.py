from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from report_change_cost import changed_paths, line_changes, summarize  # noqa: E402


class ChangeCostTests(unittest.TestCase):
    def make_target(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / "src").mkdir()
        (root / "src/example.py").write_text("one\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=root,
            check=True,
        )
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
        return root

    def test_diff_ref_head_does_not_double_count_worktree_lines(self) -> None:
        target = self.make_target()
        (target / "src/example.py").write_text("one\ntwo\n", encoding="utf-8")

        paths = changed_paths(target, "HEAD")
        self.assertEqual(paths, ["src/example.py"])
        changes = line_changes(target, "HEAD", paths or [])
        summary = summarize(paths or [], changes)

        self.assertEqual(changes["src/example.py"], {"added": 1, "deleted": 0})
        self.assertEqual(summary["line_changes"]["product"], 1)

    def test_diff_ref_head_does_not_double_count_staged_lines(self) -> None:
        target = self.make_target()
        (target / "src/example.py").write_text("one\ntwo\n", encoding="utf-8")
        subprocess.run(["git", "add", "src/example.py"], cwd=target, check=True)

        paths = changed_paths(target, "HEAD")
        self.assertEqual(paths, ["src/example.py"])
        changes = line_changes(target, "HEAD", paths or [])

        self.assertEqual(changes["src/example.py"], {"added": 1, "deleted": 0})

    def test_diff_ref_head_still_counts_untracked_lines(self) -> None:
        target = self.make_target()
        (target / "src/new.py").write_text("one\ntwo\n", encoding="utf-8")

        paths = changed_paths(target, "HEAD")
        self.assertEqual(paths, ["src/new.py"])
        changes = line_changes(target, "HEAD", paths or [])

        self.assertEqual(changes["src/new.py"], {"added": 2, "deleted": 0})


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from clean_local_artifacts import collect_candidates, remove_candidate  # noqa: E402


class ArtifactCleanupTests(unittest.TestCase):
    def test_selects_only_entries_whose_newest_content_is_old(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "old-run"
            old.mkdir()
            old_file = old / "report.json"
            old_file.write_text("{}\n", encoding="utf-8")
            recent = root / "recent-run"
            recent.mkdir()
            recent_file = recent / "report.json"
            recent_file.write_text("{}\n", encoding="utf-8")
            os.utime(old, (10, 10))
            os.utime(old_file, (10, 10))
            os.utime(recent, (100, 100))
            os.utime(recent_file, (100, 100))

            candidates = collect_candidates(root, cutoff=50)

            self.assertEqual([candidate.path.name for candidate in candidates], ["old-run"])

    def test_removes_selected_directory_without_touching_sibling(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selected = root / "selected"
            selected.mkdir()
            (selected / "output.txt").write_text("output", encoding="utf-8")
            sibling = root / "keep"
            sibling.mkdir()

            candidate = next(
                item
                for item in collect_candidates(root, cutoff=float("inf"))
                if item.path == selected
            )
            remove_candidate(candidate)

            self.assertFalse(selected.exists())
            self.assertTrue(sibling.exists())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_cross_platform_tools import changed_tree_paths, tree_hashes  # noqa: E402


class CrossPlatformToolTests(unittest.TestCase):
    def test_tree_hashes_ignore_git_metadata_but_detect_project_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            metadata = target / ".git"
            metadata.mkdir()
            index = metadata / "index"
            index.write_bytes(b"before")
            project_file = target / "project.txt"
            project_file.write_text("before\n", encoding="utf-8")

            before = tree_hashes(target)
            index.write_bytes(b"after")

            self.assertEqual(tree_hashes(target), before)

            project_file.write_text("after\n", encoding="utf-8")
            after = tree_hashes(target)

            self.assertEqual(changed_tree_paths(before, after), ["project.txt"])


if __name__ == "__main__":
    unittest.main()

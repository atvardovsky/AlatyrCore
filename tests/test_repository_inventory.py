from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from repository_inventory import RepositoryInventory  # noqa: E402


class RepositoryInventoryTests(unittest.TestCase):
    def test_inventory_includes_nonignored_untracked_files_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
            (root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            (root / "untracked.txt").write_text("untracked\n", encoding="utf-8")
            (root / "ignored").mkdir()
            (root / "ignored" / "large.bin").write_bytes(b"ignored")
            (root / "deleted.txt").write_text("deleted\n", encoding="utf-8")
            (root / "linked.txt").symlink_to("tracked.txt")
            subprocess.run(
                ["git", "add", ".gitignore", "tracked.txt", "deleted.txt", "linked.txt"],
                cwd=root,
                check=True,
            )
            (root / "deleted.txt").unlink()

            inventory = RepositoryInventory.load(root)

            self.assertEqual(
                inventory.paths,
                (".gitignore", "linked.txt", "tracked.txt", "untracked.txt"),
            )
            self.assertEqual(inventory.missing_paths, ("deleted.txt",))
            self.assertEqual(
                {entry.path: entry.kind for entry in inventory.entries}["linked.txt"],
                "symlink",
            )


if __name__ == "__main__":
    unittest.main()

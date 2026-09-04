from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from sparse_overlay import overlay_decision, sparse_overlay  # noqa: E402
from scaffold_target_structure import copy_file  # noqa: E402


class SparseOverlayTests(unittest.TestCase):
    def test_marks_identical_file_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "same.txt"
            path.write_bytes(b"same\n")

            decision = overlay_decision(path, b"same\n")

            self.assertFalse(decision.changed)
            self.assertEqual(decision.current_digest, decision.desired_digest)

    def test_marks_missing_and_different_files_changed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            different = root / "different.txt"
            different.write_bytes(b"before\n")

            decisions = sparse_overlay(
                {
                    different: b"after\n",
                    root / "missing.txt": b"new\n",
                }
            )

            self.assertTrue(all(decision.changed for decision in decisions))
            self.assertIsNone(decisions[1].current_digest)

    def test_projection_does_not_rewrite_identical_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.txt"
            target = root / "target.txt"
            source.write_bytes(b"stable\n")
            target.write_bytes(b"stable\n")
            before = target.stat().st_mtime_ns

            changed = copy_file(source, target, write=True)

            self.assertFalse(changed)
            self.assertEqual(target.stat().st_mtime_ns, before)


if __name__ == "__main__":
    unittest.main()

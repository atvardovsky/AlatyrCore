import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from refresh_source_projections import Stage, prepare, apply, ordered_stages


class SourceProjectionRefreshTests(unittest.TestCase):
    def fixture(self, root):
        (root / "tools").mkdir()
        (root / "input.txt").write_text("new")
        (root / "docs").mkdir()
        (root / "docs/a.txt").write_text("old")
        (root / "docs/b.txt").write_text("old")
        for name, source, output in [("a", "input.txt", "docs/a.txt"), ("b", "docs/a.txt", "docs/b.txt")]:
            (root / "tools" / (name + ".py")).write_text(
                "from pathlib import Path\nimport sys\n"
                f"expected=Path({source!r}).read_bytes()\np=Path({output!r})\n"
                "if '--check' in sys.argv:\n raise SystemExit(0 if p.read_bytes()==expected else 1)\n"
                "p.write_bytes(expected)\n")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], cwd=root, check=True)
        return (Stage("b", ("a",), ("docs/b.txt",), ("b.py",), ("b.py", "--check")),
                Stage("a", (), ("docs/a.txt",), ("a.py",), ("a.py", "--check")))

    def test_dry_run_predicts_dependency_closure_and_second_apply_is_noop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stages = self.fixture(root)
            before, changes = prepare(root, stages)
            self.assertEqual(changes, {"docs/a.txt": b"new", "docs/b.txt": b"new"})
            self.assertEqual((root / "docs/a.txt").read_text(), "old")
            apply(root, before, changes, stages)
            modified = (root / "docs/a.txt").stat().st_mtime_ns
            next_before, next_changes = prepare(root, stages)
            self.assertEqual(next_changes, {})
            apply(root, next_before, next_changes, stages)
            self.assertEqual((root / "docs/a.txt").stat().st_mtime_ns, modified)

    def test_concurrent_source_change_prevents_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stages = self.fixture(root)
            before, changes = prepare(root, stages)
            (root / "input.txt").write_text("concurrent")
            with self.assertRaisesRegex(ValueError, "source changed"):
                apply(root, before, changes, stages)
            self.assertEqual((root / "docs/a.txt").read_text(), "old")

    def test_unowned_generator_writes_are_not_applied(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stages = self.fixture(root)
            stages = (Stage("a", (), ("docs/not-a.txt",), ("a.py",), ("a.py", "--check")),)
            with self.assertRaisesRegex(ValueError, "unique declared owner"):
                prepare(root, stages)
            self.assertEqual((root / "docs/a.txt").read_text(), "old")

    def test_cycles_and_duplicate_output_owners_fail(self):
        for stages in [
            (Stage("a", ("a",), ("x",), ("a.py",), ("a.py",)),),
            (Stage("a", (), ("x",), ("a.py",), ("a.py",)), Stage("b", (), ("x",), ("b.py",), ("b.py",)))]:
            with self.assertRaises(ValueError): ordered_stages(stages)

    def test_input_mutation_during_apply_is_not_accepted(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stages = self.fixture(root)
            before, changes = prepare(root, stages)
            original = os.replace
            def concurrent(source, destination):
                original(source, destination)
                (root / "input.txt").write_text("concurrent owner edit")
            with patch("refresh_source_projections.os.replace", side_effect=concurrent):
                with self.assertRaisesRegex(ValueError, "inputs changed during refresh"):
                    apply(root, before, changes, stages)
            self.assertEqual((root / "input.txt").read_text(), "concurrent owner edit")

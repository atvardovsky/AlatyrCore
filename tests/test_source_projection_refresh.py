import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from refresh_source_projections import STAGES, Stage, prepare, apply, ordered_stages


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

    def test_current_stage_uses_its_checker_instead_of_rewriting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "docs/a.txt").write_text("new")
            (root / "tools/fail.py").write_text("raise SystemExit('must not run')\n")
            stage = Stage("a", (), ("docs/a.txt",), ("fail.py",), ("a.py", "--check"), preserve_current=True)
            _before, changes = prepare(root, (stage,))
            self.assertEqual(changes, {})

    def test_preserved_stage_still_repairs_stale_content_and_requires_final_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            stage = Stage("a", (), ("docs/a.txt",), ("a.py",), ("a.py", "--check"), preserve_current=True)
            _before, changes = prepare(root, (stage,))
            self.assertEqual(changes, {"docs/a.txt": b"new"})
            (root / "tools/fail.py").write_text("raise SystemExit('invalid canonical state')\n")
            stage = Stage("a", (), ("docs/a.txt",), ("a.py",), ("fail.py",), preserve_current=True)
            with self.assertRaisesRegex(ValueError, "invalid canonical state"):
                prepare(root, (stage,))
            self.assertEqual((root / "docs/a.txt").read_text(), "old")

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


class CommittedSourceProjectionRefreshTests(unittest.TestCase):
    def command(self, root, *arguments):
        return subprocess.run(
            [sys.executable, str(root / "tools/alatyr.py"), "refresh-source", *arguments],
            cwd=root, capture_output=True, text=True, timeout=120,
        )

    def commit(self, root):
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
             "commit", "--allow-empty", "-qm", "refresh regression fixture"],
            cwd=root, check=True, capture_output=True,
        )

    def assert_policy_and_provenance_drift(self, root):
        stage = replace(next(stage for stage in STAGES if stage.name == "support"), dependencies=())
        state_path = "templates/target/.ai/support-state.json"
        policy_path = "templates/target/.ai/project/support-policy.json"
        for kind, relative in (("policy", policy_path), ("provenance", state_path)):
            with self.subTest(drift=kind):
                path = root / relative
                original = path.read_bytes()
                value = json.loads(original)
                if kind == "policy":
                    value["exclusions"][0]["reason"] += " (regression change)"
                else:
                    value["generated_by"]["template_version"] = "outdated"
                mutated = (json.dumps(value, indent=2) + "\n").encode("utf-8")
                path.write_bytes(mutated)
                try:
                    _before, changes = prepare(root, (stage,))
                    self.assertIn(state_path, changes)
                    self.assertEqual(path.read_bytes(), mutated)
                finally:
                    path.write_bytes(original)

    def test_real_cli_preserves_current_state_after_commit_and_detects_managed_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            subprocess.run(
                ["git", "-c", "core.autocrlf=false", "clone", "--shared", "--quiet", str(ROOT), str(root)],
                check=True, capture_output=True,
            )
            shutil.copyfile(ROOT / "tools/refresh_source_projections.py", root / "tools/refresh_source_projections.py")
            generated = self.command(root, "--write")
            self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
            self.commit(root)
            self.assertEqual(subprocess.check_output(["git", "status", "--short"], cwd=root), b"")
            preserved = {
                path: ((root / path).read_bytes(), (root / path).stat().st_mtime_ns)
                for path in ("templates/target/.ai/support-state.json", "conformance/evidence-status.json")
            }
            for mode in ("--check", "--write"):
                with self.subTest(mode=mode):
                    result = self.command(root, mode)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(json.loads(result.stdout)["changed_paths"], [])
                    for path, expected in preserved.items():
                        self.assertEqual(((root / path).read_bytes(), (root / path).stat().st_mtime_ns), expected)
            self.assertEqual(subprocess.check_output(["git", "status", "--short"], cwd=root), b"")

            managed = root / "templates/target/.ai/assistant/flows/architecture-assistance.flow.md"
            managed.write_bytes(managed.read_bytes() + b"\n<!-- Genuine managed-content regression change. -->\n")
            dirty_before = subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=root)
            drift = self.command(root, "--check")
            self.assertEqual(drift.returncode, 1, drift.stdout + drift.stderr)
            changed = json.loads(drift.stdout)["changed_paths"]
            self.assertIn("templates/target/.ai/support-state.json", changed)
            self.assertIn("conformance/evidence-status.json", changed)
            self.assertEqual(subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=root), dirty_before)
            repaired = self.command(root, "--write")
            self.assertEqual(repaired.returncode, 0, repaired.stdout + repaired.stderr)
            self.commit(root)
            result = self.command(root, "--check")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["changed_paths"], [])
            self.assert_policy_and_provenance_drift(root)

import json
import os
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
from source_state import source_snapshot


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
        return (Stage("b", ("a",), ("docs/b.txt",), ("b.py",), ("b.py", "--check"), check_first=True),
                Stage("a", (), ("docs/a.txt",), ("a.py",), ("a.py", "--check"), check_first=True))

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

    def test_check_first_is_explicit_and_provenance_normalizers_keep_generating(self):
        self.assertFalse(Stage("custom", (), ("x",), ("render.py",), ("check.py",)).preserve_current)
        for stage in STAGES:
            if stage.name in {"entry", "bootstrap"}:
                self.assertFalse(stage.preserve_current)
                self.assertFalse(stage.check_first)

    def test_custom_stage_does_not_skip_rendering_from_an_incomplete_checker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "tools/noop.py").write_text("raise SystemExit(0)\n")
            stage = Stage("a", (), ("docs/a.txt",), ("a.py",), ("noop.py",))
            self.assertEqual(prepare(root, (stage,))[1], {"docs/a.txt": b"new"})

    def test_check_reuse_matches_fresh_checks_and_is_invalidated_by_upstream_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stages = self.fixture(root)
            optimized = prepare(root, stages)
            canonical_stages = tuple(replace(stage, check_first=False) for stage in stages)
            canonical = prepare(root, canonical_stages, reuse_checks=False)
            self.assertEqual(optimized, canonical)
            apply(root, *optimized, stages)
            import refresh_source_projections as refresh
            with patch("refresh_source_projections._run", wraps=refresh._run) as run:
                self.assertEqual(prepare(root, stages)[1], {})
            self.assertEqual(run.call_count, len(stages))
            (root / "input.txt").write_text("changed upstream")
            self.assertEqual(prepare(root, stages)[1], prepare(root, canonical_stages, reuse_checks=False)[1])

    def test_checker_mutation_is_rejected_even_when_it_exits_successfully(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "tools/mutate.py").write_text("from pathlib import Path\nPath('input.txt').write_text('tampered')\n")
            stage = Stage("a", (), ("docs/a.txt",), ("a.py",), ("mutate.py",))
            with self.assertRaisesRegex(ValueError, "checker.*modified"):
                prepare(root, (stage,))
            self.assertEqual((root / "input.txt").read_text(), "new")

    def test_renderer_index_change_invalidates_previously_passed_check(self):
        import refresh_source_projections as refresh
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stages = self.fixture(root)
            (root / "docs/a.txt").write_text("new")
            (root / "tools/index.py").write_text(
                "import subprocess\nsubprocess.run(['git','update-index','--assume-unchanged','input.txt'],check=True)\n")
            (root / "tools/noop.py").write_text("raise SystemExit(0)\n")
            stages = (stages[1], Stage("index", ("a",), (), ("index.py",), ("noop.py",)))
            index_before = subprocess.check_output(["git", "ls-files", "-v", "input.txt"], cwd=root)
            with patch("refresh_source_projections._run", wraps=refresh._run) as run:
                self.assertEqual(prepare(root, stages)[1], {})
            self.assertEqual(sum(call.args[1] == ("a.py", "--check") for call in run.call_args_list), 2)
            self.assertEqual(subprocess.check_output(["git", "ls-files", "-v", "input.txt"], cwd=root), index_before)

    @unittest.skipIf(os.name == "nt", "executable-mode mutation is POSIX-specific")
    def test_checker_permission_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "tools/mode.py").write_text("from pathlib import Path\np=Path('input.txt')\np.chmod(p.stat().st_mode ^ 0o100)\n")
            stage = Stage("a", (), ("docs/a.txt",), ("a.py",), ("mode.py",))
            mode_before = (root / "input.txt").stat().st_mode
            with self.assertRaisesRegex(ValueError, "checker.*modified"):
                prepare(root, (stage,))
            self.assertEqual((root / "input.txt").stat().st_mode, mode_before)

    def test_checker_git_ref_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "tools/refs.py").write_text("import subprocess\nsubprocess.run(['git','update-ref','refs/alatyr-fixture/checker','HEAD'],check=True)\n")
            stage = Stage("a", (), ("docs/a.txt",), ("a.py",), ("refs.py",))
            with self.assertRaisesRegex(ValueError, "checker.*modified"):
                prepare(root, (stage,))

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
        for name, relative in (("entry", "templates/target/.ai/assistant/entry-packet.json"),
                               ("bootstrap", "templates/target/.ai/assistant/bootstrap-integrity.json")):
            with self.subTest(provenance=name):
                stage = replace(next(stage for stage in STAGES if stage.name == name), dependencies=())
                path = root / relative
                original = path.read_bytes()
                value = json.loads(original)
                value["generated_by"]["template_version"] = "outdated"
                mutated = json.dumps(value).encode("utf-8")
                path.write_bytes(mutated)
                try:
                    _before, changes = prepare(root, (stage,))
                    self.assertIn(relative, changes)
                    self.assertNotEqual(json.loads(changes[relative])["generated_by"]["template_version"], "outdated")
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
            # Exercise the current source tree, including newly authored helpers.
            for name, entry in source_snapshot(ROOT).items():
                destination = root / name
                if entry.kind == "missing":
                    destination.unlink(missing_ok=True)
                elif entry.kind == "file":
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / name, destination)
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

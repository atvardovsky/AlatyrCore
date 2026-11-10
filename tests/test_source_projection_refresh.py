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
from refresh_source_projections import STAGES, Stage, prepare, apply, ordered_stages, mirror_snapshot, stage_input_digest
from source_state import source_snapshot


class SourceProjectionRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.fixture_seed = Path(directory.name)
        cls.initialize_fixture(cls.fixture_seed)

    @staticmethod
    def initialize_fixture(root):
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

    def fixture(self, root):
        shutil.copytree(self.fixture_seed, root, dirs_exist_ok=True)
        return (Stage("b", ("a",), ("docs/b.txt",), ("b.py",), ("b.py", "--check"), check_first=True),
                Stage("a", (), ("docs/a.txt",), ("a.py",), ("a.py", "--check"), check_first=True))

    def test_seed_copies_do_not_share_content_modes_index_or_refs(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / "first", Path(directory) / "second"
            self.fixture(first)
            self.fixture(second)
            before = source_snapshot(self.fixture_seed)
            self.assertEqual(source_snapshot(first), before)
            self.assertEqual(source_snapshot(second), before)
            args = ["git", "for-each-ref", "--format=%(refname) %(objectname)"]
            refs = subprocess.check_output(args, cwd=self.fixture_seed)
            flags = subprocess.check_output(["git", "ls-files", "-v"], cwd=self.fixture_seed)
            (first / "input.txt").write_text("isolated mutation")
            if os.name != "nt":
                (first / "input.txt").chmod((first / "input.txt").stat().st_mode ^ 0o100)
            subprocess.run(["git", "update-index", "--assume-unchanged", "input.txt"], cwd=first, check=True)
            subprocess.run(["git", "update-ref", "refs/fixture/isolated", "HEAD"], cwd=first, check=True)
            for root in (self.fixture_seed, second):
                self.assertEqual(source_snapshot(root), before)
                self.assertEqual(subprocess.check_output(args, cwd=root), refs)
                self.assertEqual(subprocess.check_output(["git", "ls-files", "-v"], cwd=root), flags)

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
            args = ["git", "for-each-ref", "--format=%(refname) %(objectname)"]
            before = subprocess.check_output(args, cwd=root)
            with self.assertRaisesRegex(ValueError, "checker.*modified"):
                prepare(root, (stage,))
            self.assertEqual(subprocess.check_output(args, cwd=root), before)

    def test_renderer_ref_writes_are_isolated_and_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "tools/refs.py").write_text("import subprocess\nsubprocess.run(['git','update-ref','refs/fixture/renderer','HEAD'],check=True)\n")
            before = subprocess.check_output(["git", "show-ref"], cwd=root)
            stage = Stage("refs", (), (), ("refs.py",), ("a.py", "--check"))
            with self.assertRaises(ValueError):
                prepare(root, (stage,))
            self.assertEqual(subprocess.check_output(["git", "show-ref"], cwd=root), before)

    def test_checker_head_and_config_writes_leave_caller_metadata_unchanged(self):
        for arguments in (["symbolic-ref", "HEAD", "refs/heads/other"],
                          ["config", "alatyr.fixture", "changed"]):
            with self.subTest(arguments=arguments), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root)
                before = {name: (root / ".git" / name).read_bytes() for name in ("HEAD", "config", "index")}
                (root / "tools/control.py").write_text(
                    "import subprocess\nsubprocess.run(" + repr(["git", *arguments]) + ",check=True)\n")
                stage = Stage("a", (), ("docs/a.txt",), ("a.py",), ("control.py",))
                with self.assertRaisesRegex(ValueError, "checker.*modified"):
                    prepare(root, (stage,))
                self.assertEqual({name: (root / ".git" / name).read_bytes() for name in before}, before)

    def test_linked_worktree_keeps_its_own_head_and_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root, linked = Path(directory) / "source", Path(directory) / "linked"
            stages = self.fixture(root)
            subprocess.run(["git", "worktree", "add", "--detach", "-q", str(linked), "HEAD"],
                           cwd=root, check=True, capture_output=True)
            before, changes = prepare(linked, stages)
            self.assertEqual(changes, {"docs/a.txt": b"new", "docs/b.txt": b"new"})
            self.assertEqual(before.revision, subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=linked, text=True).strip())
            self.assertEqual((root / "docs/a.txt").read_bytes(), b"old")

    def test_global_config_is_copied_but_writes_are_private_and_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root, home = Path(directory) / "source", Path(directory) / "home"
            self.fixture(root)
            home.mkdir()
            config = home / ".gitconfig"
            config.write_text("[alatyr]\n fixture = original\n", encoding="utf-8")
            (root / "tools/global.py").write_text(
                "import subprocess\n"
                "assert subprocess.check_output(['git','config','--global','alatyr.fixture'],text=True).strip()=='original'\n"
                "subprocess.run(['git','config','--global','alatyr.fixture','changed'],check=True)\n")
            stage = Stage("a", (), ("docs/a.txt",), ("a.py",), ("global.py",))
            before = config.read_bytes()
            with patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(home),
                                         "XDG_CONFIG_HOME": str(home / ".config"),
                                         "GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"}):
                with self.assertRaisesRegex(ValueError, "checker.*modified"):
                    prepare(root, (stage,))
            self.assertEqual(config.read_bytes(), before)

    def test_split_index_is_materialized_without_changing_caller(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stages = self.fixture(root)
            subprocess.run(["git", "update-index", "--split-index"], cwd=root, check=True)
            paths = [root / ".git/index", *sorted((root / ".git").glob("sharedindex.*"))]
            self.assertGreater(len(paths), 1)
            before = {path.name: path.read_bytes() for path in paths}
            self.assertEqual(prepare(root, stages)[1], {"docs/a.txt": b"new", "docs/b.txt": b"new"})
            self.assertEqual({path.name: path.read_bytes() for path in paths}, before)

    def test_explicit_global_config_selection_matches_host_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root, home = Path(directory) / "source", Path(directory) / "home"
            stages = self.fixture(root)
            home.mkdir()
            (home / ".gitconfig").write_text("[alatyr]\n fixture = home-value\n")
            override = Path(directory) / "custom.gitconfig"
            override.write_text("[alatyr]\n fixture = explicit-value\n")
            settings = {"HOME": str(home), "USERPROFILE": str(home),
                        "XDG_CONFIG_HOME": str(home / ".config"),
                        "GIT_CONFIG_GLOBAL": str(override), "GIT_CONFIG_NOSYSTEM": "1"}
            with patch.dict(os.environ, settings):
                expected = subprocess.check_output(["git", "config", "--global", "alatyr.fixture"],
                                                   cwd=root, text=True).strip()
                (root / "tools/config.py").write_text(
                    "import subprocess\nassert subprocess.check_output(['git','config','--global','alatyr.fixture'],text=True).strip()=="
                    + repr(expected) + "\n")
                stage = Stage("config", (), (), ("config.py",), ("config.py",))
                with patch("refresh_source_projections.subprocess.check_output", wraps=subprocess.check_output) as output:
                    self.assertEqual(prepare(root, (stage,))[1], {})
                capture = next(call for call in output.call_args_list if call.args[0][:3] == ["git", "config", "--null"])
                self.assertEqual(capture.kwargs["env"]["GIT_CONFIG_GLOBAL"], str(override))
            self.assertIn("explicit-value", override.read_text())

    def test_checker_cannot_hide_mutations_in_pycache_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            cache = root / "docs/__pycache__"
            cache.mkdir()
            (cache / "owner.txt").write_text("original")
            (root / "tools/cache.py").write_text(
                "from pathlib import Path\nPath('docs/__pycache__/owner.txt').write_text('changed')\n")
            stage = Stage("a", (), ("docs/a.txt",), ("a.py",), ("cache.py",))
            with self.assertRaisesRegex(ValueError, "checker.*modified"):
                prepare(root, (stage,))
            self.assertEqual((cache / "owner.txt").read_text(), "original")

    @unittest.skipIf(os.name == "nt", "symlink privileges are host-specific")
    def test_pycache_symlink_is_rejected_by_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / "docs/__pycache__").symlink_to(root / "docs", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symbolic links"):
                mirror_snapshot(root)

    @unittest.skipIf(os.name == "nt", "POSIX executable modes")
    def test_new_output_is_validated_with_the_mode_that_apply_installs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "tools/new.py").write_text(
                "from pathlib import Path\nimport sys\np=Path('docs/new.txt')\n"
                "if '--check' in sys.argv:\n raise SystemExit(0 if p.stat().st_mode & 0o777 == 0o644 else 1)\n"
                "p.write_text('new')\np.chmod(0o755)\n")
            stage = Stage("new", (), ("docs/new.txt",), ("new.py",), ("new.py", "--check"))
            before, changes = prepare(root, (stage,))
            apply(root, before, changes, (stage,))
            self.assertEqual((root / "docs/new.txt").stat().st_mode & 0o777, 0o644)
            (root / "docs/new.txt").unlink()
            path = root / "tools/new.py"
            path.write_text(path.read_text().replace("== 0o644", "== 0o755"))
            with self.assertRaisesRegex(ValueError, "projection new.py failed"):
                prepare(root, (stage,))

    def test_mirror_collector_matches_independent_bytes_and_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            observed = mirror_snapshot(root / "docs")
            paths = [path for path in (root / "docs").rglob("*") if path.is_file()]
            self.assertEqual(observed.files, {path.relative_to(root / "docs").as_posix(): path.read_bytes() for path in paths})
            self.assertEqual(observed.modes, {path.relative_to(root / "docs").as_posix(): path.stat().st_mode & 0o7777 for path in paths})
            path = root / "docs/a.txt"
            old = path.stat()
            path.write_bytes(b"NEW")
            os.utime(path, ns=(old.st_atime_ns, old.st_mtime_ns))
            self.assertNotEqual(mirror_snapshot(root / "docs").files, observed.files)

    def test_narrow_stage_keys_bind_inputs_outputs_implementation_and_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = {"framework/rule-registry.json", "tools/render_rule_registry_docs.py",
                     "tools/render_target_validator_findings.py", "tools/refresh_source_projections.py",
                     "tools/validate_target_adapter.py", "tools/project_knowledge.py",
                     "tools/target_adapter_validation/one.py", "unrelated.md"}
            names.update(path for stage in STAGES if stage.name in {"rules", "findings"} for path in stage.outputs)
            for name in names:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((Path(__file__).resolve().parents[1] / name).read_bytes()
                                 if name in {"tools/render_rule_registry_docs.py", "tools/render_target_validator_findings.py"}
                                 else b"original")
            for stage in (item for item in STAGES if item.name in {"rules", "findings"}):
                def key():
                    return stage_input_digest(stage, root, mirror_snapshot(root).files)
                before = key()
                self.assertIsNotNone(before)
                (root / "unrelated.md").write_bytes(b"changed")
                self.assertEqual(key(), before)
                for name in (stage.outputs[0], "tools/" + stage.command[0], "tools/refresh_source_projections.py",
                             "framework/rule-registry.json" if stage.name == "rules" else "tools/validate_target_adapter.py"):
                    path = root / name
                    prior = path.read_bytes()
                    path.write_bytes(b"changed")
                    self.assertNotEqual(key(), before, name)
                    path.write_bytes(prior)
                if stage.name == "findings":
                    extra = root / "tools/target_adapter_validation/new.py"
                    extra.write_bytes(b"")
                    self.assertNotEqual(key(), before)
                    extra.unlink()
                    self.assertEqual(key(), before)
                    extra.mkdir()
                    self.assertNotEqual(key(), before)
                    extra.rmdir()
                self.assertIsNone(stage_input_digest(replace(stage, command=("unknown.py",)), root, {}))

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

    @unittest.skipIf(os.name == "nt", "POSIX executable modes")
    def test_concurrent_output_mode_change_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stages = self.fixture(root)
            before, changes = prepare(root, stages)
            original = os.replace
            def concurrent(source, destination):
                original(source, destination)
                destination.chmod(0o755)
            with patch("refresh_source_projections.os.replace", side_effect=concurrent):
                with self.assertRaisesRegex(ValueError, "outputs changed during refresh"):
                    apply(root, before, changes, stages)


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

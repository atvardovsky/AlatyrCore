from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_change_packages import changed_index_validator, git
from framework_source_binding import baseline_framework, materialize_git_subtree, resolve_installed_commit
from plan_target_upgrade import previous_source_commit
from target_adapter_validation.framework_baseline import source_pack_projection


class FrameworkSourceBindingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "source"
        self.source.mkdir()
        git(self.source, "init", "-q")
        git(self.source, "config", "user.name", "Fixture")
        git(self.source, "config", "user.email", "fixture@example.invalid")
        (self.source / "VERSION").write_text("1.2.3\n")
        (self.source / "framework").mkdir()
        (self.source / "framework/rule.md").write_bytes(b"accepted baseline\n")
        git(self.source, "add", ".")
        git(self.source, "commit", "-qm", "initial")
        self.initial = git(self.source, "rev-parse", "HEAD")
        (self.source / "framework/rule.md").write_bytes(b"accepted patch with same version\n")
        git(self.source, "commit", "-am", "baseline patch", "-q")
        self.pin = git(self.source, "rev-parse", "HEAD")
        self.target = self.root / "target"
        (self.target / ".ai").mkdir(parents=True)
        shutil.copytree(self.source / "framework", self.target / ".ai/framework")
        (self.target / ".ai/alatyr.yaml").write_text(f"framework:\n  version: 1.2.3\n  source_commit: {self.pin}\n")

    def test_routine_check_uses_pin_after_source_advances_but_candidate_sees_drift(self):
        (self.source / "framework/rule.md").write_bytes(b"candidate change\n")
        git(self.source, "commit", "-am", "candidate", "-q")
        for role, expected in (("installed", False), ("candidate", True)):
            checked = changed_index_validator(self.target)
            checked.framework_source = self.source
            checked.framework_source_role = role
            checked.check_framework_baseline()
            self.assertEqual(checked.framework_drift_detected, expected, checked.findings)
        self.assertEqual(previous_source_commit(self.source, self.target, "1.2.3"), self.pin)

    def test_clean_matching_pin_reuses_checkout_without_churn(self):
        with baseline_framework(self.source, pin=self.pin, version="1.2.3") as path:
            self.assertEqual(path, self.source / "framework")

    def test_candidate_role_cannot_establish_acceptance_even_without_source(self):
        checked = changed_index_validator(self.target)
        checked.framework_source = None
        checked.framework_source_role = "candidate"
        checked.validation_phase = "acceptance"
        checked.check_framework_baseline()
        self.assertIn("FRAMEWORK_CANDIDATE_NOT_ACCEPTANCE", {item.code for item in checked.findings if item.level == "error"})

    def test_dirty_checkout_cannot_replace_pinned_content(self):
        (self.source / "framework/rule.md").write_bytes(b"uncommitted candidate\n")
        with baseline_framework(self.source, pin=self.pin, version="1.2.3") as path:
            self.assertEqual((path / "rule.md").read_text(), "accepted patch with same version\n")
        self.assertEqual((self.source / "framework/rule.md").read_text(), "uncommitted candidate\n")

    def test_dirty_version_metadata_cannot_change_pinned_pack_inputs(self):
        (self.source / "VERSION").write_bytes(b"9.9.9\n")
        with baseline_framework(self.source, pin=self.pin, version="1.2.3") as path:
            self.assertNotEqual(path, self.source / "framework")
            self.assertEqual((path.parent / "VERSION").read_text().strip(), "1.2.3")

    def test_selective_packs_keep_pinned_version_and_projection_inputs(self):
        source = self.root / "pack-source"
        source.mkdir()
        shutil.copytree(ROOT / "framework", source / "framework")
        for name in ("VERSION", "ADAPTER_SCHEMA_VERSION", "TEMPLATE_VERSION"):
            shutil.copy2(ROOT / name, source / name)
        git(source, "init", "-q")
        git(source, "config", "user.name", "Fixture")
        git(source, "config", "user.email", "fixture@example.invalid")
        git(source, "add", ".")
        git(source, "commit", "-qm", "pack baseline")
        pin = git(source, "rev-parse", "HEAD")
        version = (source / "VERSION").read_text().strip()
        targets = []
        for pack in ("kernel", "core", "standard"):
            target = self.root / pack
            _, _, contents = source_pack_projection(source / "framework", pack)
            for path, value in contents.items():
                output = target / ".ai/framework" / path
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(value)
            (target / ".ai/alatyr.yaml").write_text(f"framework:\n  version: {version}\n  source_commit: {pin}\n  pack: {pack}\n")
            targets.append(target)
        (source / "framework/context-profiles.md").write_bytes(b"candidate policy\n")
        git(source, "commit", "-am", "candidate", "-q")
        for target in targets:
            checked = changed_index_validator(target)
            checked.framework_source = source
            checked.check_framework_baseline()
            self.assertFalse(checked.framework_drift_detected, checked.findings)
            self.assertFalse(any(item.level == "error" for item in checked.findings), checked.findings)

    def test_missing_malformed_and_version_conflicting_pins_fail_closed(self):
        for pin, version in (("f" * 40, "1.2.3"), ("HEAD", "1.2.3"), (self.pin, "9.0.0")):
            with self.subTest(pin=pin, version=version), self.assertRaises(ValueError):
                resolve_installed_commit(self.source, pin, version)
        for role in ({}, [], None, True, 4, "unknown"):
            with self.subTest(role=role), self.assertRaises(ValueError):
                with baseline_framework(self.source, pin=self.pin, version="1.2.3", role=role):
                    self.fail("malformed source roles must not be accepted")

    def test_explicit_invalid_pin_does_not_use_version_heuristic(self):
        (self.target / ".ai/alatyr.yaml").write_text("framework:\n  version: 1.2.3\n  source_commit: unknown\n")
        # Explicit unresolved values must not silently become a different commit.
        with self.assertRaises(ValueError):
            previous_source_commit(self.source, self.target, "1.2.3")

    def test_materializer_rejects_link_blobs_and_path_escape(self):
        if os.name != "nt":
            (self.source / "framework/link.md").symlink_to("rule.md")
            git(self.source, "add", ".")
            git(self.source, "commit", "-qm", "link")
            self.assertFalse(materialize_git_subtree(self.source, "HEAD", "framework", self.root / "output"))
            self.assertFalse((self.root / "output").exists())
            commit = git(self.source, "rev-parse", "HEAD")
            with self.assertRaisesRegex(ValueError, "regular Git blobs"):
                with baseline_framework(self.source, pin=commit, version="1.2.3"):
                    self.fail("clean checkout must not bypass regular-blob checks")
        self.assertFalse(materialize_git_subtree(self.source, self.pin, "../framework", self.root / "output"))

    def test_materializer_batches_exact_blobs_without_archive_transformations(self):
        for number in range(20):
            (self.source / "framework" / f"file-{number}.md").write_bytes(f"exact content {number}\n".encode())
        (self.source / ".gitattributes").write_bytes(b"framework/* export-ignore\n")
        git(self.source, "add", ".")
        git(self.source, "commit", "-qm", "batch fixture")
        destination = self.root / "batch"
        original = subprocess.run
        with patch("framework_source_binding.subprocess.run", wraps=original) as calls:
            self.assertTrue(materialize_git_subtree(self.source, "HEAD", "framework", destination))
        batches = [call for call in calls.call_args_list if call.args[0][:3] == ["git", "cat-file", "--batch"]]
        self.assertEqual(len(batches), 1)
        self.assertEqual(len(list(destination.glob("*.md"))), 21)
        for number in range(20):
            self.assertEqual((destination / f"file-{number}.md").read_bytes(), f"exact content {number}\n".encode())


if __name__ == "__main__":
    unittest.main()

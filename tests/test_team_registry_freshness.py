"""Opt-in registry freshness binds source bytes, not arbitrary HEAD movement."""

from __future__ import annotations

import copy
import errno
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.capability import CapabilityValidationContext  # noqa: E402
from target_adapter_validation.context import TargetRepositoryView  # noqa: E402
from target_adapter_validation.team_collaboration import _check_registry_freshness  # noqa: E402
from target_validation_support import GitEvidenceView  # noqa: E402


REGISTRY = ".ai/assistant/team/work-registry.json"
SOURCES = [
    ".ai/project/team-policy.json",
    ".ai/project/team-operating-model.md",
    ".ai/assistant/team/backend-contract.json",
    ".ai/assistant/team/active-work-index.json",
    ".ai/assistant/team/task-record-template.json",
    ".ai/assistant/team/tasks/task-1.json",
]


class Findings:
    def __init__(self):
        self.items = []

    def error(self, code, message, path=None):
        self.items.append(("error", code, message, path))

    def warn(self, code, message, path=None):
        self.items.append(("warning", code, message, path))

    def info(self, code, message, path=None):
        self.items.append(("info", code, message, path))


class TeamRegistryFreshnessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="alatyr-team-freshness-")
        self.addCleanup(temporary.cleanup)
        self.target = Path(temporary.name).resolve()
        self.git("init", "-q")
        self.git("config", "user.name", "Alatyr Tests")
        self.git("config", "user.email", "tests@example.invalid")
        for path in SOURCES:
            self.write(path, path + "\n")
        self.commit("Capture team sources")
        self.revision = self.git("rev-parse", "HEAD")
        self.registry = {
            "schema_version": 2,
            "evidence_revision": self.revision,
            "evidence_binding": {
                "schema_version": 1,
                "inputs": [
                    {"path": path, "sha256": hashlib.sha256((self.target / path).read_bytes()).hexdigest()}
                    for path in SOURCES
                ],
            },
        }

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.target, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout.decode("utf-8").strip()

    def write(self, path, value):
        selected = self.target / path
        selected.parent.mkdir(parents=True, exist_ok=True)
        selected.write_text(value, encoding="utf-8")

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "-qm", message)

    def check(self, *, required=None, target=None, registry=None):
        target = target or self.target
        filesystem = TargetRepositoryView(target)
        self.findings = Findings()
        self.evidence = GitEvidenceView(target)
        context = CapabilityValidationContext(
            filesystem=filesystem, git=self.evidence, findings=self.findings,
            allow_placeholders=False,
            resolve_target_path=lambda value: target / value,
            read_target_text=filesystem.read_text,
            load_target_json_object=lambda *_: None,
            check_target_reference=lambda *_: None,
            check_action_modes=lambda *_: None,
            relative_target_path=lambda value: value.relative_to(target).as_posix(),
            module_enabled=lambda *_: True,
        )
        _check_registry_freshness(
            context, registry if registry is not None else self.registry,
            REGISTRY, SOURCES if required is None else required,
        )
        return self.findings.items

    def assert_error(self, **kwargs):
        findings = self.check(**kwargs)
        self.assertTrue(any(row[0] == "error" for row in findings), findings)

    def assert_stale(self):
        findings = self.check()
        self.assertTrue(any(row[:2] == ("warning", "TEAM_REGISTRY_REVISION_STALE") for row in findings), findings)

    def test_legacy_schema_two_retains_revision_comparison(self):
        del self.registry["evidence_binding"]
        self.assertEqual(self.check(), [])
        self.write("unrelated.txt", "Unrelated change\n")
        self.commit("Advance unrelated HEAD")
        self.assert_stale()

    def test_legacy_unavailable_revision_retains_no_freshness_claim(self):
        del self.registry["evidence_binding"]
        for value in ("unavailable", "none", "", "{REVISION}", None):
            with self.subTest(value=value):
                self.registry["evidence_revision"] = value
                self.assertEqual(self.check(), [])

    def test_valid_binding_at_reviewed_head(self):
        self.assertEqual(self.check(), [])

    def test_unrelated_descendant_head_is_not_stale(self):
        self.write("unrelated.txt", "Unrelated change\n")
        self.commit("Advance unrelated HEAD")
        self.assertEqual(self.check(), [])

    def test_uncommitted_unrelated_file_is_not_a_bound_source_change(self):
        self.write("unrelated.txt", "Unrelated draft\n")
        self.assertEqual(self.check(), [])

    def test_each_required_source_change_warns(self):
        for path in SOURCES:
            with self.subTest(path=path):
                original = (self.target / path).read_text(encoding="utf-8")
                self.write(path, original + "Changed\n")
                self.assert_stale()
                self.write(path, original)

    def test_committed_source_change_warns_even_if_worktree_restores_old_bytes(self):
        path = SOURCES[0]
        original = (self.target / path).read_text(encoding="utf-8")
        self.write(path, original + "Changed\n")
        self.commit("Change a bound source")
        self.assert_stale()
        self.write(path, original)
        self.assert_stale()

    def test_missing_source_fails(self):
        (self.target / SOURCES[0]).unlink()
        self.assert_error()

    def test_current_hash_cannot_relabel_the_reviewed_commit(self):
        self.write(SOURCES[0], "Changed\n")
        self.registry["evidence_binding"]["inputs"][0]["sha256"] = hashlib.sha256(b"Changed\n").hexdigest()
        self.assert_error()

    def test_missing_required_sources_fail(self):
        original = self.registry["evidence_binding"]["inputs"]
        for index in range(len(SOURCES)):
            with self.subTest(index=index):
                self.registry["evidence_binding"]["inputs"] = original[:index] + original[index + 1:]
                self.assert_error()
        self.registry["evidence_binding"]["inputs"] = original

    def test_new_discovered_task_requires_a_new_binding(self):
        new_task = ".ai/assistant/team/tasks/task-2.json"
        self.write(new_task, "New task\n")
        self.assert_error(required=[*SOURCES, new_task])

    def test_symbolic_abbreviated_unknown_and_non_commit_revisions_fail(self):
        tree = self.git("rev-parse", "HEAD^{tree}")
        for value in ("HEAD", self.revision[:12], "0" * 40, tree, None):
            with self.subTest(value=value):
                self.registry["evidence_revision"] = value
                self.assert_error()

    def test_non_ancestor_revision_fails(self):
        self.git("checkout", "-qb", "other")
        self.write("other.txt", "Other branch\n")
        self.commit("Other descendant")
        other = self.git("rev-parse", "HEAD")
        self.git("checkout", "--detach", "-q", self.revision)
        self.registry["evidence_revision"] = other
        self.assert_error()

    def test_unavailable_ancestry_fails_closed(self):
        with patch.object(GitEvidenceView, "is_ancestor", return_value=None):
            self.assert_error()

    def test_non_repository_and_nested_repository_target_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assert_error(target=Path(directory).resolve())
        nested = self.target / "nested"
        nested.mkdir()
        self.assert_error(target=nested)

    def test_worktree_root_alias_uses_the_same_physical_root(self):
        with tempfile.TemporaryDirectory() as directory:
            alias = Path(directory) / "alias"
            try:
                alias.symlink_to(self.target, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("platform does not permit directory symlinks")
            self.assertEqual(self.check(target=alias), [])

    def test_unsafe_duplicate_and_self_referential_paths_fail(self):
        original = copy.deepcopy(self.registry["evidence_binding"]["inputs"])
        paths = ("../outside", "/absolute", "C:/absolute", "a\\b", "a/../b", "./a", "a//b", "a/", ".", "", "bad\0path", ".git/config", REGISTRY, SOURCES[1])
        for path in paths:
            with self.subTest(path=path):
                self.registry["evidence_binding"]["inputs"] = copy.deepcopy(original)
                self.registry["evidence_binding"]["inputs"][0]["path"] = path
                self.assert_error()

    def test_malformed_binding_fields_and_hashes_fail(self):
        original = copy.deepcopy(self.registry["evidence_binding"])
        for binding in (None, {}, {"schema_version": 1, "inputs": []}, {"schema_version": True, "inputs": original["inputs"]}, {**original, "unknown": True}, {"schema_version": 1, "inputs": [None]}):
            with self.subTest(binding=binding):
                self.registry["evidence_binding"] = binding
                self.assert_error()
        for digest in ("0" * 63, "A" * 64, "g" * 64, None, 1):
            with self.subTest(digest=digest):
                self.registry["evidence_binding"] = copy.deepcopy(original)
                self.registry["evidence_binding"]["inputs"][0]["sha256"] = digest
                self.assert_error()

    def test_symlink_file_and_directory_components_fail(self):
        path = self.target / SOURCES[0]
        original = path.read_bytes()
        destination = self.target / "same-bytes.json"
        destination.write_bytes(original)
        path.unlink()
        try:
            path.symlink_to(destination)
        except (OSError, NotImplementedError):
            self.skipTest("platform does not permit symlinks")
        self.assert_error()
        path.unlink()
        path.write_bytes(original)
        project = self.target / ".ai/project"
        moved = self.target / "project-sources"
        project.rename(moved)
        project.symlink_to(moved, target_is_directory=True)
        self.assert_error()

    def test_external_symlink_source_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory) / "source.json"
            outside.write_bytes((self.target / SOURCES[0]).read_bytes())
            selected = self.target / SOURCES[0]
            selected.unlink()
            try:
                selected.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("platform does not permit symlinks")
            self.assert_error()

    def test_committed_symlink_cannot_be_replaced_with_matching_regular_bytes(self):
        self.write("destination.txt", "data\n")
        selected = self.target / SOURCES[0]
        selected.unlink()
        try:
            selected.symlink_to("../../destination.txt")
        except (OSError, NotImplementedError):
            self.skipTest("platform does not permit symlinks")
        self.commit("Capture symlink")
        self.registry["evidence_revision"] = self.git("rev-parse", "HEAD")
        selected.unlink()
        selected.write_text("../../destination.txt", encoding="utf-8")
        self.registry["evidence_binding"]["inputs"][0]["sha256"] = hashlib.sha256(selected.read_bytes()).hexdigest()
        self.assert_error()

    def test_file_and_input_count_limits_fail_closed(self):
        original = copy.deepcopy(self.registry["evidence_binding"])
        self.registry["evidence_binding"]["inputs"] *= 22
        self.assert_error()
        self.registry["evidence_binding"] = original
        self.write(SOURCES[0], "x" * (1024 * 1024 + 1))
        self.commit("Oversized source")
        self.registry["evidence_revision"] = self.git("rev-parse", "HEAD")
        self.registry["evidence_binding"]["inputs"][0]["sha256"] = hashlib.sha256((self.target / SOURCES[0]).read_bytes()).hexdigest()
        self.assert_error()

    def test_total_source_bytes_limit_fails_closed(self):
        inputs = self.registry["evidence_binding"]["inputs"]
        for index in range(9):
            path = f"extra/source-{index}.txt"
            self.write(path, "x" * (1024 * 1024))
            inputs.append({"path": path, "sha256": hashlib.sha256((self.target / path).read_bytes()).hexdigest()})
        self.commit("Capture oversized source set")
        self.registry["evidence_revision"] = self.git("rev-parse", "HEAD")
        self.assert_error()

    def test_full_validator_uses_binding_and_requires_discovered_task_sources(self):
        from check_team_collaboration_scenarios import task, validator, write_fixture

        write_fixture(self.target, task())
        self.write(SOURCES[4], "Task record template\n")
        self.commit("Capture realistic registry sources")
        path = self.target / REGISTRY
        registry = json.loads(path.read_text(encoding="utf-8"))
        registry["evidence_revision"] = self.git("rev-parse", "HEAD")
        registry["evidence_binding"] = {
            "schema_version": 1,
            "inputs": [{"path": source, "sha256": hashlib.sha256((self.target / source).read_bytes()).hexdigest()} for source in SOURCES],
        }
        path.write_text(json.dumps(registry), encoding="utf-8")
        self.write("unrelated.txt", "Unrelated\n")
        self.commit("Advance unrelated registry publication")
        checked = validator(self.target)
        checked.check_team_collaboration(None)
        self.assertEqual(checked.findings, [])
        registry["evidence_binding"]["inputs"].pop()
        path.write_text(json.dumps(registry), encoding="utf-8")
        checked = validator(self.target)
        checked.check_team_collaboration(None)
        self.assertTrue(any(finding.code == "TEAM_REGISTRY_METADATA" for finding in checked.findings))

    def full_validator_binding(self, *, task_destination=None):
        from check_team_collaboration_scenarios import task, write_fixture

        write_fixture(self.target, task())
        self.write(SOURCES[4], "Task record template\n")
        sources = list(SOURCES)
        if task_destination is not None:
            self.write(task_destination, (self.target / SOURCES[-1]).read_text(encoding="utf-8"))
            sources[-1] = task_destination
        self.commit("Capture full-validator sources and alias destinations")
        registry = json.loads((self.target / REGISTRY).read_text(encoding="utf-8"))
        registry["evidence_revision"] = self.git("rev-parse", "HEAD")
        registry["evidence_binding"] = {
            "schema_version": 1,
            "inputs": [
                {"path": source, "sha256": hashlib.sha256((self.target / source).read_bytes()).hexdigest()}
                for source in sources
            ],
        }
        self.write(REGISTRY, json.dumps(registry))
        self.commit("Publish full-validator source binding")
        return registry

    def assert_full_validator_path_error(self, *, message=None):
        from check_team_collaboration_scenarios import validator

        checked = validator(self.target)
        checked.check_team_collaboration(None)
        self.assertTrue(
            any(
                finding.code == "TEAM_REGISTRY_PATH"
                and (message is None or message in finding.message)
                for finding in checked.findings
            ),
            checked.findings,
        )

    def test_symlink_inspection_oserror_fails_closed(self):
        with patch.object(Path, "is_symlink", side_effect=OSError(errno.ENAMETOOLONG, "fixture path too long")):
            self.assert_error()

    def test_source_reader_filesystem_and_encoding_exceptions_fail_closed(self):
        failures = (
            OSError(errno.ENAMETOOLONG, "fixture path too long"),
            UnicodeEncodeError("utf-8", "\ud800", 0, 1, "surrogates not allowed"),
            ValueError("fixture path escaped the target"),
            RuntimeError("fixture symlink loop"),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__), patch.object(
                TargetRepositoryView, "read_bytes_result", side_effect=failure
            ):
                self.assert_error()

    def test_git_source_reader_encoding_exception_fails_closed(self):
        failure = UnicodeEncodeError("utf-8", "\ud800", 0, 1, "surrogates not allowed")
        with patch.object(GitEvidenceView, "bounded_file_at_ref", side_effect=failure):
            self.assert_error()

    def test_full_validator_overlong_binding_path_fails_closed(self):
        registry = self.full_validator_binding()
        registry["evidence_binding"]["inputs"].append({"path": "x" * 4096, "sha256": "0" * 64})
        self.write(REGISTRY, json.dumps(registry))
        self.assert_full_validator_path_error()

    def test_full_validator_non_utf8_binding_paths_fail_closed(self):
        registry = self.full_validator_binding()
        inputs = copy.deepcopy(registry["evidence_binding"]["inputs"])
        for path in ("unpaired-\ud800.json", "escaped-byte-\udcff.json"):
            with self.subTest(path=repr(path)):
                registry["evidence_binding"]["inputs"] = [
                    *inputs, {"path": path, "sha256": "0" * 64}
                ]
                self.write(REGISTRY, json.dumps(registry))
                self.assert_full_validator_path_error(message="UTF-8")

    def test_full_validator_rejects_task_file_alias_with_prebound_destination(self):
        destination = ".ai/retained-team/task-1.json"
        self.full_validator_binding(task_destination=destination)
        selected = self.target / SOURCES[-1]
        selected.unlink()
        try:
            selected.symlink_to(self.target / destination)
        except (OSError, NotImplementedError):
            self.skipTest("platform does not permit file symlinks")
        self.assert_full_validator_path_error(message="symlink")

    def test_full_validator_rejects_task_directory_alias_with_prebound_destination(self):
        destination = ".ai/retained-team/tasks/task-1.json"
        self.full_validator_binding(task_destination=destination)
        selected = self.target / SOURCES[-1]
        selected.unlink()
        directory = selected.parent
        directory.rmdir()
        try:
            directory.symlink_to((self.target / destination).parent, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("platform does not permit directory symlinks")
        self.assert_full_validator_path_error(message="symlink")

    def test_full_validator_legacy_task_alias_keeps_prior_behavior(self):
        from check_team_collaboration_scenarios import validator

        destination = ".ai/retained-team/task-1.json"
        registry = self.full_validator_binding(task_destination=destination)
        del registry["evidence_binding"]
        registry["evidence_revision"] = "unavailable"
        self.write(REGISTRY, json.dumps(registry))
        selected = self.target / SOURCES[-1]
        selected.unlink()
        try:
            selected.symlink_to(self.target / destination)
        except (OSError, NotImplementedError):
            self.skipTest("platform does not permit file symlinks")
        checked = validator(self.target)
        checked.check_team_collaboration(None)
        self.assertEqual(checked.findings, [])

    def test_full_validator_task_discovery_oserror_fails_closed(self):
        self.full_validator_binding()
        directory = (self.target / SOURCES[-1]).parent
        original_glob = Path.glob

        def failing_glob(path, pattern):
            if path == directory:
                raise OSError(errno.ENAMETOOLONG, "fixture task directory too long")
            return original_glob(path, pattern)

        with patch.object(Path, "glob", failing_glob):
            self.assert_full_validator_path_error(message="directory cannot be inspected safely")


if __name__ == "__main__":
    unittest.main()

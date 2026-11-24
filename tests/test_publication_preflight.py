from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from publication_preflight import MAX_OUTPUT, MAX_PATHS, _git, publication_preflight
from target_validation_support import GitEvidenceView


class PublicationPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.target = Path(self.temporary.name).resolve()
        self.git("init", "-q")
        for key, value in (("user.name", "Fixture"), ("user.email", "fixture@example.invalid"), ("gc.auto", "0"), ("maintenance.auto", "false")):
            self.git("config", key, value)
        (self.target / "src").mkdir()
        (self.target / "src/app.py").write_text("implementation\n")
        (self.target / "src/required.py").write_text("unchanged dependency\n")
        (self.target / "outside.txt").write_text("source-specific infrastructure\n")
        self.source = self.commit("source")

    def git(self, *args):
        result = subprocess.run(["git", *args], cwd=self.target, check=True, capture_output=True)
        return result.stdout.decode().strip()

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD")

    def compare(self, candidate, paths=None, **checks):
        return publication_preflight(self.target, self.source, candidate, ["src"] if paths is None else paths, **checks)

    def test_retired_paths_are_checked_on_candidate_even_if_unchanged(self):
        self.assertEqual(self.compare(self.source, absent_paths=["retired", "src/not-present"])["failures"], [])
        failures = self.compare(self.source, absent_paths=["outside.txt", "src"])["failures"]
        self.assertEqual([item["path"] for item in failures], ["outside.txt", "src"])
        (self.target / "outside.txt").unlink()
        self.assertEqual(self.compare(self.commit("retire configuration"), absent_paths=["outside.txt"])["failures"], [])

    def test_root_lockfile_must_be_explicit_and_exact(self):
        lock = self.target / "package.lock"
        lock.write_text("pinned\n")
        self.source = self.commit("root dependency lock")
        lock.write_text("different\n")
        candidate = self.commit("changed root dependency lock")
        self.assertFalse(self.compare(candidate)["failures"])
        self.assertEqual(self.compare(candidate, ["src", "package.lock"])["failures"][0]["path"], "package.lock")

    def test_selected_catalog_drift_blocks_without_hydrating_unrelated_leaves(self):
        from context_input_snapshot import _limited_read
        from tests.test_context_catalog import entry

        folder = self.target / "documentation"
        folder.mkdir()
        for name in ("validation.md", "unrelated.md"):
            (folder / name).write_text("use current validation\n")
        index = {"schema_version": 1, "index_kind": "alatyr-context-index", "index_id": "project",
                 "title": "Project", "summary": "Project context", "contour": "project", "max_depth": 3}
        child = folder / "child.json"
        child.write_text(json.dumps({**index, "index_id": "child", "entries": [
            entry(folder, "validation", "content", "validation.md"),
            entry(folder, "unrelated", "content", "unrelated.md"),
        ]}))
        top = folder / "context-index.json"
        top.write_text(json.dumps({**index, "entries": [entry(folder, "child-ref", "index", "child.json")]}))
        checks = {"context_index": "documentation/context-index.json", "context_paths": ["documentation/validation.md"]}
        (folder / "unrelated.md").write_text("unrelated stale projection\n")
        first = self.commit("add catalog")
        with patch("context_input_snapshot._limited_read", wraps=_limited_read) as reads:
            self.assertEqual(self.compare(first, **checks)["failures"], [])
        children = [call for call in reads.call_args_list if call.args[0] == child]
        self.assertEqual(len(children), 2)  # Observation and final freshness check.
        self.assertTrue(all(call.args[1] == 1024 * 1024 and call.kwargs["regular_only"] for call in children))
        self.assertFalse(any(call.args[0] == folder / "unrelated.md" for call in reads.call_args_list))
        with self.assertRaisesRegex(ValueError, "exact candidate"):
            self.compare(self.source, **checks)
        self.git("update-index", "--assume-unchanged", "documentation/validation.md")
        with self.assertRaisesRegex(ValueError, "assume-unchanged"):
            self.compare(first, **checks)
        self.git("update-index", "--no-assume-unchanged", "documentation/validation.md")
        (folder / "validation.md").write_text("use revised validation\n")
        with self.assertRaisesRegex(ValueError, "clean candidate"):
            self.compare(first, **checks)
        failures = self.compare(self.commit("stale validation projection"), **checks)["failures"]
        self.assertEqual(len(failures), 1)
        self.assertIn("documentation/child.json", failures[0]["reason"])
        child.write_text(child.read_text() + "\n")
        failures = self.compare(self.commit("stale child-index digest"), **checks)["failures"]
        self.assertIn("content_digest is stale", failures[0]["reason"])

        (self.target / ".git/info/exclude").write_text("documentation/alias.json\n")
        try:
            (folder / "alias.json").symlink_to("child.json")
        except (OSError, NotImplementedError):
            return
        top.write_text(json.dumps({**index, "entries": [entry(folder, "alias-ref", "index", "alias.json")]}))
        failures = self.compare(self.commit("untracked index alias"), **checks)["failures"]
        self.assertIn("must not traverse a symlink", failures[0]["reason"])

    def test_unselected_infrastructure_diff_is_allowed_without_granting_authority(self):
        (self.target / "outside.txt").unlink()
        candidate = self.commit("candidate infrastructure")
        report = self.compare(candidate)
        self.assertEqual(report["state"], "selected-tree-equivalent")
        self.assertEqual(report["candidate_revision"], candidate)
        for flag in ("authorization_granted", "publication_performed", "live_remote_verified"):
            self.assertFalse(report[flag])

    def test_missing_unchanged_dependency_and_candidate_only_descendant_fail(self):
        (self.target / "src/required.py").unlink()
        candidate = self.commit("omit dependency")
        self.assertTrue(self.compare(candidate)["failures"])
        self.assertTrue(self.compare(candidate, ["src/required.py"])["failures"])
        self.assertTrue(self.compare(candidate, ["never-existed.py"])["failures"])
        (self.target / "src/new.py").write_text("candidate-only behavior")
        self.assertTrue(self.compare(self.commit("extra behavior"))["failures"])

    def test_selected_modes_and_symlink_substitution_are_not_byte_only_comparisons(self):
        self.git("update-index", "--chmod=+x", "src/app.py")
        self.git("commit", "-qm", "mode change")
        self.assertTrue(self.compare(self.git("rev-parse", "HEAD"))["failures"])
        file = self.target / "src/required.py"
        file.unlink()
        try:
            file.symlink_to("app.py")
        except (OSError, NotImplementedError):
            return
        self.assertTrue(self.compare(self.commit("link change"))["failures"])

    def test_literal_special_paths_and_subtree_selection(self):
        for name in ("space name.py", "[literal].py", "a*b.py", "unicode-\u00e9.py"):
            if os.name == "nt" and "*" in name:
                continue
            path = self.target / "src" / name
            path.write_text("literal content\n", encoding="utf-8")
        source = self.commit("literal names")
        paths = [p.relative_to(self.target).as_posix() for p in (self.target / "src").iterdir()]
        self.assertEqual(publication_preflight(self.target, source, source, paths)["failures"], [])
        self.assertEqual(publication_preflight(self.target, source, source, ["src", *paths])["failures"], [])

    def test_git_stdout_is_bounded_during_collection_and_stderr_is_discarded(self):
        config = self.target / ".git/config"
        baseline = config.read_text(encoding="utf-8")
        for size in (MAX_OUTPUT - 1, MAX_OUTPUT, MAX_OUTPUT + 1):
            config.write_text(baseline + "\n[large]\n value = " + "x" * (size - 1) + "\n", encoding="utf-8")
            if size > MAX_OUTPUT:
                with self.assertRaisesRegex(ValueError, "byte limit"):
                    _git(self.target, "config", "--get", "large.value")
            else:
                self.assertEqual(len(_git(self.target, "config", "--get", "large.value")), size)
        with self.assertRaises(ValueError):
            _git(self.target, "config", "--bool", "--get", "large.value")

    def test_bounds_and_bad_paths_or_revision_expressions_are_rejected(self):
        for count in (MAX_PATHS - 1, MAX_PATHS, MAX_PATHS + 1):
            paths = [f"missing-{i}.py" for i in range(count)]
            if count > MAX_PATHS:
                with self.assertRaises(ValueError): self.compare(self.source, paths)
            else:
                self.assertEqual(len(self.compare(self.source, paths)["failures"]), count)
        for path in ("../src", "/src", "C:/src", "\\\\host\\src", "src\\app.py", "./src", "src//app.py", ".git/config", "src/../src"):
            with self.subTest(path=path), self.assertRaises(ValueError): self.compare(self.source, [path])
        for ref in ("HEAD", "--help", self.source + "~1", "a" * 40, [], None):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                publication_preflight(self.target, ref, self.source, ["src"])

    def test_ref_moves_do_not_change_frozen_candidate_and_replacements_do_not_substitute(self):
        (self.target / "outside.txt").write_text("candidate")
        candidate = self.commit("candidate")
        (self.target / "src/app.py").write_text("different")
        moved = self.commit("move branch")
        self.assertFalse(self.compare(candidate)["failures"])
        self.assertTrue(self.compare(moved)["failures"])
        self.git("replace", candidate, moved)
        self.assertFalse(self.compare(candidate)["failures"])

    def test_promisor_repositories_fail_before_object_lookup_and_never_fetch(self):
        self.git("config", "remote.origin.promisor", "true")
        with self.assertRaisesRegex(ValueError, "promisor"):
            self.compare("a" * 40)

    def test_inherited_git_routing_and_config_cannot_replace_the_selected_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            foreign = Path(directory).resolve()
            subprocess.run(["git", "init", "-q"], cwd=foreign, check=True)
            with patch.dict(os.environ, {"GIT_DIR": str(foreign / ".git"), "GIT_WORK_TREE": str(foreign)}):
                self.assertEqual(self.compare(self.source)["failures"], [])
        self.git("config", "remote.origin.promisor", "true")
        override = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "remote.origin.promisor", "GIT_CONFIG_VALUE_0": "false"}
        with patch.dict(os.environ, override), self.assertRaisesRegex(ValueError, "promisor"):
            self.compare(self.source)

    def test_public_cli_and_exact_tracking_refs(self):
        argv = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "publication-preflight", "--target", str(self.target), "--source-ref", self.source, "--candidate-ref", self.source, "--path", "src"]
        run = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)["candidate_revision"], self.source)
        self.git("update-ref", "refs/remotes/origin/main", self.source)
        git = GitEvidenceView(self.target)
        self.assertEqual(git.literal_remote_ref("refs/remotes/origin/main"), self.source)
        for ref in ("refs/remotes/origin/main~1", "refs/remotes/origin/main^{}", "refs/remotes/origin/main@{0}"):
            self.assertIsNone(git.literal_remote_ref(ref))

    def test_selected_gitlink_is_not_treated_as_validated_dependency_contents(self):
        self.git("update-index", "--add", "--cacheinfo", "160000," + self.source + ",vendor")
        self.git("commit", "-qm", "gitlink entry")
        revision = self.git("rev-parse", "HEAD")
        report = publication_preflight(self.target, revision, revision, ["vendor"])
        self.assertIn("gitlink", report["failures"][0]["reason"])

    def test_sha256_commit_identity_when_git_supports_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            result = subprocess.run(["git", "init", "-q", "--object-format=sha256"], cwd=root, capture_output=True)
            if result.returncode:
                self.skipTest("installed Git does not support SHA-256 repositories")
            for args in (("config", "user.name", "Fixture"), ("config", "user.email", "fixture@example.invalid")):
                subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
            (root / "file.txt").write_text("content\n")
            for args in (("add", "file.txt"), ("commit", "-qm", "source")):
                subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
            revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            self.assertEqual(len(revision), 64)
            self.assertEqual(publication_preflight(root, revision, revision, ["file.txt"])["failures"], [])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_change_packages import changed_index_validator, git, valid_package_fixture
from target_validation_support import GitEvidenceView
from target_adapter_validation.harness_scenarios.analysis_strategies import _model, _write_model


class HistoricalSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.target = Path(self.directory.name).resolve()
        self.path, self.package = valid_package_fixture(self.target)
        self.commit = self.package["provenance"]["after_revision"]
        self.package["status"] = "blocked"
        self.package["provenance"].update(
            evidence_quality="selected-file-snapshot", public_claim_strength="limited",
            selected_file_snapshot={
                "algorithm": "sha256", "paths": ["src/feature.txt"],
                "digest": GitEvidenceView(self.target).snapshot_sha256(self.commit, ["src/feature.txt"]),
                "source_commit": self.commit,
            },
        )
        shutil.copy2(ROOT / "templates/target/.ai/.gitignore", self.target / ".ai/.gitignore")
        strategy = self.target / ".ai/assistant/analysis-strategies/invariant-first.json"
        strategy.parent.mkdir(parents=True)
        shutil.copy2(ROOT / "templates/target/.ai/assistant/analysis-strategies/invariant-first.json", strategy)
        model = _model()
        model["operation_id"] = "operation-1"
        model_path = self.target / ".ai/.runtime/problem-models/fixture-problem.json"
        _write_model(self.target, model_path, model)
        self.package["incident_continuity"] = {
            "mode": "none", "family_id": "none", "trigger": "none", "corrective_iteration": 0,
            "predecessors": [], "problem_model": {"path": model_path.relative_to(self.target).as_posix(), "sha256": hashlib.sha256(model_path.read_bytes()).hexdigest()},
            "latest_failed_gate": {"state": "none", "id": "none", "evidence_refs": []}, "lifecycle_model_required": False,
        }
        (self.target / "src/feature.txt").write_bytes(b"later work\n")

    def check(self, *, selected=False, task=None):
        self.path.write_text(json.dumps(self.package), encoding="utf-8")
        index_path = self.path.parent / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index["records"][0].update(status=self.package["status"], evidence_quality="selected-file-snapshot")
        index_path.write_text(json.dumps(index), encoding="utf-8")
        checked = changed_index_validator(self.target)
        checked.change_packages = [self.path] if selected else []
        checked.current_task_id = task
        phase = next(phase for phase in checked.validation_phases(None, "core", set()) if phase.phase_id == "change-packages")
        phase.run()
        return checked

    def snapshot_errors(self, checked):
        return {item.code for item in checked.findings if item.level == "error" and item.code.startswith("PACKAGE_SNAPSHOT")}

    def test_exact_historical_commit_does_not_promote_blocked_or_implementing_work(self):
        for status in ("blocked", "implementing"):
            with self.subTest(status=status):
                self.package["status"] = status
                checked = self.check()
                self.assertEqual(self.snapshot_errors(checked), set())
                self.assertEqual({item.code for item in checked.findings if item.level == "error"}, set())
                self.assertTrue(any(item.code == "PACKAGE_SNAPSHOT_HISTORICAL_BOUND" for item in checked.findings))
                self.assertEqual(self.package["status"], status)

    def test_cli_routes_historical_and_selected_snapshot_findings(self):
        original = copy.deepcopy(self.package)
        for scenario in ("historical", "wrong-digest", "selected"):
            with self.subTest(scenario=scenario):
                self.package = copy.deepcopy(original)
                if scenario == "wrong-digest":
                    self.package["provenance"]["selected_file_snapshot"]["digest"] = "0" * 64
                self.check()
                command = [sys.executable, "-B", str(ROOT / "tools/validate_target_adapter.py"),
                           "--target", str(self.target), "--diff-ref", "HEAD",
                           "--validation-phase", "migration-staging", "--json"]
                if scenario == "selected":
                    command.extend(["--change-package", str(self.path)])
                result = subprocess.run(command, capture_output=True, text=True, timeout=30)
                payload = json.loads(result.stdout)
                findings = payload["findings"]
                errors = {row["code"] for row in findings if row["level"] == "error"}
                if scenario == "historical":
                    self.assertTrue(any(row["code"] == "PACKAGE_SNAPSHOT_HISTORICAL_BOUND" for row in findings))
                    self.assertFalse(any(code.startswith("PACKAGE_SNAPSHOT") for code in errors))
                else:
                    self.assertIn("PACKAGE_SNAPSHOT_COMMIT", errors)
                    self.assertNotEqual(result.returncode, 0)
                # The deliberately minimal fixture is not a full accepted adapter.
                self.assertFalse(payload["placeholder_validation"]["acceptance_eligible"])

    def test_wrong_digest_or_non_immutable_revision_is_rejected(self):
        original = copy.deepcopy(self.package)
        for field, value in (("digest", "0" * 64), ("source_commit", "HEAD"), ("source_commit", self.commit[:12]), ("source_commit", "f" * 40), ("source_commit", self.commit + "^{tree}")):
            with self.subTest(field=field, value=value):
                self.package = copy.deepcopy(original)
                self.package["provenance"]["selected_file_snapshot"][field] = value
                self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check()))

    def test_unsupported_claim_retains_historical_verification_without_promotion(self):
        self.package["provenance"]["public_claim_strength"] = "unsupported"
        checked = self.check()
        self.assertEqual(self.snapshot_errors(checked), set())
        self.assertTrue(any(item.code == "PACKAGE_SNAPSHOT_HISTORICAL_BOUND" for item in checked.findings))

    def test_malformed_snapshot_fields_return_findings(self):
        original = copy.deepcopy(self.package)
        for field in ("algorithm", "digest", "paths", "source_commit"):
            for value in ([], {}, None, False, 1, "unknown"):
                with self.subTest(field=field, value=value):
                    self.package = copy.deepcopy(original)
                    self.package["provenance"]["selected_file_snapshot"][field] = value
                    self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check()))

    def test_unpaired_unicode_paths_fail_before_blob_access(self):
        for point in (0xD800, 0xDC00):
            with self.subTest(point=point):
                self.package["provenance"]["selected_file_snapshot"]["paths"] = ["src/" + chr(point)]
                with patch.object(GitEvidenceView, "snapshot_sha256", side_effect=AssertionError("invalid UTF-8 must not read blobs")):
                    self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check()))

    def test_historical_evidence_cannot_accept_selected_package_or_current_task(self):
        for selected, task in ((True, None), (False, "package-1"), (False, "operation-1")):
            with self.subTest(selected=selected, task=task):
                self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check(selected=selected, task=task)))

    def write_task(self, operation):
        path = self.target / ".ai/assistant/active-tasks.json"
        path.write_text(json.dumps({"schema_version": 1, "index_kind": "target-active-task-index", "tasks": [{
            "task_id": "separate-task", "operation_id": operation, "state": "active", "task_class": "small-task",
            "problem_model": None, "completion_evidence": None, "canonical_owners": [], "changed_fact_ids": [],
            "incident_family_id": "none", "predecessor_task_ids": [], "latest_failed_gate_id": "none",
        }]}), encoding="utf-8")

    def test_registered_distinct_task_id_cannot_hide_shared_operation(self):
        self.write_task("operation-1")
        self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check(task="separate-task")))

    def test_shared_model_and_untrusted_task_index_cannot_claim_distinctness(self):
        self.write_task("unrelated-operation")
        path = self.target / ".ai/assistant/active-tasks.json"
        index = json.loads(path.read_text(encoding="utf-8"))
        index["tasks"][0].update(task_class="standard-task", problem_model=self.package["incident_continuity"]["problem_model"])
        path.write_text(json.dumps(index), encoding="utf-8")
        self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check(task="separate-task")))
        for raw in (b"invalid", b"{}", b'{"schema_version":1,"schema_version":1}', b" " * (512 * 1024 + 1)):
            with self.subTest(size=len(raw)):
                path.write_bytes(raw)
                self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check(task="separate-task")))

    def test_duplicate_field_in_otherwise_valid_index_is_rejected(self):
        self.write_task("unrelated-operation")
        path = self.target / ".ai/assistant/active-tasks.json"
        raw = path.read_text(encoding="utf-8")
        path.write_text(raw.replace('"operation_id": "unrelated-operation"', '"operation_id": "operation-1", "operation_id": "unrelated-operation"'), encoding="utf-8")
        self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check(task="separate-task")))

    def test_duplicate_other_task_ids_cannot_establish_distinctness(self):
        self.write_task("unrelated-operation")
        path = self.target / ".ai/assistant/active-tasks.json"
        index = json.loads(path.read_text(encoding="utf-8"))
        other = dict(index["tasks"][0], task_id="other-task")
        index["tasks"].extend([other, copy.deepcopy(other)])
        path.write_text(json.dumps(index), encoding="utf-8")
        self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check(task="separate-task")))

    def test_malformed_package_ownership_is_reported_not_raised(self):
        self.write_task("unrelated-operation")
        original = copy.deepcopy(self.package)
        for container, key in ((self.package, "package_id"), (self.package["operation"], "id")):
            for value in ([], {}, None):
                with self.subTest(key=key, value=value):
                    container[key] = value
                    self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check(task="separate-task")))
            container[key] = original["package_id"] if key == "package_id" else original["operation"]["id"]
        self.write_task("unrelated-operation")
        self.assertEqual(self.snapshot_errors(self.check(task="separate-task")), set())
        (self.target / ".ai/assistant/active-tasks.json").unlink()
        self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check(task="separate-task")))

    def test_missing_or_malformed_snapshot_is_reported_not_raised(self):
        original = copy.deepcopy(self.package)
        for value in (None, [], "invalid"):
            with self.subTest(value=value):
                self.package = copy.deepcopy(original)
                self.package["provenance"]["selected_file_snapshot"] = value
                self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check()))
        del self.package["provenance"]["selected_file_snapshot"]
        self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check()))

    def test_current_classification_or_strong_claim_cannot_use_historical_escape(self):
        self.package["evidence_classification"] = "observed-current"
        self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check()))
        self.package["evidence_classification"] = "historical-record"
        self.package["provenance"]["public_claim_strength"] = "strong"
        self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check()))

    def test_unsafe_missing_duplicate_and_directory_paths_are_rejected(self):
        snapshot = self.package["provenance"]["selected_file_snapshot"]
        for paths in (["../outside"], ["/outside"], ["src/*"], ["src/feature?.txt"], [":(glob)src/*"], ["src\\feature.txt"], ["src"], ["missing.txt"], ["src/feature.txt", "src/feature.txt"]):
            with self.subTest(paths=paths):
                snapshot["paths"] = paths
                self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check()))

    def test_literal_bracket_blob_is_verified_without_current_file(self):
        path = "src/routes/[id]/route.ts"
        file = self.target / path
        file.parent.mkdir(parents=True)
        file.write_bytes(b"literal route\n")
        git(self.target, "--literal-pathspecs", "add", path)
        git(self.target, "commit", "-qm", "literal route")
        revision = git(self.target, "rev-parse", "HEAD")
        digest = hashlib.sha256(path.encode() + b"\0" + file.read_bytes() + b"\0").hexdigest()
        file.unlink()
        self.package["provenance"]["selected_file_snapshot"].update(paths=[path], digest=digest, source_commit=revision)
        self.assertEqual(self.snapshot_errors(self.check()), set())

    def test_symlink_blob_and_non_ancestor_base_are_rejected(self):
        original_digest = self.package["provenance"]["selected_file_snapshot"]["digest"]
        link = self.target / "src/link.txt"
        try:
            link.symlink_to("feature.txt")
        except OSError as exc:
            self.skipTest(str(exc))
        git(self.target, "add", "src/link.txt")
        git(self.target, "commit", "-qm", "symlink fixture")
        revision = git(self.target, "rev-parse", "HEAD")
        digest = hashlib.sha256(b"src/link.txt\0feature.txt\0").hexdigest()
        self.package["provenance"]["selected_file_snapshot"].update(paths=["src/link.txt"], digest=digest, source_commit=revision)
        self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check()))
        self.package["provenance"]["selected_file_snapshot"].update(paths=["src/feature.txt"], digest=original_digest, source_commit=self.commit)
        self.package["provenance"]["before_revision"] = revision
        self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check()))

    def test_absent_historical_commit_keeps_current_snapshot_enforcement(self):
        del self.package["provenance"]["selected_file_snapshot"]["source_commit"]
        self.assertIn("PACKAGE_SNAPSHOT_HASH", self.snapshot_errors(self.check()))

    def test_bounded_snapshot_reads_fail_closed(self):
        with patch.object(GitEvidenceView, "snapshot_sha256", return_value=None) as read:
            self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check()))
        self.assertEqual(read.call_args.kwargs["byte_limits"], (4 * 1024 * 1024, 64 * 1024 * 1024))
        self.package["provenance"]["selected_file_snapshot"]["paths"] = [f"src/{index}.txt" for index in range(257)]
        with patch.object(GitEvidenceView, "snapshot_sha256", side_effect=AssertionError("oversized selection must not read blobs")):
            self.assertIn("PACKAGE_SNAPSHOT_COMMIT", self.snapshot_errors(self.check()))

    def test_real_git_blob_at_and_above_per_file_limit(self):
        path = "src/bounded.bin"
        for size, accepted in ((4 * 1024 * 1024, True), (4 * 1024 * 1024 + 1, False)):
            with self.subTest(size=size):
                content = b"x" * size
                (self.target / path).write_bytes(content)
                git(self.target, "add", path)
                git(self.target, "commit", "-qm", "bounded blob")
                revision = git(self.target, "rev-parse", "HEAD")
                digest = hashlib.sha256(path.encode() + b"\0" + content + b"\0").hexdigest()
                self.package["provenance"]["selected_file_snapshot"].update(paths=[path], digest=digest, source_commit=revision)
                self.assertEqual(not self.snapshot_errors(self.check()), accepted)


if __name__ == "__main__":
    unittest.main()

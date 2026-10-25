from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_change_packages import changed_index_validator, git
from check_engineering_evidence import fixture_index, fixture_record
from target_adapter_validation.active_tasks import INDEX_PATH, validate_active_tasks
from target_adapter_validation.harness_scenarios.analysis_strategies import _model, _write_model
from target_adapter_validation.context import TargetRepositoryView


from tests import active_task_fixture as fixture


class TaskClosureTests(fixture.ActiveTaskFixture):
    def test_malformed_enums_produce_findings_not_exceptions(self):
        self.close()
        original = copy.deepcopy(self.closure)
        for field in ["implementation", "evidence_finalization", "publication"]:
            for bad in [{}, [], None, True, 7, "invalid"]:
                with self.subTest(field=field, bad=bad):
                    self.closure = copy.deepcopy(original)
                    self.closure["delivery"][field] = bad
                    self.write_closure()
                    self.assertIn("ACTIVE_TASK_SCHEMA", self.errors(self.check()))
        for field in ["kind", "binding_state"]:
            for bad in [{}, [], None, True, 7]:
                with self.subTest(binding=field, bad=bad):
                    self.closure = copy.deepcopy(original)
                    self.closure["repository_binding"][field] = bad
                    self.write_closure()
                    self.assertTrue(self.errors(self.check()))


    def test_capture_requires_unique_final_task_bound_record(self):
        self.close()
        self.closure["engineering_evidence"].update(state="captured", materiality="material", record_ids=["ENG-1"])
        self.write_closure()
        self.assertIn("TASK_EVIDENCE_UNREGISTERED", self.errors(self.check()))
        record = fixture_record(self.base, self.result)
        record["task"]["operation_id"] = self.task["operation_id"]
        record["task"]["references"] = ["fixture-task"]
        index = fixture_index(record)
        path = self.target / ".ai/project/engineering-evidence/index.json"
        record_path = self.target / index["records"][0]["record"]
        record_path.parent.mkdir(parents=True)
        record_path.write_text(json.dumps(record), encoding="utf-8")
        path.write_text(json.dumps(index), encoding="utf-8")
        self.assertEqual(self.errors(self.check()), set())
        index["records"][0]["status"] = "draft"
        path.write_text(json.dumps(index), encoding="utf-8")
        self.assertIn("TASK_EVIDENCE_UNFINALIZED", self.errors(self.check()))
        index["records"][0]["task_references"] = ["another-task"]
        path.write_text(json.dumps(index), encoding="utf-8")
        self.assertIn("TASK_EVIDENCE_LINEAGE", self.errors(self.check()))


    def test_nested_binding_values_never_crash(self):
        self.close()
        original = copy.deepcopy(self.closure)
        for field in ["selected_paths", "prior_bindings", "base_revision", "result_revision", "snapshot_sha256"]:
            for bad in [{}, [None], [{}], None, True, 7]:
                with self.subTest(field=field, bad=bad):
                    self.closure = copy.deepcopy(original)
                    self.closure["repository_binding"]["kind"] = "selected-file-snapshot" if field in {"selected_paths", "snapshot_sha256"} else "commit"
                    self.closure["repository_binding"]["selected_paths"] = ["src/example.txt"]
                    self.closure["repository_binding"]["snapshot_sha256"] = "0" * 64
                    self.closure["repository_binding"][field] = bad
                    self.write_closure()
                    self.assertTrue(self.errors(self.check()))


    def test_false_current_snapshot_is_not_a_historical_warning(self):
        self.close()
        self.closure["repository_binding"].update(kind="selected-file-snapshot", selected_paths=["src/example.txt"], snapshot_sha256="0" * 64)
        self.write_closure()
        self.assertIn("TASK_CLOSURE_SNAPSHOT_HASH", self.errors(self.check()))
        checked = self.check(selected=False)
        self.assertIn("TASK_CLOSURE_SNAPSHOT_HISTORICAL", {finding.code for finding in checked.findings})
        self.assertNotIn("TASK_CLOSURE_SNAPSHOT_HASH", self.errors(checked))


    def test_captured_receipt_cannot_belong_to_another_operation_or_result(self):
        self.close()
        self.closure["engineering_evidence"].update(state="captured", materiality="material", record_ids=["ENG-1"])
        self.write_closure()
        record = fixture_record(self.base, self.result)
        record["task"]["references"] = ["fixture-task"]
        index = fixture_index(record)
        index_path = self.target / ".ai/project/engineering-evidence/index.json"
        record_path = self.target / index["records"][0]["record"]
        record_path.parent.mkdir(parents=True)
        index_path.write_text(json.dumps(index), encoding="utf-8")
        record_path.write_text(json.dumps(record), encoding="utf-8")
        self.assertIn("TASK_EVIDENCE_LINEAGE", self.errors(self.check()))
        record["task"]["operation_id"] = self.task["operation_id"]
        record["repository_binding"]["result_revision"] = self.base
        record_path.write_text(json.dumps(record), encoding="utf-8")
        self.assertIn("TASK_EVIDENCE_RESULT", self.errors(self.check()))


    def test_material_skip_requires_task_specific_preservation(self):
        self.close()
        self.closure["engineering_evidence"].update(materiality="material", preserved_owners=["design.md"], preservation=[{"fact_id": "change-1", "fact_type": "design", "owner": "design.md"}])
        registry = self.target / ".ai/project/source-of-truth-registry.md"
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_text("### Fact Type: `design`\n\nCanonical owner: `design.md`\n", encoding="utf-8")
        self.write_closure()
        self.assertEqual(self.errors(self.check()), set())
        self.closure["engineering_evidence"]["preservation"][0]["fact_type"] = "unrelated"
        self.write_closure()
        self.assertIn("TASK_EVIDENCE_PRESERVATION", self.errors(self.check()))
        self.closure["engineering_evidence"]["preservation"] = []
        self.write_closure()
        self.assertIn("TASK_EVIDENCE_PRESERVATION", self.errors(self.check()))


    def test_publication_requires_a_result_bound_observation_not_a_label(self):
        self.close()
        self.closure["delivery"]["publication"] = "published"
        self.closure["publication_evidence"] = ["none"]
        self.write_closure()
        self.assertIn("ACTIVE_TASK_SCHEMA", self.errors(self.check()))
        git(self.target, "update-ref", "refs/remotes/origin/main", self.result)
        receipt = {"schema_version": 1, "record_kind": "alatyr-publication-receipt", "task_id": "fixture-task", "operation_id": self.task["operation_id"], "remote_ref": "refs/remotes/origin/main", "observed_revision": self.result, "observed_at": "2026-01-01T00:00:00Z"}
        path = self.target / "publication.json"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        self.closure["publication_evidence"] = [self.bind(path)]
        self.write_closure()
        self.assertEqual(self.errors(self.check()), set())
        for field, value in [("operation_id", "another-operation"), ("observed_revision", self.base), ("observed_at", "tomorrow")]:
            wrong = dict(receipt, **{field: value})
            path.write_text(json.dumps(wrong), encoding="utf-8")
            self.closure["publication_evidence"] = [self.bind(path)]
            self.write_closure()
            self.assertIn("TASK_CLOSURE_PUBLICATION", self.errors(self.check()))


    def test_current_result_checks_commit_tree_and_snapshot_coverage(self):
        self.close()
        (self.target / "src/example.txt").write_text("uncommitted change")
        self.assertIn("TASK_CLOSURE_RESULT_DRIFT", self.errors(self.check()))
        (self.target / "src/example.txt").write_text("implementation\n")
        self.closure["repository_binding"].update(kind="tree", result_revision=git(self.target, "rev-parse", "HEAD^{tree}"))
        self.write_closure()
        self.assertEqual(self.errors(self.check()), set())
        digest = hashlib.sha256(b"design.md\0" + (self.target / "design.md").read_bytes() + b"\0").hexdigest()
        self.closure["repository_binding"].update(kind="selected-file-snapshot", selected_paths=["design.md"], snapshot_sha256=digest)
        self.write_closure()
        self.assertIn("TASK_CLOSURE_RESULT_SCOPE", self.errors(self.check()))
        selected = ["design.md", "src/example.txt"]
        digest = hashlib.sha256()
        for path in selected:
            digest.update(path.encode() + b"\0" + (self.target / path).read_bytes() + b"\0")
        self.closure["repository_binding"].update(selected_paths=selected, snapshot_sha256=digest.hexdigest())
        self.write_closure()
        self.assertEqual(self.errors(self.check()), set())


    def test_lineage_requires_previous_binding_payload_not_only_reason(self):
        self.close()
        self.closure["repository_binding"]["prior_bindings"] = [{"reason": "Upgraded binding", "replaced_at": "2026-01-01T00:00:00Z"}]
        self.write_closure()
        self.assertIn("TASK_CLOSURE_BINDING_LINEAGE", self.errors(self.check()))


    def test_task_index_maintenance_has_no_closure_hash_cycle(self):
        git(self.target, "add", ".")
        git(self.target, "commit", "-qm", "register accepted task headers")
        self.result = git(self.target, "rev-parse", "HEAD")
        self.close()
        self.closure["implementation_surfaces"] += [INDEX_PATH, self.task["completion_evidence"]["path"]]
        self.write_closure()
        self.assertEqual(self.errors(self.check()), set())
        self.closure["knowledge_review"]["reason"] = "Finalized after the implementation commit"
        self.write_closure()
        self.assertEqual(self.errors(self.check()), set())
        self.closure["implementation_surfaces"][-1] = "./" + self.closure["implementation_surfaces"][-1]
        self.write_closure()
        self.assertEqual(self.errors(self.check()), set())
        self.closure["delivery"]["implementation"] = {}
        self.write_closure()
        self.assertIn("ACTIVE_TASK_SCHEMA", self.errors(self.check()))
        self.closure["delivery"]["implementation"] = "complete"
        self.task["canonical_owners"] += ["src/example.txt"]
        self.closure["canonical_owners"] = self.task["canonical_owners"]
        self.write_closure()
        self.assertIn("TASK_CLOSURE_RESULT_DRIFT", self.errors(self.check()))
        self.task["canonical_owners"] = self.closure["canonical_owners"] = ["design.md"]
        self.write_closure()
        other = dict(self.task, task_id="other-task", state="active", task_class="small-task", problem_model=None, completion_evidence=None)
        self.write_index([self.task, other])
        self.assertIn("TASK_CLOSURE_RESULT_DRIFT", self.errors(self.check()))
        self.write_closure()
        self.closure["repository_binding"].update(kind="selected-file-snapshot", selected_paths=[INDEX_PATH], snapshot_sha256=hashlib.sha256(b"irrelevant").hexdigest())
        self.write_closure()
        self.assertIn("TASK_CLOSURE_RESULT_SCOPE", self.errors(self.check()))


    def test_index_projection_rejects_duplicate_json_keys_and_task_ids(self):
        index_path = self.target / INDEX_PATH
        index_path.write_text(index_path.read_text().rstrip()[:-1] + ', "schema_version": 1}', encoding="utf-8")
        git(self.target, "add", ".")
        git(self.target, "commit", "-qm", "malformed duplicate registration key")
        self.result = git(self.target, "rev-parse", "HEAD")
        self.close()
        self.closure["implementation_surfaces"] += [INDEX_PATH]
        self.write_closure()
        self.assertIn("TASK_CLOSURE_RESULT_DRIFT", self.errors(self.check()))
        self.write_index([self.task, copy.deepcopy(self.task)])
        self.assertIn("ACTIVE_TASK_DUPLICATE", self.errors(self.check()))


    def test_exact_result_byte_budget_allows_empty_tail_but_not_extra_content(self):
        per_file = 16 * 1024 * 1024
        design_size = (self.target / "design.md").stat().st_size
        paths = [f"src/payload-{index}.bin" for index in range(4)]
        for index, path in enumerate(paths):
            (self.target / path).write_bytes(b"x" * (per_file - design_size if index == 0 else per_file))
        tail = self.target / "zz-empty.txt"
        tail.write_bytes(b"")
        git(self.target, "add", ".")
        git(self.target, "commit", "-qm", "exactly bounded implementation")
        self.result = git(self.target, "rev-parse", "HEAD")
        self.close()
        self.closure["implementation_surfaces"] = paths + ["zz-empty.txt"]
        self.write_closure()
        self.assertEqual(self.errors(self.check()), set())
        checked = self.check()
        selected = ["design.md", *paths, "zz-empty.txt"]
        self.assertEqual(checked.git.snapshot_sha256(self.result, selected, byte_limits=(per_file, 4 * per_file)), self.snapshot(selected))
        original_binding = copy.deepcopy(self.closure["repository_binding"])
        self.closure["repository_binding"].update(kind="selected-file-snapshot", selected_paths=selected, snapshot_sha256=self.snapshot(selected))
        self.write_closure()
        self.assertEqual(self.errors(self.check()), set())
        self.closure["repository_binding"] = original_binding
        tail.write_bytes(b"x")
        git(self.target, "add", "zz-empty.txt")
        git(self.target, "commit", "-qm", "one byte above total budget")
        self.closure["repository_binding"]["result_revision"] = git(self.target, "rev-parse", "HEAD")
        self.write_closure()
        self.assertIn("TASK_CLOSURE_RESULT_DRIFT", self.errors(self.check()))
        checked = self.check()
        self.assertIsNone(checked.git.snapshot_sha256(self.closure["repository_binding"]["result_revision"], selected, byte_limits=(per_file, 4 * per_file)))
        original_binding = copy.deepcopy(self.closure["repository_binding"])
        self.closure["repository_binding"].update(kind="selected-file-snapshot", selected_paths=selected, snapshot_sha256=self.snapshot(selected))
        self.write_closure()
        self.assertIn("TASK_CLOSURE_SNAPSHOT_LIMIT", self.errors(self.check()))
        self.closure["repository_binding"] = original_binding
        tail.unlink()
        git(self.target, "add", "zz-empty.txt")
        git(self.target, "commit", "-qm", "absent trailing path consumes no bytes")
        self.closure["repository_binding"]["result_revision"] = git(self.target, "rev-parse", "HEAD")
        self.write_closure()
        self.assertEqual(self.errors(self.check()), set())


    def test_snapshot_file_budget_rejects_oversized_sources_without_opening_them(self):
        self.close()
        path = self.target / "oversized.bin"
        path.write_bytes(b"x" * (16 * 1024 * 1024 + 1))
        selected = ["design.md", "src/example.txt", "oversized.bin"]
        self.closure["implementation_surfaces"].append("oversized.bin")
        self.closure["repository_binding"].update(kind="selected-file-snapshot", selected_paths=selected, snapshot_sha256=self.snapshot(selected))
        self.write_closure()
        original = Path.open
        def bounded_open(candidate, *args, **kwargs):
            if candidate == path:
                raise AssertionError("oversized snapshot must not be opened")
            return original(candidate, *args, **kwargs)
        with patch.object(Path, "open", bounded_open):
            self.assertIn("TASK_CLOSURE_SNAPSHOT_LIMIT", self.errors(self.check()))


    def test_historical_publication_retains_immutable_observation_when_ref_moves(self):
        self.close()
        self.closure["delivery"]["publication"] = "published"
        remote = "refs/remotes/origin/main"
        git(self.target, "update-ref", remote, self.result)
        receipt = {"schema_version": 1, "record_kind": "alatyr-publication-receipt", "task_id": "fixture-task", "operation_id": self.task["operation_id"], "remote_ref": remote, "observed_revision": self.result, "observed_at": "2026-01-01T00:00:00Z"}
        path = self.target / "publication.json"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        self.closure["publication_evidence"] = [self.bind(path)]
        self.write_closure()
        self.assertEqual(self.errors(self.check()), set())
        git(self.target, "commit", "--allow-empty", "-qm", "later unrelated publication")
        git(self.target, "update-ref", remote, "HEAD")
        for available in [True, False]:
            if not available:
                git(self.target, "update-ref", "-d", remote)
            checked = self.check(selected=False)
            self.assertEqual(self.errors(checked), set())
            self.assertIn("TASK_PUBLICATION_HISTORICAL", {finding.code for finding in checked.findings})
            self.assertIn("TASK_CLOSURE_PUBLICATION", self.errors(self.check()))
        receipt["observed_revision"] = self.base
        path.write_text(json.dumps(receipt), encoding="utf-8")
        self.closure["publication_evidence"] = [self.bind(path)]
        self.write_closure()
        self.assertIn("TASK_CLOSURE_PUBLICATION", self.errors(self.check(selected=False)))

    def test_publication_revision_expression_is_not_a_literal_tracking_ref(self):
        self.close()
        self.closure["delivery"]["publication"] = "published"
        git(self.target, "update-ref", "refs/remotes/origin/main", self.result)
        receipt = {"schema_version": 1, "record_kind": "alatyr-publication-receipt", "task_id": "fixture-task", "operation_id": self.task["operation_id"], "remote_ref": "refs/remotes/origin/main~1", "observed_revision": self.result, "observed_at": "2026-01-01T00:00:00Z"}
        path = self.target / "publication.json"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        self.closure["publication_evidence"] = [self.bind(path)]
        self.write_closure()
        for selected in (True, False):
            self.assertIn("TASK_CLOSURE_PUBLICATION", self.errors(self.check(selected=selected)))


    @unittest.skipIf(os.name == "nt", "literal backslash filename is a POSIX alias regression")
    def test_closure_path_cannot_alias_a_different_implementation_file(self):
        self.close()
        wrong = self.target / "src\\example.txt"
        wrong.write_text(json.dumps(self.closure), encoding="utf-8")
        self.task["completion_evidence"] = self.bind(wrong)
        self.write_index()
        (self.target / "src/example.txt").write_text("changed implementation")
        self.assertTrue(self.errors(self.check()))
        self.closure["repository_binding"].update(kind="selected-file-snapshot", selected_paths=["design.md"], snapshot_sha256=self.snapshot(["design.md"]))
        wrong.write_text(json.dumps(self.closure), encoding="utf-8")
        self.task["completion_evidence"] = self.bind(wrong)
        self.write_index()
        self.assertTrue(self.errors(self.check()))
        self.closure["implementation_surfaces"] = ["src\\example.txt"]
        self.write_closure()
        self.assertIn("ACTIVE_TASK_SCHEMA", self.errors(self.check()))


    def test_historical_snapshot_candidate_uses_the_same_git_read_budget(self):
        self.close()
        path = self.target / "snapshot.bin"
        path.write_bytes(b"x" * (16 * 1024 * 1024 + 1))
        git(self.target, "add", "snapshot.bin")
        git(self.target, "commit", "-qm", "oversized historical input")
        selected = ["design.md", "src/example.txt", "snapshot.bin"]
        self.closure["implementation_surfaces"].append("snapshot.bin")
        self.closure["repository_binding"].update(kind="selected-file-snapshot", selected_paths=selected, snapshot_sha256=self.snapshot(selected))
        self.write_closure()
        path.write_bytes(b"smaller worktree")
        original = subprocess.run
        def no_unbounded_blob(command, *args, **kwargs):
            if len(command) > 1 and command[0] == "git" and command[1] == "show" and any(str(part).endswith(":snapshot.bin") for part in command):
                raise AssertionError("historical candidate must not read an unbounded Git blob")
            if command[:4] == ["git", "cat-file", "blob", git_revision + ":snapshot.bin"]:
                raise AssertionError("oversized Git blob must not be opened")
            return original(command, *args, **kwargs)
        git_revision = git(self.target, "rev-parse", "HEAD")
        with patch("target_validation_support.subprocess.run", side_effect=no_unbounded_blob):
            checked = self.check(selected=False)
        self.assertEqual(self.errors(checked), set())
        codes = {finding.code for finding in checked.findings}
        self.assertIn("TASK_CLOSURE_SNAPSHOT_HISTORICAL", codes)
        self.assertNotIn("TASK_CLOSURE_SNAPSHOT_COMMIT_CANDIDATE", codes)


    def test_bounded_snapshot_reuses_the_existing_git_view_without_status_rescans(self):
        checked = self.check()
        original = subprocess.run
        def no_status_scan(command, *args, **kwargs):
            if command[:2] == ["git", "status"]:
                raise AssertionError("selected snapshot must reuse the existing repository evidence view")
            return original(command, *args, **kwargs)
        paths = ["design.md", "src/example.txt"]
        with patch("target_validation_support.subprocess.run", side_effect=no_status_scan):
            first = checked.git.snapshot_sha256(self.result, paths, byte_limits=(16 * 1024 * 1024, 64 * 1024 * 1024))
            second = checked.git.snapshot_sha256(self.result, paths, byte_limits=(16 * 1024 * 1024, 64 * 1024 * 1024))
        self.assertEqual(first, self.snapshot(paths))
        self.assertEqual(first, second)



if __name__ == "__main__":
    unittest.main()

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


class ActiveTaskTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.target = Path(self.directory.name)
        git(self.target, "init", "-q")
        git(self.target, "config", "user.email", "fixture@example.invalid")
        git(self.target, "config", "user.name", "Fixture")
        (self.target / ".ai").mkdir()
        shutil.copy2(ROOT / "templates/target/.ai/.gitignore", self.target / ".ai/.gitignore")
        (self.target / "design.md").write_text("accepted design\n", encoding="utf-8")
        git(self.target, "add", ".")
        git(self.target, "commit", "-qm", "design")
        self.base = git(self.target, "rev-parse", "HEAD")
        (self.target / "src").mkdir()
        (self.target / "src/example.txt").write_text("implementation\n", encoding="utf-8")
        git(self.target, "add", ".")
        git(self.target, "commit", "-qm", "implement")
        self.result = git(self.target, "rev-parse", "HEAD")
        self.task = {"task_id": "fixture-task", "state": "active", "task_class": "standard-task", "problem_model": None, "completion_evidence": None, "canonical_owners": ["design.md"], "changed_fact_ids": ["change-1"], "incident_family_id": "none", "predecessor_task_ids": [], "latest_failed_gate_id": "none"}
        descriptor = self.target / ".ai/assistant/analysis-strategies/invariant-first.json"
        descriptor.parent.mkdir(parents=True)
        shutil.copy2(ROOT / "templates/target/.ai/assistant/analysis-strategies/invariant-first.json", descriptor)
        self.model = _model()
        self.task["operation_id"] = self.model["operation_id"]
        self.model_path = self.target / ".ai/.runtime/problem-models/fixture.json"
        self.write_model()
        self.write_index()

    def bind(self, path):
        return {"path": path.relative_to(self.target).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def snapshot(self, paths):
        digest = hashlib.sha256()
        for path in sorted(paths):
            digest.update(path.encode() + b"\0" + (self.target / path).read_bytes() + b"\0")
        return digest.hexdigest()

    def write_model(self):
        _write_model(self.target, self.model_path, self.model)
        self.task["problem_model"] = self.bind(self.model_path)

    def write_index(self, tasks=None):
        path = self.target / INDEX_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema_version": 1, "index_kind": "target-active-task-index", "tasks": [self.task] if tasks is None else tasks}), encoding="utf-8")

    def check(self, *, selected=True, scope="full"):
        checked = changed_index_validator(self.target)
        checked.current_task_id = "fixture-task" if selected else None
        checked.validation_scope = scope
        phase = next(phase for phase in checked.validation_phases(None, "core", set()) if phase.phase_id == "active-tasks")
        phase.run()
        return checked

    def errors(self, checked):
        return {finding.code for finding in checked.findings if finding.level == "error"}

    def close(self):
        self.closure = {"schema_version": 1, "record_kind": "alatyr-task-closure", "task_id": "fixture-task", "delivery": {"implementation": "complete", "evidence_finalization": "final", "publication": "not-requested"}, "engineering_evidence": {"state": "skipped", "materiality": "non-material", "reason": "No reusable finding beyond existing design", "record_ids": [], "preserved_owners": [], "next_safe_action": "none"}, "repository_binding": {"kind": "commit", "binding_state": "final", "base_revision": self.base, "result_revision": self.result, "prior_bindings": []}, "publication_evidence": [], "canonical_owners": ["design.md"], "implementation_surfaces": ["src/example.txt"], "changed_fact_ids": ["change-1"], "incident_family_id": "none", "predecessor_task_ids": [], "latest_failed_gate_id": "none", "knowledge_review": {"state": "not-required", "reason": "Existing owner is already routable", "candidate_ids": []}}
        self.task["state"] = "closed"
        self.closure["operation_id"] = self.task["operation_id"]
        self.closure["engineering_evidence"]["preservation"] = []
        self.closure["architecture_review"] = {"state": "not-required", "reason": "No architecture item changes in this fixture", "item_ids": []}
        self.write_closure()

    def write_closure(self):
        path = self.target / ".ai/assistant/task-closures/fixture-task.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.closure), encoding="utf-8")
        self.task["completion_evidence"] = self.bind(path)
        self.write_index()

    def test_registered_active_and_closed_tasks_pass_without_publication(self):
        self.assertEqual(self.errors(self.check()), set())
        self.close()
        self.assertEqual(self.errors(self.check()), set())

    def test_empty_registry_does_not_accept_explicit_task(self):
        self.write_index([])
        self.assertIn("ACTIVE_TASK_UNREGISTERED", self.errors(self.check()))
        result = subprocess.run([sys.executable, str(ROOT / "tools/validate_target_adapter.py"), "--target", str(self.target), "--task-id", "fixture-task", "--validation-phase", "migration-staging"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ACTIVE_TASK_UNREGISTERED", result.stdout + result.stderr)

    def test_invalid_active_model_is_selected_automatically(self):
        self.model["incident"]["mode"] = "corrective"
        self.write_model()
        self.write_index()
        self.assertIn("ANALYSIS_PROBLEM_MODEL_INVALID", self.errors(self.check(selected=False)))

    def test_open_proof_allowed_during_work_but_not_at_closure(self):
        self.model["proof_obligations"][0]["status"] = "open"
        self.model["proof_obligations"][0]["evidence_refs"] = []
        self.write_model()
        self.write_index()
        self.assertNotIn("ANALYSIS_PROBLEM_MODEL_INCOMPLETE", self.errors(self.check()))
        self.close()
        self.assertIn("ANALYSIS_REQUIRED_OBLIGATION_OPEN", self.errors(self.check()))

    def test_cross_task_and_stale_artifact_binding_rejected(self):
        self.model["task_binding"]["task_ids"] = ["other-task"]
        self.write_model()
        self.write_index()
        self.assertIn("ACTIVE_TASK_MODEL_LINEAGE", self.errors(self.check()))
        self.model_path.write_text("{}", encoding="utf-8")
        self.assertIn("ACTIVE_TASK_DIGEST", self.errors(self.check()))

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

    def test_boundaries_and_unrelated_closed_records_not_opened_in_changed_scope(self):
        small = dict(self.task, task_class="small-task", problem_model=None)
        self.write_index([dict(small, task_id=f"task-{i}") for i in range(128)])
        self.assertEqual(self.errors(self.check(selected=False)), set())
        self.write_index([dict(small, task_id=f"task-{i}") for i in range(129)])
        self.assertIn("ACTIVE_TASK_SCHEMA", self.errors(self.check(selected=False)))
        self.close()
        git(self.target, "add", ".")
        git(self.target, "commit", "-qm", "close task")
        observed = []
        original = TargetRepositoryView.read_json_result
        def observe(view, path):
            observed.append(path)
            return original(view, path)
        with patch.object(TargetRepositoryView, "read_json_result", observe):
            self.check(selected=False, scope="changed")
        self.assertFalse(any(str(path).endswith("fixture-task.json") for path in observed))

    def test_class_downgrade_cannot_hide_open_obligations(self):
        git(self.target, "add", ".")
        git(self.target, "commit", "-qm", "register task")
        self.task.update(task_class="small-task", problem_model=None)
        self.write_index()
        self.assertIn("ACTIVE_TASK_CLASS", self.errors(self.check()))
        self.assertIn("ACTIVE_TASK_CLASS", self.errors(self.check(selected=False, scope="changed")))

    def test_missing_self_cyclic_and_false_gate_lineage_rejected(self):
        for predecessor in ["missing-task", "fixture-task"]:
            self.task["predecessor_task_ids"] = [predecessor]
            self.write_index()
            self.assertIn("ACTIVE_TASK_PREDECESSOR", self.errors(self.check()))
        other = dict(self.task, task_id="other-task", task_class="small-task", problem_model=None, predecessor_task_ids=["fixture-task"])
        self.task["predecessor_task_ids"] = ["other-task"]
        self.write_index([self.task, other])
        self.assertIn("ACTIVE_TASK_PREDECESSOR", self.errors(self.check()))
        self.task["predecessor_task_ids"] = []
        self.task["latest_failed_gate_id"] = "fake-gate"
        self.write_index()
        self.assertIn("ACTIVE_TASK_PROJECTION", self.errors(self.check()))

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

    def test_root_edit_does_not_reopen_unchanged_historical_model(self):
        self.close()
        git(self.target, "add", ".")
        git(self.target, "commit", "-qm", "close task")
        self.model_path.unlink()
        additional = dict(self.task, task_id="small-new-task", task_class="small-task", problem_model=None, completion_evidence=None, state="active")
        self.write_index([self.task, additional])
        checked = self.check(selected=False, scope="changed")
        self.assertEqual(self.errors(checked), set())
        self.assertNotIn(self.model_path.absolute(), checked.context._bytes_cache)

    def test_bounded_index_and_context_reads_at_and_above_byte_limit(self):
        raw = (self.target / INDEX_PATH).read_bytes()
        limit = 512 * 1024
        for length, accepted in [(limit - 1, True), (limit, True), (limit + 1, False)]:
            (self.target / INDEX_PATH).write_bytes(raw + b" " * (length - len(raw)))
            checked = self.check()
            self.assertEqual("ACTIVE_TASK_INDEX_LIMIT" not in self.errors(checked), accepted)
        path = self.target / "large.bin"
        path.write_bytes(b"x" * (limit + 1))
        view = TargetRepositoryView(self.target)
        with patch.object(Path, "open", side_effect=AssertionError("oversized file must not be opened")):
            self.assertIsNone(view.read_bytes_result(path, max_bytes=limit).value)

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

    def test_model_facts_cannot_be_replaced_with_agreeing_unrelated_headers(self):
        self.close()
        self.task["changed_fact_ids"] = ["unrelated-fact"]
        self.closure["changed_fact_ids"] = ["unrelated-fact"]
        self.write_closure()
        self.assertIn("ACTIVE_TASK_PROJECTION", self.errors(self.check()))

    def test_active_registration_cannot_be_removed_without_terminal_disposition(self):
        self.model["proof_obligations"][0].update(status="open", evidence_refs=[])
        self.write_model()
        self.write_index()
        git(self.target, "add", ".")
        git(self.target, "commit", "-qm", "register active work")
        self.write_index([])
        self.assertIn("ACTIVE_TASK_REMOVED", self.errors(self.check(selected=False, scope="changed")))
        self.close()
        self.closure["delivery"].update(implementation="blocked", evidence_finalization="blocked")
        self.closure["engineering_evidence"].update(state="blocked", next_safe_action="Owner decides whether work can resume")
        self.write_closure()
        self.assertEqual(self.errors(self.check(selected=False, scope="changed")), set())

    def test_predecessor_requires_real_model_identity_and_ordering(self):
        prior = copy.deepcopy(self.model)
        prior["model_id"] = "prior-model"
        prior["task_binding"]["task_ids"] = ["prior-task"]
        prior["active_projection"]["path"] = ".ai/.runtime/problem-model-projections/prior-model.json"
        prior["incident"].update(mode="new", family_id="incident-1", trigger="reported-defect")
        path = self.target / ".ai/.runtime/problem-models/prior.json"
        _write_model(self.target, path, prior)
        predecessor = dict(self.task, task_id="prior-task", problem_model=self.bind(path), incident_family_id="incident-1")
        self.model["incident"].update(mode="continuation", family_id="incident-1", trigger="reported-defect", corrective_iteration=1, predecessor_model_ids=["prior-model"])
        self.task.update(incident_family_id="incident-1", predecessor_task_ids=["prior-task"])
        self.write_model()
        self.write_index([self.task, predecessor])
        self.assertEqual(self.errors(self.check()), set())
        self.model["incident"]["predecessor_model_ids"] = ["missing-model"]
        self.write_model()
        self.write_index([self.task, predecessor])
        self.assertIn("ACTIVE_TASK_PREDECESSOR", self.errors(self.check()))
        predecessor.update(task_class="small-task", problem_model=None)
        self.write_index([self.task, predecessor])
        self.assertIn("ACTIVE_TASK_PREDECESSOR", self.errors(self.check()))

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

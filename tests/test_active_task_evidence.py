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


class ActiveTaskTests(fixture.ActiveTaskFixture):
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



if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from tests.active_task_fixture import ActiveTaskFixture, ROOT
from tests.test_behavior_acceptance import original_case

sys.path.insert(0, str(ROOT / "tools"))
from archive_task_evidence import prepare
from check_change_packages import changed_index_validator, git
from support_write_transaction import SupportTransaction
from render_context_catalogs import build_directory_catalog_contents
from target_adapter_validation.active_tasks import validate_active_tasks
from target_adapter_validation.harness_scenarios.analysis_strategies import _write_model


class TaskAcceptanceBoundaryTests(ActiveTaskFixture):
    def test_retained_witnesses_stay_outside_routine_context_catalogs(self):
        self.close()
        contents = build_directory_catalog_contents(self.target / ".ai/assistant", "assistant")
        self.assertFalse(any(path.startswith("task-evidence/") for path in contents))
        self.assertNotIn("task-evidence", contents["context-index.json"])

    def test_changed_scope_reopens_only_the_changed_retained_witness(self):
        self.close()
        git(self.target, "add", "."); git(self.target, "commit", "-qm", "retain task")
        for name in ("model", "projection"):
            path = self.target / self.closure["analysis_witness"][name]["path"]
            original = path.read_bytes(); path.write_bytes(original + b" ")
            with self.subTest(name=name):
                self.assertIn("ACTIVE_TASK_DIGEST", self.errors(self.check(selected=False, scope="changed")))
            path.write_bytes(original)
        self.assertEqual(self.errors(self.check(selected=False, scope="changed")), set())

    def test_legacy_history_does_not_block_an_unrelated_selected_current_task(self):
        current_model, current_task = copy.deepcopy(self.model), copy.deepcopy(self.task)
        self.task["task_id"] = "legacy-task"
        self.model["task_binding"]["task_ids"] = ["legacy-task"]
        self.model["schema_version"] = 4
        self.model["active_projection"]["schema_version"] = 3
        self.model.pop("behavior_review"); self.model.pop("original_case")
        self.write_model(); self.close()
        legacy_task = copy.deepcopy(self.task)
        self.model, self.task = current_model, current_task
        self.write_model(); self.close()
        self.write_index([self.task, legacy_task])
        checked = changed_index_validator(self.target)
        checked.require_task_acceptance = True
        checked.current_task_id = "fixture-task"
        checked.current_task_class = "standard-task"
        validate_active_tasks(checked)
        self.assertEqual(self.errors(checked), set())
        checked = changed_index_validator(self.target)
        checked.require_task_acceptance = True; checked.current_task_id = "legacy-task"
        validate_active_tasks(checked)
        self.assertIn("TASK_ACCEPTANCE_LEGACY_MODEL", self.errors(checked))

    def test_clean_clone_full_history_needs_no_ignored_runtime_files(self):
        self.close()
        git(self.target, "add", ".")
        git(self.target, "commit", "-qm", "retain closed task evidence")
        clone = self.target.parent / (self.target.name + "-clone")
        self.addCleanup(shutil.rmtree, clone, True)
        subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(self.target), str(clone)], check=True)
        self.assertFalse((clone / ".ai/.runtime").exists())
        validator = changed_index_validator(clone)
        validator.validation_scope = "full"
        validate_active_tasks(validator)
        self.assertEqual(self.errors(validator), set())

    def test_active_missing_model_cannot_use_a_closed_witness(self):
        self.close()
        self.task.update(state="active", completion_evidence=None)
        self.write_index()
        shutil.rmtree(self.target / ".ai/.runtime")
        self.assertIn("ACTIVE_TASK_BINDING", self.errors(self.check(selected=False)))

    def test_missing_and_tampered_durable_projection_fail_closed(self):
        self.close()
        projection = self.target / self.closure["analysis_witness"]["projection"]["path"]
        projection.unlink()
        self.assertIn("ACTIVE_TASK_BINDING", self.errors(self.check(selected=False)))
        projection.write_text("{}")
        self.assertIn("ACTIVE_TASK_DIGEST", self.errors(self.check(selected=False)))

    def test_rehashed_unrelated_projection_and_model_lineage_are_rejected(self):
        self.close()
        projection = self.target / self.closure["analysis_witness"]["projection"]["path"]
        value = json.loads(projection.read_text()); value["operation_id"] = "unrelated"
        projection.write_text(json.dumps(value))
        self.closure["analysis_witness"]["projection"] = self.bind(projection)
        self.model_path.unlink()
        self.write_closure()
        self.assertIn("ANALYSIS_PROBLEM_MODEL_PROJECTION_INVALID", self.errors(self.check(selected=False)))

    def test_original_complaint_remains_open_despite_green_proof_obligations(self):
        self.model["original_case"] = original_case()
        self.write_model()
        self.close()
        self.assertIn("TASK_BEHAVIOR_ACCEPTANCE", self.errors(self.check()))
        result = subprocess.run([sys.executable, str(ROOT / "tools/validate_target_adapter.py"), "--target", str(self.target), "--task-id", "fixture-task", "--task-class", "standard-task", "--require-task-acceptance", "--validation-phase", "migration-staging", "--json"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertIn("TASK_BEHAVIOR_ACCEPTANCE", {item["code"] for item in payload["findings"]})
        self.assertEqual(payload["task_acceptance"]["state"], "blocked")

    def test_archiver_preserves_exact_model_digest_and_rejects_stale_plan(self):
        self.close()
        self.closure.pop("analysis_witness")
        self.model_path.unlink(missing_ok=True)
        self.write_model()
        # Publish the legacy-style closure without the fixture's auto-retention.
        closure_path = self.target / self.task["completion_evidence"]["path"]
        closure_path.write_text(json.dumps(self.closure))
        self.task["completion_evidence"] = self.bind(closure_path)
        self.write_index()
        plan = prepare(self.target, "fixture-task", "owner:retention-reviewed")
        index = self.target / ".ai/assistant/active-tasks.json"
        original = index.read_bytes()
        index.write_bytes(original + b" ")
        with self.assertRaisesRegex(ValueError, "changed while planning"):
            SupportTransaction(self.target).apply(plan.outputs, expected_inputs=plan.inputs)
        index.write_bytes(original)
        SupportTransaction(self.target).apply(plan.outputs, expected_inputs=plan.inputs)
        updated = json.loads(closure_path.read_text())
        self.assertEqual(updated["analysis_witness"]["model"]["sha256"], hashlib.sha256(self.model_path.read_bytes()).hexdigest())
        shutil.rmtree(self.target / ".ai/.runtime")
        self.assertEqual(self.errors(self.check(selected=False)), set())

    def test_closed_predecessor_is_resolved_from_durable_witness(self):
        self.close()
        prior = copy.deepcopy(self.model)
        prior.update(model_id="prior-model", operation_id="prior-operation", original_case=dict(original_case(), status="verified-fixed", evidence_refs=["fixture:original-case"]))
        prior["task_binding"]["task_ids"] = ["prior-task"]
        prior["active_projection"]["path"] = ".ai/.runtime/problem-model-projections/prior-model.json"
        prior["incident"].update(mode="new", family_id="incident-family", trigger="reported-defect")
        path = self.target / ".ai/.runtime/problem-models/prior-model.json"
        _write_model(self.target, path, prior)
        prior_task = copy.deepcopy(self.task)
        prior_task.update(task_id="prior-task", operation_id="prior-operation", problem_model=self.bind(path), incident_family_id="incident-family")
        directory = self.target / ".ai/assistant/task-evidence/prior-task"
        directory.mkdir(parents=True)
        retained_model, retained_projection = directory / "model.json", directory / "projection.json"
        retained_model.write_bytes(path.read_bytes())
        retained_projection.write_bytes((self.target / prior["active_projection"]["path"]).read_bytes())
        closure = copy.deepcopy(self.closure)
        closure.update(task_id="prior-task", operation_id="prior-operation", incident_family_id="incident-family", analysis_witness={"model": self.bind(retained_model), "projection": self.bind(retained_projection), "retention_review": "fixture:review"})
        closure_path = directory / "closure.json"; closure_path.write_text(json.dumps(closure))
        prior_task["completion_evidence"] = self.bind(closure_path)
        path.unlink(); (self.target / prior["active_projection"]["path"]).unlink()
        self.model.update(original_case=original_case())
        self.model["incident"].update(mode="continuation", family_id="incident-family", trigger="reported-defect", corrective_iteration=1, predecessor_model_ids=["prior-model"])
        self.task.update(state="active", completion_evidence=None, incident_family_id="incident-family", predecessor_task_ids=["prior-task"])
        self.write_model(); self.write_index([self.task, prior_task])
        self.assertEqual(self.errors(self.check()), set())

    def test_archiver_rejects_ignored_durable_destinations(self):
        self.close()
        ignore = self.target / ".ai/.gitignore"
        ignore.write_text(ignore.read_text() + "\nassistant/task-evidence/\n")
        with self.assertRaisesRegex(ValueError, "retainable by Git"):
            prepare(self.target, "fixture-task", "owner:retention-reviewed")

    def test_archiver_rejects_dot_path_task_identities(self):
        for identity in (".", ".."):
            with self.subTest(identity=identity), self.assertRaisesRegex(ValueError, "identity"):
                prepare(self.target, identity, "owner:retention-reviewed")

    def test_archiver_cli_retains_witnesses_without_runtime_dependency(self):
        self.close()
        shutil.copy2(ROOT / "templates/target/.ai/alatyr.yaml", self.target / ".ai/alatyr.yaml")
        result = subprocess.run([
            sys.executable, str(ROOT / "tools/archive_task_evidence.py"),
            "--target", str(self.target), "--task-id", "fixture-task",
            "--retention-review", "owner:retention-reviewed", "--write",
            "--migration-staging",
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["write"])
        shutil.rmtree(self.target / ".ai/.runtime")
        self.assertEqual(self.errors(self.check(selected=False)), set())

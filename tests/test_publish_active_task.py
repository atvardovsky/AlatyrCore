from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from publish_active_task import prepare, INDEX
from support_write_transaction import SupportTransaction
from tests.active_task_fixture import ActiveTaskFixture


class PublishActiveTaskTests(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        self.model_path.unlink()
        self.model_path = self.target / ".ai/.runtime/problem-models/fixture-problem.json"
        self.write_model()
        self.write_index()
        self.draft = self.target / ".ai/.runtime/drafts/task.json"
        self.draft.parent.mkdir(parents=True)
        self.write_draft()

    def write_draft(self, model=None):
        self.draft.write_text(json.dumps(self.model if model is None else model), encoding="utf-8")

    def plan(self):
        return prepare(self.target, "fixture-task", self.draft.relative_to(self.target).as_posix())

    def test_pending_model_publishes_exact_projection_without_granting_acceptance(self):
        self.model["proof_obligations"][0].update(status="open", evidence_refs=[])
        self.model["review_results"][0].update(status="pending", evidence_refs=[])
        self.write_draft()
        plan = self.plan()
        self.assertEqual(len(plan.outputs), 3)
        SupportTransaction(self.target).apply(plan.outputs, expected_inputs=plan.inputs)
        checked = self.check()
        self.assertEqual(self.errors(checked), set(), checked.findings)
        model = json.loads(self.model_path.read_text())
        projection = json.loads((self.target / model["active_projection"]["path"]).read_text())
        self.assertEqual(model["proof_obligations"][0]["status"], "open")
        self.assertEqual(projection["payload"]["required_reviews"][0]["status"], "pending")
        self.assertEqual(projection["source_model"]["sha256"], hashlib.sha256(self.model_path.read_bytes()).hexdigest())

    def test_invalid_review_and_lifecycle_drafts_leave_all_files_unchanged(self):
        before = {path: path.read_bytes() for path in (self.model_path, self.target / INDEX, self.target / self.model["active_projection"]["path"])}
        for field in ("review", "lifecycle"):
            mutant = copy.deepcopy(self.model)
            if field == "review":
                mutant["review_results"][0]["status"] = "open"
            else:
                mutant["lifecycle_model"]["required"] = True
                mutant["lifecycle_model"]["required_outcomes"] = ["success", "rejection", "deferral", "expiry", "recovery", "failure"]
            self.write_draft(mutant)
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.plan()
            self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_closed_task_and_shared_model_cannot_be_modified(self):
        self.close()
        with self.assertRaisesRegex(ValueError, "closed"):
            self.plan()
        self.task.update(state="active", completion_evidence=None)
        peer = dict(self.task, task_id="peer-task")
        self.write_index([self.task, peer])
        with self.assertRaisesRegex(ValueError, "another task"):
            self.plan()

    def test_unbound_model_edit_and_scope_mismatch_fail(self):
        self.model_path.write_text("{}")
        with self.assertRaisesRegex(ValueError, "digest binding"):
            self.plan()
        self.write_model()
        self.write_index()
        self.model["changed_facts"][0]["id"] = "other-fact"
        self.write_draft()
        with self.assertRaisesRegex(ValueError, "header differs"):
            self.plan()

    def test_projection_is_derived_even_if_old_hash_is_correct_but_payload_wrong(self):
        path = self.target / self.model["active_projection"]["path"]
        projection = json.loads(path.read_text())
        projection["payload"]["proof_obligations"][0]["status"] = "blocked"
        path.write_text(json.dumps(projection))
        self.assertIn("ANALYSIS_PROBLEM_MODEL_PROJECTION_INVALID", self.errors(self.check()))
        plan = self.plan()
        SupportTransaction(self.target).apply(plan.outputs, expected_inputs=plan.inputs)
        self.assertEqual(self.errors(self.check()), set())

    def test_draft_and_peer_index_changes_invalidate_plan_without_writes(self):
        for changed in (self.draft, self.target / INDEX):
            self.write_draft()
            self.write_index()
            plan = self.plan()
            old_model = self.model_path.read_bytes()
            changed.write_bytes(changed.read_bytes() + b"\n")
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "changed while planning"):
                SupportTransaction(self.target).apply(plan.outputs, expected_inputs=plan.inputs)
            self.assertEqual(self.model_path.read_bytes(), old_model)

    def test_new_registration_is_explicit_and_preview_does_not_write(self):
        self.write_index([])
        with self.assertRaisesRegex(ValueError, "registration draft"):
            self.plan()
        registration = self.target / ".ai/.runtime/drafts/registration.json"
        registration.write_text(json.dumps(self.task))
        plan = prepare(self.target, "fixture-task", self.draft.relative_to(self.target).as_posix(), registration.relative_to(self.target).as_posix())
        self.assertEqual(json.loads((self.target / INDEX).read_text())["tasks"], [])
        SupportTransaction(self.target).apply(plan.outputs, expected_inputs=plan.inputs)
        self.assertEqual(self.errors(self.check()), set())

    def test_new_registration_cannot_add_dangling_or_cyclic_lineage(self):
        self.write_index([])
        registration = self.target / ".ai/.runtime/drafts/registration.json"
        for predecessor in ("missing-task", "fixture-task"):
            registration.write_text(json.dumps(dict(self.task, predecessor_task_ids=[predecessor])))
            with self.subTest(predecessor=predecessor), self.assertRaisesRegex(ValueError, "predecessor graph"):
                prepare(self.target, "fixture-task", self.draft.relative_to(self.target).as_posix(), registration.relative_to(self.target).as_posix())
            self.assertEqual(json.loads((self.target / INDEX).read_text())["tasks"], [])

    def test_existing_runtime_filename_is_preserved_and_successor_dependencies_block(self):
        previous_path = self.model_path
        self.model_path = self.model_path.with_name("existing-runtime-name.json")
        self.write_model()
        self.write_index()
        plan = self.plan()
        self.assertIn(self.model_path, plan.outputs)
        self.assertNotIn(previous_path, plan.outputs)
        SupportTransaction(self.target).apply(plan.outputs, expected_inputs=plan.inputs)
        self.assertEqual(self.errors(self.check()), set())
        self.task = json.loads((self.target / INDEX).read_text())["tasks"][0]
        successor = dict(self.task, task_id="successor", predecessor_task_ids=["fixture-task"])
        self.write_index([self.task, successor])
        with self.assertRaisesRegex(ValueError, "registered successors"):
            self.plan()

    def test_portable_case_aliases_cannot_overwrite_peer_models_or_replace_drafts(self):
        alias = ".ai/.runtime/problem-models/FIXTURE-PROBLEM.json"
        (self.target / alias).write_bytes(self.model_path.read_bytes())
        with self.assertRaisesRegex(ValueError, "separate from published outputs"):
            prepare(self.target, "fixture-task", alias)
        model = copy.deepcopy(self.model)
        model.update(model_id="FIXTURE-PROBLEM", task_binding={"task_ids": ["peer-task"], "workstream_ids": []})
        model["active_projection"]["path"] = ".ai/.runtime/problem-model-projections/FIXTURE-PROBLEM.json"
        self.write_draft(model)
        registration = self.target / ".ai/.runtime/drafts/registration.json"
        registration.write_text(json.dumps(dict(self.task, task_id="peer-task")))
        before = self.model_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "another task"):
            prepare(self.target, "peer-task", self.draft.relative_to(self.target).as_posix(), registration.relative_to(self.target).as_posix())
        self.assertEqual(self.model_path.read_bytes(), before)

    def test_existing_projection_ownership_is_checked_before_overwrite(self):
        model = copy.deepcopy(self.model)
        model.update(model_id="new-model", task_binding={"task_ids": ["new-task"], "workstream_ids": []})
        model["active_projection"]["path"] = ".ai/.runtime/problem-model-projections/new-model.json"
        self.write_draft(model)
        projection = self.target / model["active_projection"]["path"]
        original = (self.target / self.model["active_projection"]["path"]).read_bytes()
        projection.write_bytes(original)
        registration = self.target / ".ai/.runtime/drafts/registration.json"
        registration.write_text(json.dumps(dict(self.task, task_id="new-task")))
        with self.assertRaisesRegex(ValueError, "projection belongs to another model"):
            prepare(self.target, "new-task", self.draft.relative_to(self.target).as_posix(), registration.relative_to(self.target).as_posix())
        self.assertEqual(projection.read_bytes(), original)

    def test_cli_preview_and_malformed_json_are_non_mutating(self):
        command = [sys.executable, str(ROOT / "tools/alatyr.py"), "publish-task", "--target", str(self.target), "--task-id", "fixture-task", "--draft", self.draft.relative_to(self.target).as_posix()]
        before = self.model_path.read_bytes()
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["acceptance_granted"])
        self.assertEqual(before, self.model_path.read_bytes())
        for bad in ("[]", '{"model_id":"one","model_id":"two"}', '{"bad":'):
            self.draft.write_text(bad)
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)

    def test_malformed_registration_fields_are_rejected_before_header_operations(self):
        self.write_index([])
        registration = self.target / ".ai/.runtime/drafts/registration.json"
        for field in ("changed_fact_ids", "canonical_owners", "predecessor_task_ids"):
            for value in ([{}], {}, None, True, 4):
                registration.write_text(json.dumps(dict(self.task, **{field: value})))
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    prepare(self.target, "fixture-task", self.draft.relative_to(self.target).as_posix(), registration.relative_to(self.target).as_posix())

    def test_partial_write_rollback_preserves_peer_postimage(self):
        plan = self.plan()
        transaction = SupportTransaction(self.target)
        from support_write_transaction import replace_output
        index = self.target / INDEX
        def fail_index(target, path, expected, desired):
            if path == index:
                self.model_path.write_bytes(b"peer postimage")
                raise OSError("write failure")
            return replace_output(target, path, expected, desired)
        with patch("support_write_transaction.replace_output", side_effect=fail_index), self.assertRaises(OSError):
            transaction.apply(plan.outputs, expected_inputs=plan.inputs)
        self.assertIn(self.model_path.relative_to(self.target).as_posix(), transaction.rollback())
        self.assertEqual(self.model_path.read_bytes(), b"peer postimage")

    def test_public_write_path_publishes_only_local_active_state(self):
        version = (ROOT / "VERSION").read_text().strip()
        schema = (ROOT / "ADAPTER_SCHEMA_VERSION").read_text().strip()
        template = (ROOT / "TEMPLATE_VERSION").read_text().strip()
        (self.target / ".ai/alatyr.yaml").write_text(f"schema_version: {schema}\nframework:\n  version: {version}\n  template_version: {template}\n")
        self.model["review_results"][0].update(status="pending", evidence_refs=[])
        self.write_draft()
        command = [sys.executable, str(ROOT / "tools/alatyr.py"), "publish-task", "--target", str(self.target), "--task-id", "fixture-task", "--draft", self.draft.relative_to(self.target).as_posix(), "--write"]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["acceptance_granted"])
        self.assertEqual(self.errors(self.check()), set())
        self.task = json.loads((self.target / INDEX).read_text())["tasks"][0]
        self.model = json.loads(self.model_path.read_text())
        self.close()
        self.assertIn("ANALYSIS_REQUIRED_REVIEW_OPEN", self.errors(self.check()))

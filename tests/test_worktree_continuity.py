from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from tests.active_task_fixture import ActiveTaskFixture
from publish_active_task import prepare as publish, INDEX
from restore_active_task import prepare as restore
from support_write_transaction import SupportTransaction
from worktree_readiness import readiness
from tests.test_target_delegate import delegate


class WorktreeContinuityTests(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        self.draft = self.target / ".ai/.runtime/drafts/task.json"
        self.draft.parent.mkdir(parents=True)
        self.write_draft()
        versions = {name: (ROOT / name).read_text().strip() for name in ("VERSION", "ADAPTER_SCHEMA_VERSION", "TEMPLATE_VERSION")}
        (self.target / ".ai/alatyr.yaml").write_text(f"schema_version: {versions['ADAPTER_SCHEMA_VERSION']}\nframework:\n  version: {versions['VERSION']}\n  template_version: {versions['TEMPLATE_VERSION']}\ninstallation:\n  state: accepted\n  state_record: .ai/assistant/installation-state.json\n")
        (self.target / ".ai/assistant/installation-state.json").write_text(json.dumps({"current_state": "accepted"}))

    def write_draft(self):
        self.draft.write_text(json.dumps(self.model))

    def plan(self):
        return publish(self.target, "fixture-task", self.draft.relative_to(self.target).as_posix())

    def retained(self):
        plan = publish(self.target, "fixture-task", self.draft.relative_to(self.target).as_posix(), retention_review="reviewed-task-handoff")
        SupportTransaction(self.target).apply(plan.outputs, expected_inputs=plan.inputs)
        self.task = json.loads((self.target / INDEX).read_text())["tasks"][0]
        return plan

    def test_foreign_retained_active_evidence_stays_valid_but_selected_requires_runtime(self):
        self.retained()
        self.model_path.unlink()
        (self.target / self.model["active_projection"]["path"]).unlink()
        self.assertEqual(self.errors(self.check(selected=False)), set())
        self.assertIn("ACTIVE_TASK_REHYDRATION_REQUIRED", self.errors(self.check()))
        plan = restore(self.target, "fixture-task")
        self.assertFalse(self.model_path.exists())
        SupportTransaction(self.target).apply(plan.outputs, expected_inputs=plan.inputs)
        self.assertEqual(self.errors(self.check()), set())

    def test_handoff_refuses_ignored_analysis_dependencies_instead_of_claiming_portability(self):
        from tests.test_analysis_evidence import add_evidence
        add_evidence(self.model, self.target)
        self.write_draft()
        with self.assertRaisesRegex(ValueError, "ignored or unverified analysis artifact"):
            self.retained()

    def test_registered_validation_rejects_a_manually_bound_ignored_analysis_dependency(self):
        from tests.test_analysis_evidence import add_evidence
        self.retained()
        add_evidence(self.model, self.target)
        self.write_model()
        witness = self.task["analysis_handoff"]
        model_file = self.target / witness["model"]["path"]
        projection_file = self.target / witness["projection"]["path"]
        model_file.write_bytes(self.model_path.read_bytes())
        projection_file.write_bytes((self.target / self.model["active_projection"]["path"]).read_bytes())
        witness["model"]["sha256"] = self.task["problem_model"]["sha256"]
        witness["projection"]["sha256"] = hashlib.sha256(projection_file.read_bytes()).hexdigest()
        self.write_index()
        self.assertIn("ACTIVE_TASK_HANDOFF_RETENTION", self.errors(self.check(selected=False)))
        with self.assertRaisesRegex(ValueError, "ignored or unverified"):
            restore(self.target, "fixture-task")

    def test_malformed_retained_model_returns_cli_findings_before_header_operations(self):
        self.retained()
        model_file = self.target / self.task["analysis_handoff"]["model"]["path"]
        for value in (None, 7, {"malformed": True}):
            model = copy.deepcopy(self.model)
            model["task_binding"]["task_ids"] = value
            raw = json.dumps(model).encode()
            model_file.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            self.task["problem_model"]["sha256"] = self.task["analysis_handoff"]["model"]["sha256"] = digest
            self.write_index()
            result = subprocess.run([sys.executable, str(ROOT / "tools/alatyr.py"), "restore-task", "--target", str(self.target), "--task-id", "fixture-task"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("invalid active handoff", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_foreign_active_handoff_still_checks_current_source_artifacts(self):
        from tests.test_analysis_evidence import add_evidence
        ignored_path = add_evidence(self.model, self.target)
        self.model = json.loads(json.dumps(self.model).replace(ignored_path, "design.md"))
        digest = hashlib.sha256((self.target / "design.md").read_bytes()).hexdigest()
        evidence = self.model["analysis_evidence"]
        evidence["probes"][0]["result"]["artifacts"][0]["sha256"] = digest
        evidence["review_challenges"][0]["artifacts"][0]["sha256"] = digest
        self.write_draft()
        self.retained()
        self.model_path.unlink()
        self.assertEqual(self.errors(self.check(selected=False)), set())
        (self.target / "design.md").write_text("changed source input")
        self.assertIn("ANALYSIS_EVIDENCE_ARTIFACT", self.errors(self.check(selected=False)))

    def test_retained_projection_and_runtime_drift_are_not_ignored(self):
        self.retained()
        for which in ("model", "projection"):
            path = self.target / self.task["analysis_handoff"][which]["path"]
            before = path.read_bytes()
            path.write_bytes(before + b"\n")
            with self.subTest(which=which):
                self.assertIn("ACTIVE_TASK_DIGEST", self.errors(self.check(selected=False)))
                with self.assertRaisesRegex(ValueError, "digest"):
                    restore(self.target, "fixture-task")
            path.write_bytes(before)
        self.model_path.write_bytes(b"{}")
        self.assertIn("ACTIVE_TASK_DIGEST", self.errors(self.check(selected=False)))
        with self.assertRaisesRegex(ValueError, "conflicting runtime"):
            restore(self.target, "fixture-task")

    def test_handoff_revision_requires_new_review_and_keeps_prior_bytes(self):
        first = self.retained()
        retained = {path: content for path, content in first.outputs.items() if "task-evidence" in path.parts}
        self.model["proof_obligations"][0].update(status="open", evidence_refs=[])
        self.write_draft()
        with self.assertRaisesRegex(ValueError, "retention-review"):
            self.plan()
        self.retained()
        self.assertTrue(all(path.read_bytes() == content for path, content in retained.items()))
        self.assertEqual(self.errors(self.check()), set())

    def test_registration_cannot_introduce_handoff_without_derived_retention(self):
        registration = self.target / ".ai/.runtime/drafts/registration.json"
        witness = {"model": dict(self.task["problem_model"], path=".ai/assistant/task-evidence/fixture-task/missing/model.json"),
                   "projection": {"path": ".ai/assistant/task-evidence/fixture-task/missing/projection.json", "sha256": "a" * 64},
                   "retention_review": "claimed-review"}
        registration.write_text(json.dumps(dict(self.task, analysis_handoff=witness)))
        with self.assertRaisesRegex(ValueError, "introduce or modify"):
            publish(self.target, "fixture-task", self.draft.relative_to(self.target).as_posix(), registration.relative_to(self.target).as_posix())

    def test_readiness_requires_every_declared_handoff_and_selected_projection(self):
        self.retained()
        for path in (self.target / self.task["analysis_handoff"]["model"]["path"],
                     self.target / self.task["analysis_handoff"]["projection"]["path"],
                     self.target / self.model["active_projection"]["path"]):
            raw = path.read_bytes()
            path.unlink()
            with self.subTest(path=path):
                self.assertEqual(readiness(self.target, ROOT, "fixture-task")["state"], "blocked")
            path.write_bytes(raw)

    def test_readiness_does_not_offer_restore_over_conflicts_or_unavailable_witness(self):
        self.retained()
        self.model_path.write_text("conflicting evidence")
        checked = readiness(self.target, ROOT, "fixture-task")
        action = next(item["next_action"] for item in checked["issues"] if item["code"] == "WORKTREE_TASK_EVIDENCE")
        self.assertIn("reconcile", action)
        self.assertNotIn("restore-task", action)
        self.model_path.unlink()
        (self.target / self.task["analysis_handoff"]["model"]["path"]).unlink()
        checked = readiness(self.target, ROOT, "fixture-task")
        self.assertFalse(any("restore-task" in item["next_action"] for item in checked["issues"]))

    def test_restore_preserves_conflicting_postimage_and_rejects_changed_index(self):
        self.retained()
        self.model_path.unlink()
        plan = restore(self.target, "fixture-task")
        self.model_path.write_bytes(b"peer evidence")
        with self.assertRaisesRegex(ValueError, "changed while planning"):
            SupportTransaction(self.target).apply(plan.outputs, expected_inputs=plan.inputs)
        self.assertEqual(self.model_path.read_bytes(), b"peer evidence")
        self.model_path.unlink()
        plan = restore(self.target, "fixture-task")
        (self.target / INDEX).write_bytes((self.target / INDEX).read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "changed while planning"):
            SupportTransaction(self.target).apply(plan.outputs, expected_inputs=plan.inputs)
        self.assertFalse(self.model_path.exists())

    def test_actual_linked_worktree_can_recover_only_committed_exact_handoff(self):
        from check_change_packages import git
        self.retained()
        git(self.target, "add", ".")
        git(self.target, "commit", "-qm", "retain reviewed handoff")
        peer = self.target.parent / (self.target.name + "-linked")
        self.addCleanup(shutil.rmtree, peer)
        git(self.target, "worktree", "add", "-qb", "peer", str(peer))
        path = peer / self.model_path.relative_to(self.target)
        self.assertFalse(path.exists())
        plan = restore(peer, "fixture-task")
        SupportTransaction(peer).apply(plan.outputs, expected_inputs=plan.inputs)
        self.assertEqual(path.read_bytes(), self.model_path.read_bytes())
        (peer / ".ai/local").mkdir(parents=True)
        common = self.target / ".git/alatyr/framework-source"
        common.parent.mkdir()
        common.write_text(str(ROOT))
        with patch.dict(os.environ, {"ALATYR_CORE": ""}):
            self.assertEqual(delegate.resolve_source(peer, None), ROOT)
        command = [sys.executable, str(ROOT / "tools/alatyr.py"), "worktree-preflight", "--target", str(peer), "--framework-source", str(ROOT), "--require-ready"]
        checked = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(json.loads(checked.stdout)["state"], "ready-for-context-review")
        self.assertNotIn("Traceback", checked.stderr)

    def test_readiness_rejects_unknown_baseline_or_missing_runtime_and_accepts_resolved_bindings(self):
        self.retained()
        versions = {name: (ROOT / name).read_text().strip() for name in ("VERSION", "ADAPTER_SCHEMA_VERSION", "TEMPLATE_VERSION")}
        manifest = self.target / ".ai/alatyr.yaml"
        manifest.write_text(f"schema_version: {versions['ADAPTER_SCHEMA_VERSION']}\nframework:\n  version: {versions['VERSION']}\n  template_version: {versions['TEMPLATE_VERSION']}\ninstallation:\n  state: accepted\n  state_record: .ai/assistant/installation-state.json\n")
        state = self.target / ".ai/assistant/installation-state.json"
        state.write_text(json.dumps({"current_state": "accepted"}))
        self.assertEqual(readiness(self.target, ROOT)["state"], "ready-for-context-review")
        self.model_path.unlink()
        self.assertEqual(readiness(self.target, ROOT)["task_bindings"][0]["state"], "retained-bound")
        checked = readiness(self.target, ROOT, "fixture-task")
        self.assertEqual(checked["state"], "blocked")
        self.assertTrue(any(row["code"] == "WORKTREE_TASK_EVIDENCE" for row in checked["issues"]))

    def test_no_handoff_never_reconstructs_or_accepts_alternate_model(self):
        with self.assertRaisesRegex(ValueError, "no reviewed"):
            restore(self.target, "fixture-task")
        self.retained()
        self.task["problem_model"]["sha256"] = "f" * 64
        self.write_index()
        with self.assertRaisesRegex(ValueError, "registered runtime digest"):
            restore(self.target, "fixture-task")

    def test_unknown_retention_review_cannot_authorize_restoration(self):
        self.retained()
        self.task["analysis_handoff"]["retention_review"] = "unknown"
        self.write_index()
        with self.assertRaisesRegex(ValueError, "retention-review"):
            restore(self.target, "fixture-task")

    def test_public_restore_preview_and_write_use_same_contract(self):
        self.retained()
        self.model_path.unlink()
        command = [sys.executable, str(ROOT / "tools/alatyr.py"), "restore-task", "--target", str(self.target), "--task-id", "fixture-task"]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.model_path.exists())
        result = subprocess.run([*command, "--write"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["acceptance_granted"])
        self.assertEqual(self.errors(self.check()), set())

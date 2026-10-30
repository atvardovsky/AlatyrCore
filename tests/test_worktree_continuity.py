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

    def doctor(self, *, selected=True, text=False):
        args = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "doctor",
                "--target", str(self.target), "--framework-source", str(ROOT)]
        if selected:
            args += ["--current-task", "fixture-task"]
        if not text:
            args += ["--json"]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertNotIn("Traceback", result.stderr)
        return result, result.stdout if text else json.loads(result.stdout)

    def test_public_doctor_selected_runtime_matrix_preserves_foreign_handoffs(self):
        self.retained()
        paths = [self.model_path, self.target / self.model["active_projection"]["path"]]
        originals = {path: path.read_bytes() for path in paths}
        for absent in ((0,), (1,), (0, 1)):
            with self.subTest(absent=absent):
                for path, content in originals.items():
                    path.write_bytes(content)
                for index in absent:
                    paths[index].unlink()
                before = {path.relative_to(self.target).as_posix(): path.read_bytes()
                          for path in self.target.rglob("*") if path.is_file() and ".git" not in path.parts}
                _, foreign = self.doctor(selected=False)
                self.assertNotIn("ACTIVE_TASK_REHYDRATION_REQUIRED", {row["code"] for row in foreign["findings"]})
                result, selected = self.doctor()
                self.assertNotEqual(result.returncode, 0)
                current = selected["current_task"]
                self.assertIn("ACTIVE_TASK_REHYDRATION_REQUIRED", {row["code"] for row in selected["findings"]})
                self.assertEqual(current["state"], "bound-recorded-disposition")
                self.assertFalse(current["acceptance_granted"])
                runtime = current["runtime_readiness"]
                self.assertEqual(runtime["state"], "rehydration-required")
                self.assertEqual({row["path"] for row in runtime["prerequisites"]},
                                 {paths[index].relative_to(self.target).as_posix() for index in absent})
                self.assertTrue(current["diagnostics"])
                self.assertEqual(current["execution_focus"]["state"], "blocked-by-runtime-evidence")
                self.assertIsNone(current["execution_focus"]["next_action"])
                codes = {row["code"] for row in selected["findings"]}
                self.assertIn("ACTIVE_TASK_REHYDRATION_REQUIRED", codes)
                self.assertNotIn("ACTIVE_TASK_NOT_CLOSED", codes)
                self.assertNotIn("TASK_ACCEPTANCE_CLOSURE", codes)
                prerequisites = [row for row in selected["repair_plan"]["steps"] if row["kind"] == "prerequisite"]
                self.assertEqual({row["path"] for row in prerequisites}, {row["path"] for row in runtime["prerequisites"]})
                self.assertTrue(all(row["action"] == "inspect-reviewed-handoff-for-restore" for row in prerequisites))
                after = {path.relative_to(self.target).as_posix(): path.read_bytes()
                         for path in self.target.rglob("*") if path.is_file() and ".git" not in path.parts}
                self.assertEqual(after, before)
                plan = restore(self.target, "fixture-task")
                SupportTransaction(self.target).apply(plan.outputs, expected_inputs=plan.inputs)
                self.assertEqual({path: path.read_bytes() for path in paths}, originals)
        _, restored = self.doctor()
        self.assertEqual(restored["current_task"]["runtime_readiness"]["state"], "bound-not-execution-proof")
        self.assertFalse(restored["current_task"]["runtime_readiness"]["prerequisites"])
        self.assertNotIn("ACTIVE_TASK_REHYDRATION_REQUIRED", {row["code"] for row in restored["findings"]})

    def test_public_doctor_conflicts_never_become_restore_permission(self):
        self.retained()
        for path in (self.model_path, self.target / self.model["active_projection"]["path"]):
            original = path.read_bytes()
            with self.subTest(path=path.name):
                path.write_bytes(b"conflicting runtime bytes")
                result, payload = self.doctor()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ACTIVE_TASK_DIGEST", {row["code"] for row in payload["findings"]})
                current = payload["current_task"]
                self.assertEqual(current["state"], "bound-recorded-disposition")
                self.assertEqual(current["runtime_readiness"]["state"], "blocked")
                prerequisites = [row for row in payload["repair_plan"]["steps"] if row["kind"] == "prerequisite"]
                self.assertEqual(len(prerequisites), 1)
                self.assertEqual(prerequisites[0]["path"], path.relative_to(self.target).as_posix())
                self.assertEqual(prerequisites[0]["action"], "reconcile-conflicting-evidence")
                self.assertFalse(current["runtime_readiness"]["authorization_granted"])
                self.assertFalse(payload["repair_plan"]["acceptance_granted"])
                with self.assertRaisesRegex(ValueError, "conflicting runtime"):
                    restore(self.target, "fixture-task")
                self.assertEqual(path.read_bytes(), b"conflicting runtime bytes")
                path.write_bytes(original)

    def test_public_doctor_missing_or_corrupt_retained_evidence_is_not_ready(self):
        self.retained()
        for name in ("model", "projection"):
            path = self.target / self.task["analysis_handoff"][name]["path"]
            original = path.read_bytes()
            for missing in (False, True):
                with self.subTest(artifact=name, missing=missing):
                    if missing:
                        path.unlink()
                    else:
                        path.write_bytes(b"corrupt retained bytes")
                    result, payload = self.doctor()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(payload["current_task"]["state"], "unknown")
                    self.assertEqual(payload["current_task"]["runtime_readiness"]["state"], "blocked")
                    self.assertTrue(payload["current_task"]["diagnostics"])
                    self.assertFalse(payload["current_task"]["acceptance_granted"])
                    prerequisites = [row for row in payload["repair_plan"]["steps"] if row["kind"] == "prerequisite"]
                    self.assertEqual(len(prerequisites), 1)
                    self.assertEqual(prerequisites[0]["path"], path.relative_to(self.target).as_posix())
                    self.assertEqual(prerequisites[0]["action"], "recover-exact-evidence")
                    with self.assertRaises(ValueError):
                        restore(self.target, "fixture-task")
                    self.assertEqual(path.exists(), not missing)
                    path.write_bytes(original)

    def test_public_doctor_text_names_projection_only_recovery(self):
        self.retained()
        projection = self.target / self.model["active_projection"]["path"]
        projection.unlink()
        result, text = self.doctor(text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Selected runtime: rehydration-required", text)
        self.assertIn("inspect-reviewed-handoff-for-restore: task fixture-task [" + projection.relative_to(self.target).as_posix(), text)
        self.assertIn("not execution permission", text)
        self.assertFalse(projection.exists())

    def test_runtime_diagnostic_selection_matches_canonical_evidence_resolver(self):
        from check_change_packages import changed_index_validator
        from target_adapter_validation.active_tasks import _task_model_evidence
        self.retained()
        paths = [self.model_path, self.target / self.model["active_projection"]["path"]]
        for absent in ((), (0,), (1,), (0, 1)):
            contents = {path: path.read_bytes() for path in paths}
            for index in absent:
                paths[index].unlink()
            selected = changed_index_validator(self.target)
            selected.current_task_id = "fixture-task"
            diagnostic = changed_index_validator(self.target)
            _task_model_evidence(selected, self.task)
            _task_model_evidence(diagnostic, self.task, require_runtime=True)
            self.assertEqual([row.to_json() for row in selected.findings],
                             [row.to_json() for row in diagnostic.findings])
            for path, content in contents.items():
                path.write_bytes(content)

    def test_unavailable_runtime_is_not_misreported_as_missing(self):
        from check_change_packages import changed_index_validator
        from current_task_view import current_task_view
        self.retained()
        projection = self.target / self.model["active_projection"]["path"]
        original = projection.read_bytes()
        projection.unlink()
        projection.mkdir()
        checked = changed_index_validator(self.target)
        current = current_task_view(checked, "fixture-task")
        self.assertEqual(current["runtime_readiness"]["state"], "blocked")
        self.assertEqual(current["runtime_readiness"]["prerequisites"][0]["action"], "reconcile-conflicting-evidence")
        self.assertNotIn("ACTIVE_TASK_REHYDRATION_REQUIRED", self.errors(checked))
        self.assertTrue(projection.is_dir())
        projection.rmdir()
        projection.write_bytes(original)

    def test_runtime_and_diagnostic_binding_reads_keep_the_canonical_size_limit(self):
        from check_change_packages import changed_index_validator
        from target_adapter_validation.active_tasks import _bound_object, MAX_ARTIFACT_BYTES
        for size in (MAX_ARTIFACT_BYTES - 1, MAX_ARTIFACT_BYTES, MAX_ARTIFACT_BYTES + 1):
            with self.subTest(size=size):
                self.model_path.write_bytes(b"{}" + b" " * (size - 2))
                binding = self.bind(self.model_path)
                checked = changed_index_validator(self.target)
                value = _bound_object(checked, binding, "selected runtime model",
                    details={"task_id": "fixture-task", "runtime_binding": binding, "action": "reconcile-conflicting-evidence"})
                if size <= MAX_ARTIFACT_BYTES:
                    self.assertEqual(value, {})
                    self.assertFalse(self.errors(checked))
                else:
                    self.assertIsNone(value)
                    self.assertIn("ACTIVE_TASK_DIGEST", self.errors(checked))

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

"""Reviewed evidence loss is neither completion nor a runnable task."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import patch

from tests.active_task_fixture import ActiveTaskFixture
from check_change_packages import git
from current_task_view import current_task_view
from target_adapter_validation.active_tasks import INDEX_PATH


class HistoricalTaskLossTests(ActiveTaskFixture):
    def save(self, path, value):
        file = self.target / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        return self.bind(file)

    def setUp(self):
        super().setUp()
        git(self.target, "add", INDEX_PATH)
        git(self.target, "commit", "-qm", "register original task")
        self.original = copy.deepcopy(self.task)
        self.registration = {
            "commit": git(self.target, "rev-parse", "HEAD"),
            "index_sha256": hashlib.sha256((self.target / INDEX_PATH).read_bytes()).hexdigest(),
        }
        self.model_bytes = self.model_path.read_bytes()
        self.model_path.unlink()
        prefix = ".ai/assistant/task-evidence/fixture-task"
        self.approval_path = prefix + "/owner-review.json"
        self.approval = {
            "schema_version": 1, "record_kind": "alatyr-evidence-loss-approval",
            "decision": "approved", "scope": "historical-classification-only",
            "granted_by": "fixture-owner", "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "tasks": [{"task_id": self.task["task_id"], "operation_id": self.task["operation_id"],
                       "problem_model": self.task["problem_model"], "registration": self.registration}],
            "original_outcomes_accepted": False, "execution_authorized": False,
        }
        self.search_path = prefix + "/search.json"
        self.search = {
            "record_kind": "alatyr-evidence-search", "task_id": self.task["task_id"],
            "expected_model": self.task["problem_model"], "outcome": "not-recovered",
            "inspected_artifacts": 1, "locations": ["fixture runtime and retained evidence"],
            "limitations": "Bounded fixture search, not universal absence proof.",
        }
        self.review_path = prefix + "/dependencies.json"
        self.review = {
            "record_kind": "alatyr-evidence-loss-dependency-review", "task_id": self.task["task_id"],
            "registration": self.registration, "active_dependents": [],
            "reviewed_packages": [], "limitation": "Headers cannot recover missing proof obligations.",
        }
        self.loss_path = prefix + "/evidence-loss.json"
        self.loss = {
            "schema_version": 1, "record_kind": "alatyr-task-evidence-loss",
            "task_id": self.task["task_id"], "operation_id": self.task["operation_id"],
            "registration": self.registration, "missing_model": self.task["problem_model"],
            "owner_approval": self.save(self.approval_path, self.approval),
            "search_evidence": self.save(self.search_path, self.search),
            "dependency_review": self.save(self.review_path, self.review),
            "unresolved_outcomes": [{"fact_id": "change-1", "state": "unverified",
                "owner_ref": "design.md", "statement": "Original outcome remains unverified.",
                "next_safe_action": "Recover exact evidence or request a new independently reviewed task."}],
            "authority": "none", "acceptance_granted": False, "resumable": False,
            "missing_obligations": "unknown-not-discharged",
        }
        self.task["state"] = "historical-evidence-missing"
        self.rewrite()

    def rewrite(self, tasks=None):
        self.task["evidence_loss_disposition"] = self.save(self.loss_path, self.loss)
        self.save(INDEX_PATH, {"schema_version": 2, "index_kind": "target-active-task-index",
                               "tasks": [self.task] if tasks is None else tasks})

    def test_reviewed_missing_history_is_a_warning_not_completion(self):
        checked = self.check(selected=False)
        self.assertEqual(self.errors(checked), set(), [(f.code, f.message) for f in checked.findings])
        self.assertIn("TASK_EVIDENCE_LOST", {f.code for f in checked.findings if f.level == "warning"})
        self.assertIsNone(self.task["completion_evidence"])

    def test_schema_one_active_tasks_remain_compatible(self):
        self.task = copy.deepcopy(self.original)
        self.model_path.write_bytes(self.model_bytes)
        self.write_index()
        self.assertEqual(self.errors(self.check()), set())

    def test_loss_state_requires_schema_two(self):
        self.save(INDEX_PATH, {"schema_version": 1, "index_kind": "target-active-task-index", "tasks": [self.task]})
        self.assertIn("ACTIVE_TASK_SCHEMA", self.errors(self.check(selected=False)))

    def test_loss_cannot_be_accepted_as_selected_current_task(self):
        self.assertIn("TASK_EVIDENCE_LOSS_SELECTED", self.errors(self.check()))

    def test_selected_view_retains_unresolved_duties_and_has_no_action(self):
        checked = self.check(selected=False)
        view = current_task_view(checked, "fixture-task")
        self.assertEqual(view["state"], "historical-evidence-missing", view)
        self.assertFalse(view["acceptance_granted"])
        self.assertFalse(view["resumable"])
        self.assertEqual(view["unresolved_outcomes"], self.loss["unresolved_outcomes"])
        self.assertEqual(view["runtime_readiness"]["state"], "not-resumable")
        self.assertNotIn("execution_focus", view)
        self.assertNotIn("next_action_advice", view)

    def test_tampered_disposition_hash_is_rejected(self):
        (self.target / self.loss_path).write_bytes(b"{}")
        self.assertIn("TASK_EVIDENCE_LOSS", self.errors(self.check(selected=False)))

    def test_changed_inputs_invalidate_historical_view(self):
        checked = self.check(selected=False)
        with patch.object(checked.context, "finalize", return_value=["changed input"]):
            view = current_task_view(checked, "fixture-task")
        self.assertEqual(view["state"], "unknown")
        self.assertFalse(view["acceptance_granted"])
        self.assertNotIn("runtime_readiness", view)

    def test_actual_model_recovery_during_view_invalidates_disposition(self):
        from historical_task_evidence import validate_loss_disposition
        checked = self.check(selected=False)
        def recover(*args):
            value = validate_loss_disposition(*args)
            self.model_path.write_bytes(self.model_bytes)
            return value
        with patch("historical_task_evidence.validate_loss_disposition", side_effect=recover):
            view = current_task_view(checked, "fixture-task")
        self.assertEqual(view["state"], "unknown")
        self.assertFalse(view["acceptance_granted"])

    def test_missing_approval_search_or_dependency_evidence_is_rejected(self):
        for field in ("owner_approval", "search_evidence", "dependency_review"):
            with self.subTest(field=field):
                original = self.loss[field]
                self.loss[field] = {"path": "missing.json", "sha256": "0" * 64}
                self.rewrite()
                self.assertIn("TASK_EVIDENCE_LOSS", self.errors(self.check(selected=False)))
                self.loss[field] = original

    def test_original_registration_cannot_be_rewritten(self):
        for field, value in (("changed_fact_ids", []), ("canonical_owners", []),
                             ("operation_id", "other-operation"), ("repair_review_required", True)):
            with self.subTest(field=field):
                original = self.task[field]
                self.task[field] = value
                self.rewrite()
                self.assertIn("TASK_EVIDENCE_LOSS", self.errors(self.check(selected=False)))
                self.task[field] = original

    def test_wrong_commit_or_index_digest_is_rejected(self):
        for field, value in (("commit", "0" * 40), ("index_sha256", "0" * 64)):
            with self.subTest(field=field):
                original = self.loss["registration"][field]
                self.loss["registration"][field] = value
                self.rewrite()
                self.assertIn("TASK_EVIDENCE_LOSS", self.errors(self.check(selected=False)))
                self.loss["registration"][field] = original

    def test_recovered_or_conflicting_model_requires_explicit_review(self):
        for content in (self.model_bytes, b"conflicting evidence\n"):
            with self.subTest(content=len(content)):
                self.model_path.write_bytes(content)
                self.assertIn("TASK_EVIDENCE_LOSS", self.errors(self.check(selected=False)))
                self.model_path.unlink()

    def test_unsafe_model_path_is_not_reported_missing(self):
        self.model_path.symlink_to(self.target / "missing-outside")
        self.assertIn("TASK_EVIDENCE_LOSS", self.errors(self.check(selected=False)))

    def test_symlinked_retained_disposition_is_rejected(self):
        path = self.target / self.loss_path
        original = path.read_bytes()
        path.unlink()
        other = self.target / "other.json"
        other.write_bytes(original)
        path.symlink_to(other)
        self.assertIn("TASK_EVIDENCE_LOSS", self.errors(self.check(selected=False)))

    def test_duplicate_json_keys_are_rejected(self):
        path = self.target / self.loss_path
        path.write_bytes(path.read_bytes().replace(b'"authority": "none"', b'"authority": "none", "authority": "none"'))
        self.task["evidence_loss_disposition"] = self.bind(path)
        self.save(INDEX_PATH, {"schema_version": 2, "index_kind": "target-active-task-index", "tasks": [self.task]})
        self.assertIn("TASK_EVIDENCE_LOSS", self.errors(self.check(selected=False)))

    def test_outcomes_cannot_be_dropped_or_accepted(self):
        for outcomes in ([], [{**self.loss["unresolved_outcomes"][0], "state": "passed"}],
                          [{**self.loss["unresolved_outcomes"][0], "fact_id": "other"}]):
            with self.subTest(outcomes=outcomes):
                self.loss["unresolved_outcomes"] = outcomes
                self.rewrite()
                self.assertTrue(self.errors(self.check(selected=False)))

    def test_approval_cannot_cover_other_task_or_grant_execution(self):
        for key, value in (("decision", "pending"), ("execution_authorized", True),
                           ("original_outcomes_accepted", True), ("reviewed_at", "not-a-date"),
                           ("tasks", []), ("granted_by", "{OWNER}"), ("granted_by", "unknown"),
                           ("granted_by", " ")):
            with self.subTest(key=key):
                original = self.approval[key]
                self.approval[key] = value
                self.loss["owner_approval"] = self.save(self.approval_path, self.approval)
                self.rewrite()
                self.assertIn("TASK_EVIDENCE_LOSS", self.errors(self.check(selected=False)))
                self.approval[key] = original

    def test_active_successor_cannot_depend_on_missing_history(self):
        successor = copy.deepcopy(self.original)
        successor.update(task_id="successor", predecessor_task_ids=["fixture-task"], state="active")
        self.rewrite([self.task, successor])
        self.assertIn("ACTIVE_TASK_PREDECESSOR", self.errors(self.check(selected=False)))

    def test_loss_disposition_cannot_be_attached_to_active_task(self):
        self.task["state"] = "active"
        self.rewrite()
        self.assertIn("ACTIVE_TASK_SCHEMA", self.errors(self.check(selected=False)))

    def test_oversized_receipt_is_rejected(self):
        path = self.target / self.loss_path
        path.write_bytes(b" " * (512 * 1024 + 1))
        self.task["evidence_loss_disposition"] = self.bind(path)
        self.save(INDEX_PATH, {"schema_version": 2, "index_kind": "target-active-task-index", "tasks": [self.task]})
        self.assertIn("TASK_EVIDENCE_LOSS", self.errors(self.check(selected=False)))

    def test_declared_recovery_does_not_authorize_restore(self):
        from restore_active_task import prepare
        with self.assertRaises(ValueError):
            prepare(self.target, "fixture-task")

    def test_selected_worktree_readiness_cannot_resume_missing_history(self):
        from worktree_readiness import readiness
        report = readiness(self.target, task_id="fixture-task")
        self.assertIn("WORKTREE_TASK_EVIDENCE_LOST", {row["code"] for row in report["issues"]})
        self.assertFalse(report["acceptance_granted"])

    def package(self, *, status="blocked", selected=False):
        source = ".ai/assistant/change-packages/fixture.json"
        self.review["reviewed_packages"] = [{"path": source, "status": "blocked"}]
        self.loss["dependency_review"] = self.save(self.review_path, self.review)
        self.rewrite()
        checked = self.check(selected=False)
        if selected:
            checked.change_packages = [self.target / source]
        data = {"operation": {"id": self.task["operation_id"]}, "incident_continuity": {
            "mode": "none", "family_id": "none", "trigger": "none", "corrective_iteration": 0,
            "predecessors": [], "problem_model": self.task["problem_model"],
            "latest_failed_gate": {"state": "none", "id": "none", "evidence_refs": []},
            "lifecycle_model_required": False, "evidence_loss_disposition": self.task["evidence_loss_disposition"],
        }}
        return checked, data, source, status

    def test_matching_blocked_historical_package_retains_a_warning(self):
        checked, data, source, status = self.package()
        checked.validate_package_incident_continuity(data, source, status=status, indexed_entries=[])
        self.assertEqual(self.errors(checked), set(), [(f.code, f.message) for f in checked.findings])
        self.assertIn("PACKAGE_INCIDENT_EVIDENCE_LOST", {f.code for f in checked.findings})

    def test_selected_or_nonblocked_package_cannot_use_historical_loss(self):
        for status, selected in (("blocked", True), ("validated", False), ("complete", False), ("implementing", False)):
            with self.subTest(status=status, selected=selected):
                checked, data, source, _ = self.package(status=status, selected=selected)
                checked.validate_package_incident_continuity(data, source, status=status, indexed_entries=[])
                self.assertIn("PACKAGE_INCIDENT_EVIDENCE_LOSS", self.errors(checked))

    def test_package_cannot_borrow_another_operation_or_model_loss(self):
        for field in ("operation", "model", "family", "gate"):
            with self.subTest(field=field):
                checked, data, source, status = self.package()
                if field == "operation":
                    data["operation"]["id"] = "different"
                elif field == "model":
                    data["incident_continuity"]["problem_model"] = {"path": "other.json", "sha256": "0" * 64}
                elif field == "family":
                    data["incident_continuity"]["family_id"] = "different"
                else:
                    data["incident_continuity"]["latest_failed_gate"]["id"] = "different"
                checked.validate_package_incident_continuity(data, source, status=status, indexed_entries=[])
                self.assertIn("PACKAGE_INCIDENT_EVIDENCE_LOSS", self.errors(checked))

    def test_current_operation_or_model_alias_cannot_borrow_loss(self):
        for alias in ("operation", "model", "unknown"):
            with self.subTest(alias=alias):
                _, data, source, status = self.package()
                data["package_id"] = "historical-package"
                current = copy.deepcopy(self.original)
                current.update(task_id="current-task", operation_id="current-operation")
                current["problem_model"] = {"path": ".ai/.runtime/problem-models/current.json", "sha256": "f" * 64}
                if alias == "operation":
                    current["operation_id"] = self.task["operation_id"]
                elif alias == "model":
                    current["problem_model"]["sha256"] = self.task["problem_model"]["sha256"]
                self.rewrite([self.task, current])
                checked = self.check(selected=False)
                checked.current_task_id = "missing-task" if alias == "unknown" else "current-task"
                checked.validate_package_incident_continuity(data, source, status=status, indexed_entries=[])
                self.assertIn("PACKAGE_INCIDENT_EVIDENCE_LOSS", self.errors(checked))

    def test_explicitly_selected_runtime_model_cannot_borrow_loss(self):
        checked, data, source, status = self.package()
        checked.problem_models = [checked.target_path(self.task["problem_model"]["path"])]
        checked.validate_package_incident_continuity(data, source, status=status, indexed_entries=[])
        self.assertIn("PACKAGE_INCIDENT_EVIDENCE_LOSS", self.errors(checked))

    def test_distinct_current_task_does_not_block_unrelated_history(self):
        _, data, source, status = self.package()
        data["package_id"] = "historical-package"
        current = copy.deepcopy(self.original)
        current.update(task_id="different-task", operation_id="different-operation")
        current["problem_model"] = {"path": ".ai/.runtime/problem-models/different.json", "sha256": "f" * 64}
        self.rewrite([self.task, current])
        checked = self.check(selected=False)
        checked.current_task_id = "different-task"
        checked.validate_package_incident_continuity(data, source, status=status, indexed_entries=[])
        self.assertNotIn("PACKAGE_INCIDENT_EVIDENCE_LOSS", self.errors(checked))
        self.assertIn("PACKAGE_INCIDENT_EVIDENCE_LOST", {f.code for f in checked.findings})

    def test_invalid_package_loss_does_not_fall_through_as_success(self):
        checked, data, source, status = self.package()
        data["incident_continuity"]["evidence_loss_disposition"] = {"path": "missing.json", "sha256": "0" * 64}
        checked.validate_package_incident_continuity(data, source, status=status, indexed_entries=[])
        self.assertIn("PACKAGE_INCIDENT_EVIDENCE_LOSS", self.errors(checked))

    def test_normal_missing_package_model_still_errors(self):
        checked, data, source, status = self.package()
        del data["incident_continuity"]["evidence_loss_disposition"]
        checked.validate_package_incident_continuity(data, source, status=status, indexed_entries=[])
        self.assertIn("PACKAGE_INCIDENT_MODEL_MISSING", self.errors(checked))

    def test_retained_loss_cannot_be_removed_or_silently_reopened(self):
        git(self.target, "add", ".ai/assistant")
        git(self.target, "commit", "-qm", "retain reviewed historical loss")
        historical = copy.deepcopy(self.task)
        self.task = copy.deepcopy(self.original)
        self.model_path.write_bytes(self.model_bytes)
        self.write_index()
        self.assertIn("TASK_EVIDENCE_LOSS_REOPEN", self.errors(self.check(selected=False)))
        self.save(INDEX_PATH, {"schema_version": 2, "index_kind": "target-active-task-index", "tasks": []})
        self.assertIn("TASK_EVIDENCE_LOSS_REOPEN", self.errors(self.check(selected=False)))
        self.task = historical

    def test_transitive_active_dependency_is_not_hidden(self):
        middle = copy.deepcopy(self.original)
        middle.update(task_id="middle", predecessor_task_ids=["fixture-task"], state="closed",
                      completion_evidence={"path": "missing.json", "sha256": "0" * 64})
        successor = copy.deepcopy(self.original)
        successor.update(task_id="successor", predecessor_task_ids=["middle"], state="active")
        self.rewrite([self.task, middle, successor])
        self.assertIn("ACTIVE_TASK_PREDECESSOR", self.errors(self.check(selected=False)))

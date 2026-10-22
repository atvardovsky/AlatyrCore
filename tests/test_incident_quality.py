from __future__ import annotations

import copy
import hashlib
import json
import sys
import subprocess
import tempfile
import importlib.util
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from incident_planning import incident_frontier, reconcile_findings
from repair_review import BOUNDARIES, evidence_failures
from test_execution_contract import TestExecutionContract
from validate_target_adapter import Finding, findings_payload
from plan_target_upgrade import add_validation_impact
import tests.test_test_execution_contract as execution_fixtures
import tests.active_task_fixture as task_fixtures


def repair_policy():
    return {"schema_version": 1, "state": "enabled", "acceptance_command_ids": ["unit"], "records": [{"task_id": "fixture-task", "path": "repair.json"}]}


def review_record():
    value = {
        "schema_version": 1, "record_kind": "target-repair-review", "task_id": "fixture-task",
        "operation_id": "fixture-operation", "incident_family_id": "fixture-incident",
        "policy_sha256": "a" * 64, "original_case_ref": "issue:original", "claim": "incident-fixed",
        "diagnosis": {"hypothesis_id": "queue", "run_ref": "diagnostic.json"},
        "hypotheses": [{"id": name, "falsifier": "A measured result contradicts " + name} for name in ("queue", "fixture")],
        "fixture_boundaries": [{"id": key, "state": "verified", "reason": "Reviewed actual producer and resource boundary", "evidence_refs": ["current.json"]} for key in sorted(BOUNDARIES)],
        "attempts": [
            {"hypothesis_id": "queue", "run_ref": "diagnostic.json", "purpose": "diagnostic", "failure_class": "none", "expected_effect": "Isolate the proposed queue mechanism", "observed_effect": "Discriminating observation recorded", "reassessment_ref": None},
            {"hypothesis_id": "queue", "run_ref": "current.json", "purpose": "acceptance", "failure_class": "none", "expected_effect": "Original real flow completes", "observed_effect": "Original real flow completed", "reassessment_ref": None}],
    }
    for attempt in value["attempts"]:
        attempt.update(run_sha256="f" * 64, historical_policy=None, failure_ref=None)
    return value


class RepairReviewTests(unittest.TestCase):
    def setUp(self):
        self.contract = TestExecutionContract()
        self.schema = self.contract.repair_schema()
        self.policy = repair_policy()
        run = execution_fixtures.record()
        run["proof_boundary"] = "end-to-end"
        run["run_window"] = {"started_at": "2026-10-22T09:03:00Z", "finished_at": "2026-10-22T09:04:00Z"}
        diagnostic = copy.deepcopy(run); diagnostic["result_artifact"]["sha256"] = "d" * 64
        diagnostic.update(claim="focused", filter="queue-control", run_window={"started_at": "2026-10-22T09:01:00Z", "finished_at": "2026-10-22T09:02:00Z"})
        self.runs = {"current.json": run, "diagnostic.json": diagnostic}

    def failures(self, record, completion=True):
        return evidence_failures(record, self.policy, self.runs, self.schema, completion=completion)

    def test_valid_review_and_default_policy_compatibility(self):
        self.assertEqual(self.failures(review_record()), [])
        with patch.object(self.contract, "repair_schema", side_effect=AssertionError("legacy path loaded repair schema")):
            self.assertEqual(self.contract.policy_failures(execution_fixtures.policy()), [])

    def test_each_required_boundary_and_reason_is_enforced(self):
        for i in range(6):
            item = review_record(); item["fixture_boundaries"].pop(i)
            self.assertTrue(self.failures(item))
            item = review_record(); item["fixture_boundaries"][i]["state"] = "unknown"
            self.assertTrue(self.failures(item))
            item = review_record(); item["fixture_boundaries"][i].update(state="not-applicable", reason="unknown")
            self.assertTrue(self.failures(item))
            item["fixture_boundaries"][i].update(reason="Project has no persistence boundary", evidence_refs=[])
            self.assertTrue(self.failures(item))

    def test_component_and_failed_runs_cannot_establish_incident_acceptance(self):
        for field, value in (("proof_boundary", "unit"), ("claim", "focused"), ("state", "failed")):
            old = self.runs["current.json"][field]
            self.runs["current.json"][field] = value
            self.assertTrue(self.failures(review_record()))
            self.runs["current.json"][field] = old
        item = review_record(); item["claim"] = "component-only"
        self.assertTrue(self.failures(item))
        self.assertEqual(self.failures(item, completion=False), [])

    def test_repeated_failure_requires_later_diagnostic_reference(self):
        item = review_record()
        failed = copy.deepcopy(self.runs["current.json"]); failed["state"] = "failed"; failed["claim"] = "none"
        failed["run_window"] = {"started_at": "2026-10-22T09:00:00Z", "finished_at": "2026-10-22T09:00:30Z"}
        self.runs["failed.json"] = failed
        first = copy.deepcopy(item["attempts"][-1]); first.update(run_ref="failed.json", failure_class="production")
        item["attempts"] = [item["attempts"][-1]]
        item["attempts"].insert(0, first)
        self.assertTrue(self.failures(item))
        item["attempts"][-1]["reassessment_ref"] = "failed.json"
        self.assertTrue(self.failures(item))
        diagnostic = copy.deepcopy(self.runs["diagnostic.json"])
        diagnostic["result_artifact"]["sha256"] = "d" * 64
        self.runs["diagnostic.json"] = diagnostic
        middle = copy.deepcopy(first); middle.update(run_ref="diagnostic.json", purpose="diagnostic", failure_class="none", failure_ref="failed.json")
        item["attempts"].insert(1, middle)
        item["attempts"][-1]["reassessment_ref"] = "diagnostic.json"
        self.assertEqual(self.failures(item), [])
        diagnostic["result_artifact"]["sha256"] = failed["result_artifact"]["sha256"]
        self.assertTrue(self.failures(item))

    def test_malformed_nested_json_never_crashes(self):
        baseline = review_record()
        for path in execution_fixtures.nested_paths(baseline):
            for bad in (None, True, 3, "", [], {}, ["invalid"], {"wrong": []}):
                item = copy.deepcopy(baseline)
                execution_fixtures.set_path(item, path, bad)
                with self.subTest(path=path, bad=bad):
                    self.assertIsInstance(self.failures(item), list)

    def test_failed_run_without_output_cannot_crash_retry_review(self):
        item = review_record()
        failed = copy.deepcopy(self.runs["current.json"])
        failed.update(state="failed", claim="none", result_artifact=None,
                      run_window={"started_at": "2026-10-22T09:00:00Z", "finished_at": "2026-10-22T09:00:30Z"})
        self.runs["failed.json"] = failed
        first = copy.deepcopy(item["attempts"][-1])
        first.update(run_ref="failed.json", failure_class="production")
        item["attempts"].insert(0, first)
        item["attempts"][1]["failure_ref"] = "failed.json"
        item["attempts"][-1]["reassessment_ref"] = "diagnostic.json"
        self.assertTrue(any("reassessment requires" in failure for failure in self.failures(item)))

    def test_all_required_fields_and_diagnosis_are_required_for_completion(self):
        for key in review_record():
            item = review_record(); del item[key]
            with self.subTest(key=key): self.assertTrue(self.failures(item))
        item = review_record(); item["diagnosis"] = None
        self.assertTrue(self.failures(item))
        for key, value in (("state", "skipped"), ("proof_boundary", "static-metadata"), ("result_artifact", None)):
            previous = self.runs["diagnostic.json"][key]
            self.runs["diagnostic.json"][key] = value
            self.assertTrue(self.failures(review_record()))
            self.runs["diagnostic.json"][key] = previous
        self.runs["diagnostic.json"]["counts"]["executed"] = 0
        self.assertTrue(self.failures(review_record()))

    def test_below_at_and_above_attempt_limit(self):
        item = review_record()
        diagnostic = item["attempts"][0]
        acceptance = item["attempts"][-1]
        template_run = self.runs["current.json"]
        for count in (31, 32, 33):
            item["attempts"] = [diagnostic, acceptance]
            for i in range(count - 2):
                attempt = copy.deepcopy(acceptance); attempt["run_ref"] = f"run-{i}.json"
                run = copy.deepcopy(template_run)
                run["run_window"] = {"started_at": f"2026-10-22T10:{i:02}:00Z", "finished_at": f"2026-10-22T10:{i:02}:01Z"}
                self.runs[attempt["run_ref"]] = run
                item["attempts"].append(attempt)
            with self.subTest(count=count): self.assertEqual(bool(self.failures(item)), count > 32)

    def test_later_failure_cannot_be_omitted_reordered_or_reclassified(self):
        item = review_record()
        failed = copy.deepcopy(self.runs["current.json"])
        failed.update(state="failed", claim="none", run_window={"started_at": "2026-10-22T09:05:00Z", "finished_at": "2026-10-22T09:06:00Z"})
        self.runs["late.json"] = failed
        self.assertTrue(any("omit" in error for error in self.failures(item)))
        attempt = copy.deepcopy(item["attempts"][-1]); attempt.update(run_ref="late.json", failure_class="production")
        item["attempts"].append(attempt)
        self.assertTrue(any("failed acceptance" in error for error in self.failures(item)))
        item["attempts"][-2:] = reversed(item["attempts"][-2:])
        self.assertTrue(any("chronology" in error for error in self.failures(item)))
        attempt["purpose"] = "diagnostic"
        self.assertTrue(any("omit" in error for error in self.failures(item)))

    def test_archiving_a_whole_flow_failure_does_not_erase_retry_obligations(self):
        item = review_record()
        failed = copy.deepcopy(self.runs["current.json"])
        failed.update(state="failed", claim="none", run_window={"started_at": "2026-10-22T09:00:00Z", "finished_at": "2026-10-22T09:00:30Z"})
        self.runs["archived.json"] = failed
        item["attempts"][0].update(run_ref="archived.json", failure_class="production")
        item["diagnosis"]["run_ref"] = "archived.json"
        failures = evidence_failures(item, self.policy, self.runs, self.schema, completion=True, current_refs={"current.json"})
        self.assertTrue(any("acceptance significance" in error for error in failures))
        self.assertTrue(any("discriminating diagnostic" in error for error in failures))

    def test_run_windows_reject_missing_unbounded_or_malformed_time(self):
        for value in (None, {}, [], True, {"started_at": None, "finished_at": []}, {"started_at": "2026-10-22", "finished_at": "2026-10-23"}, {"started_at": "2026-10-22T10:00:00Z", "finished_at": "2026-10-22T09:00:00Z"}):
            self.runs["current.json"]["run_window"] = value
            self.assertTrue(self.failures(review_record()))

    def test_every_configured_acceptance_command_remains_required(self):
        self.policy["acceptance_command_ids"].append("other-flow")
        self.assertTrue(self.failures(review_record()))

    def test_policy_rejects_every_invalid_or_ambiguous_selection(self):
        policy = execution_fixtures.policy()
        policy["commands"][0]["execution"]["proof_boundary"] = "end-to-end"
        policy["repair_review"] = repair_policy()
        self.assertEqual(self.contract.policy_failures(policy), [])
        for path in execution_fixtures.nested_paths(policy["repair_review"]):
            for bad in (None, True, 7, {}, []):
                item = copy.deepcopy(policy)
                execution_fixtures.set_path(item["repair_review"], path, bad)
                self.assertIsInstance(self.contract.policy_failures(item), list)
        for key in ("task_id", "path"):
            item = copy.deepcopy(policy)
            duplicate = copy.deepcopy(item["repair_review"]["records"][0])
            duplicate["path" if key == "task_id" else "task_id"] += "-other"
            item["repair_review"]["records"].append(duplicate)
            self.assertTrue(self.contract.policy_failures(item))


class RegisteredRepairReviewTests(task_fixtures.ActiveTaskFixture):
    def configure(self):
        helper = execution_fixtures.RegisteredTestingExecutionTests()
        helper.write(self.target, ".ai/assistant/templates/repair-review.json", (ROOT/"templates/target/.ai/assistant/templates/repair-review.json").read_text())
        self.policy, self.run = helper.fixture(self.target)
        self.helper = helper
        self.policy["commands"][0]["execution"]["proof_boundary"] = "end-to-end"
        self.policy["repair_review"] = repair_policy()
        self.policy["execution_contract"]["evidence_records"].append("diagnostic.json")
        self.model["incident"].update(mode="new", family_id="fixture-incident", trigger="reported-defect")
        self.model["original_case"] = {"source_ref": "issue:original", "actor": "fixture caller", "input": "original reported input", "expected_outcome": "original flow completes", "status": "verified-fixed", "evidence_refs": ["current.json"], "supersession": None}
        self.model["hypotheses"] = [{"id": name, "statement": "Investigate " + name, "status": "supported" if name == "queue" else "rejected", "evidence_refs": ["diagnostic.json"]} for name in ("queue", "fixture")]
        marker = copy.deepcopy(self.model["proof_obligations"][0]); marker["id"] = "repair-evidence-review"
        self.model["proof_obligations"].append(marker)
        self.task["incident_family_id"] = "fixture-incident"
        self.write_model(); self.write_index()
        self.review = review_record()
        self.save()

    def save(self):
        self.helper.write(self.target, ".ai/project/testing/test-first-policy.json", self.policy)
        self.review["policy_sha256"] = hashlib.sha256((self.target/".ai/project/testing/test-first-policy.json").read_bytes()).hexdigest()
        self.run.update(policy_sha256=self.review["policy_sha256"], proof_boundary="end-to-end", run_window={"started_at": "2026-10-22T09:03:00Z", "finished_at": "2026-10-22T09:04:00Z"})
        for path in (".ai/assistant/active-tasks.json",):
            self.run["input_sha256"][path] = hashlib.sha256((self.target/path).read_bytes()).hexdigest()
        self.helper.write(self.target, "current.json", self.run)
        diagnostic = copy.deepcopy(self.run)
        diagnostic.update(claim="focused", filter="queue-control", run_window={"started_at": "2026-10-22T09:01:00Z", "finished_at": "2026-10-22T09:02:00Z"})
        self.helper.write(self.target, "diagnostic.json", diagnostic)
        for attempt in self.review["attempts"]:
            path = self.target/attempt["run_ref"]
            if path.is_file():
                attempt["run_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.helper.write(self.target, "repair.json", self.review)

    def test_public_active_task_phase_accepts_valid_review_and_rejects_false_proof(self):
        self.configure()
        checked = self.check()
        self.assertEqual(self.errors(checked), set(), [item.message for item in checked.findings if item.level == "error"])
        for field, value in (("operation_id", "different"), ("claim", "component-only")):
            self.review[field] = value; self.save()
            if field == "claim":
                self.review["fixture_boundaries"][0]["state"] = "unknown"; self.review["claim"] = "incident-fixed"; self.save()
            self.assertIn("TDD_EXECUTION_EVIDENCE", self.errors(self.check()))
            self.review = review_record(); self.save()
        self.run["input_sha256"]["test.cfg"] = "0" * 64
        self.helper.write(self.target, "current.json", self.run)
        self.assertIn("TDD_EXECUTION_EVIDENCE_STALE", self.errors(self.check()))

    def test_requirement_cannot_be_removed_or_downgraded(self):
        self.configure()
        self.policy.pop("repair_review"); self.save()
        self.assertIn("TDD_EXECUTION_CONTRACT", self.errors(self.check()))

    def test_active_only_baseline_header_catches_manual_review_downgrade(self):
        self.configure()
        task_fixtures.git(self.target, "add", ".")
        task_fixtures.git(self.target, "commit", "-qm", "capture active incident review requirement")
        self.model["proof_obligations"] = [item for item in self.model["proof_obligations"] if item["id"] != "repair-evidence-review"]
        self.model["primary_strategy_id"] = "invariant-first"
        self.write_model(); self.write_index()
        self.assertIn("TDD_EXECUTION_CONTRACT", self.errors(self.check()))

    def test_missing_comparison_cannot_accept_removed_review_metadata(self):
        self.configure()
        self.model["proof_obligations"] = [item for item in self.model["proof_obligations"] if item["id"] != "repair-evidence-review"]
        self.model["primary_strategy_id"] = "invariant-first"
        self.write_model(); self.write_index(); self.close()
        self.assertIn("TDD_REPAIR_HISTORY", self.errors(self.check(comparison=False)))

    def test_present_malformed_historical_index_is_not_absent_history(self):
        self.configure()
        path = self.target / ".ai/assistant/active-tasks.json"
        for bad in ({}, {"schema_version": 1, "index_kind": "target-active-task-index"}, {"tasks": {}}, {"tasks": "invalid"}):
            path.write_text(json.dumps(bad))
            task_fixtures.git(self.target, "add", ".")
            task_fixtures.git(self.target, "commit", "-qm", "capture malformed historical index")
            self.write_index()
            self.assertIn("TDD_REPAIR_HISTORY", self.errors(self.check()))

    def test_registered_retry_review_reports_missing_failed_output_without_crashing(self):
        self.configure()
        self.policy["execution_contract"]["evidence_records"].append("failed.json")
        first = copy.deepcopy(self.review["attempts"][-1])
        first.update(run_ref="failed.json", failure_class="production")
        self.review["attempts"].insert(0, first)
        self.review["attempts"][1]["failure_ref"] = "failed.json"
        self.review["attempts"][-1]["reassessment_ref"] = "diagnostic.json"
        self.save()
        failed = copy.deepcopy(self.run)
        failed.update(state="failed", claim="none", result_artifact=None,
                      run_window={"started_at": "2026-10-22T09:00:00Z", "finished_at": "2026-10-22T09:00:30Z"},
                      counts={"discovered": 1, "executed": 1, "passed": 0, "failed": 1, "skipped": 0})
        self.helper.write(self.target, "failed.json", failed)
        first["run_sha256"] = hashlib.sha256((self.target/"failed.json").read_bytes()).hexdigest()
        self.helper.write(self.target, "repair.json", self.review)
        checked = self.check()
        self.assertIn("TDD_EXECUTION_EVIDENCE", self.errors(checked))
        self.assertTrue(any("reassessment requires" in item.message for item in checked.findings))

    def test_missing_repair_template_is_not_reported_as_a_complete_installation(self):
        self.configure()
        (self.target/".ai/assistant/templates/repair-review.json").unlink()
        self.assertIn("TDD_EXECUTION_TEMPLATE_MISSING", self.errors(self.check()))

    def test_default_nonincident_path_does_not_load_repair_policy(self):
        checked = self.check()
        self.assertNotIn("TDD_EXECUTION_CONTRACT", self.errors(checked))

    def test_missing_and_malformed_selected_records_fail_through_public_phase(self):
        self.configure()
        (self.target/"repair.json").unlink()
        self.assertIn("TDD_EXECUTION_EVIDENCE", self.errors(self.check()))
        for value in ({}, [], True, {"claim": {}}):
            self.helper.write(self.target, "repair.json", value)
            expected = "TDD_EXECUTION_EVIDENCE" if isinstance(value, dict) else "TDD_EXECUTION_EVIDENCE_INVALID_SHAPE"
            self.assertIn(expected, self.errors(self.check()))

    def test_historical_failure_survives_real_source_change_but_old_pass_cannot_qualify(self):
        self.configure()
        captured = copy.deepcopy(self.policy)
        self.helper.write(self.target, "captured-policy.json", captured)
        captured_sha = hashlib.sha256((self.target/"captured-policy.json").read_bytes()).hexdigest()
        failed = copy.deepcopy(self.run)
        failed.update(state="failed", claim="none", policy_sha256=captured_sha,
                      run_window={"started_at": "2026-10-22T09:00:00Z", "finished_at": "2026-10-22T09:00:30Z"},
                      counts={"discovered": 1, "executed": 1, "passed": 0, "failed": 1, "skipped": 0})
        failed["input_sha256"]["src/app.py"] = hashlib.sha256((self.target/"src/app.py").read_bytes()).hexdigest()
        self.helper.write(self.target, "failed-output.txt", "original failed observable")
        failed["result_artifact"] = {"path": "failed-output.txt", "sha256": hashlib.sha256((self.target/"failed-output.txt").read_bytes()).hexdigest()}
        self.helper.write(self.target, "historical-failed.json", failed)
        self.helper.write(self.target, "src/app.py", "repaired implementation")
        for path in ("captured-policy.json", "historical-failed.json", "failed-output.txt", "src/app.py"):
            self.run["input_sha256"][path] = hashlib.sha256((self.target/path).read_bytes()).hexdigest()
        first = copy.deepcopy(self.review["attempts"][-1])
        first.update(run_ref="historical-failed.json", failure_class="production", historical_policy={"path": "captured-policy.json", "sha256": captured_sha})
        self.review["attempts"].insert(0, first)
        self.review["attempts"][1]["failure_ref"] = "historical-failed.json"
        self.review["attempts"][-1]["reassessment_ref"] = "diagnostic.json"
        self.save()
        checked = self.check()
        self.assertEqual(self.errors(checked), set(), [item.message for item in checked.findings if item.level == "error"])
        failed.update(state="passed", claim="full", counts={"discovered": 1, "executed": 1, "passed": 1, "failed": 0, "skipped": 0})
        self.helper.write(self.target, "historical-failed.json", failed)
        self.run["input_sha256"]["historical-failed.json"] = hashlib.sha256((self.target/"historical-failed.json").read_bytes()).hexdigest()
        self.review["attempts"][0]["failure_class"] = "none"
        self.save()
        self.assertIn("TDD_EXECUTION_EVIDENCE", self.errors(self.check()))

    def test_completed_task_requires_its_selected_review_record(self):
        self.configure()
        self.close()
        self.policy["repair_review"]["records"] = []
        self.save()
        self.assertIn("TDD_EXECUTION_EVIDENCE", self.errors(self.check()))


class IncidentPlanningTests(unittest.TestCase):
    def test_installed_delegate_forwards_opt_in_frontier_without_changing_status(self):
        path = ROOT/"templates/target/.ai/assistant/tools/alatyr_delegate.py"
        spec = importlib.util.spec_from_file_location("incident_delegate_fixture", path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        parser = module.build_parser()
        args = parser.parse_args(["doctor", "--incident-frontier"])
        self.assertIn("--incident-frontier", module.canonical_arguments(args, ROOT, ROOT))
        args = parser.parse_args(["status"])
        self.assertNotIn("--incident-frontier", module.canonical_arguments(args, ROOT, ROOT))

    def headers(self):
        task = {"task_id": "first", "operation_id": "operation", "state": "active", "task_class": "small-task", "problem_model": None, "completion_evidence": None, "canonical_owners": [], "changed_fact_ids": [], "incident_family_id": "incident", "predecessor_task_ids": [], "latest_failed_gate_id": "original-failure"}
        following = copy.deepcopy(task); following.update(task_id="next", predecessor_task_ids=["first"])
        return {"schema_version": 1, "index_kind": "target-active-task-index", "tasks": [task, following]}

    def test_frontier_never_retires_ancestors_or_clears_failed_gates(self):
        index = self.headers(); before = copy.deepcopy(index)
        view = incident_frontier(index)
        self.assertEqual(view["frontier"], ["next"])
        self.assertEqual(view["retained_active"], ["first", "next"])
        self.assertEqual(view["declared_failed_gates"], ["original-failure"])
        self.assertEqual(index, before)
        for predecessor in ("next", "missing"):
            index["tasks"][0]["predecessor_task_ids"] = [predecessor]
            self.assertEqual(incident_frontier(index)["state"], "unknown")

    def test_frontier_follows_retained_closed_intermediate_headers(self):
        index = self.headers()
        closed = index["tasks"][1]
        closed.update(state="closed", completion_evidence={"path": "closure.json", "sha256": "a" * 64})
        current = copy.deepcopy(index["tasks"][0]); current.update(task_id="current", predecessor_task_ids=["next"])
        index["tasks"].append(current)
        result = incident_frontier(index)
        self.assertEqual(result["frontier"], ["current"])
        self.assertEqual(result["retained_active"], ["current", "first"])

    def test_incomplete_frontier_names_the_header_field_without_echoing_values(self):
        index = self.headers(); del index["tasks"][1]["completion_evidence"]
        result = incident_frontier(index)
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(result["retained_active"], ["first", "next"])
        self.assertTrue(any("tasks.1" in error and "completion_evidence" in error for error in result["errors"]))

    def report(self, findings):
        payload = findings_payload([Finding(item["level"], item["code"], item["message"], item.get("path")) for item in findings], target=ROOT, strict_warnings=False)
        payload["comparison_context"] = {"configuration_sha256": "b" * 64, "producer_sha256": "c" * 64}
        return payload

    def test_report_comparison_preserves_duplicates_and_unknown_baselines(self):
        finding = {"level": "error", "code": "X", "path": "owner.md", "message": "Open original failure"}
        current = self.report([finding]); baseline = self.report([finding, finding])
        result = reconcile_findings(current, baseline)
        self.assertEqual(result["state"], "comparable")
        self.assertEqual(result["entries"][0]["carried_count"], 1)
        self.assertEqual(result["entries"][0]["not_observed_count"], 1)
        self.assertEqual(reconcile_findings(current)["state"], "unknown")
        for key, value in (("target", "another"), ("validation_scope", "changed"), ("comparison_context", {}), ("counts", {"errors": 0})):
            other = copy.deepcopy(baseline); other[key] = value
            self.assertEqual(reconcile_findings(current, other)["state"], "unknown")
        moved = copy.deepcopy(current); moved["findings"][0]["path"] = "moved.md"
        result = reconcile_findings(moved, baseline)
        self.assertEqual(sum(item["introduced_count"] for item in result["entries"]), 1)

    def test_unknown_identity_and_contradictory_outcomes_are_not_comparable(self):
        finding = {"level": "error", "code": "X", "path": None, "message": "Failure"}
        baseline = self.report([finding])
        for value in (None, {}, [], "", "unknown", "relative-target"):
            current = self.report([]); current["target"] = value
            before = copy.deepcopy(baseline); before["target"] = value
            self.assertEqual(reconcile_findings(current, before)["state"], "unknown")
        current = copy.deepcopy(baseline); current["status"] = "passed"
        self.assertEqual(reconcile_findings(current, baseline)["state"], "unknown")
        current["exit_code"] = 0
        self.assertEqual(reconcile_findings(current, baseline)["state"], "unknown")

    def test_upgrade_router_integrates_exact_baseline_without_waiving_findings(self):
        finding = {"level": "error", "code": "X", "path": "owner.md", "message": "Failure"}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            impact, report, before = (root/name for name in ("impact.json", "current.json", "baseline.json"))
            impact.write_text(json.dumps({"routing": {"candidate_context": []}}))
            report.write_text(json.dumps(self.report([finding])))
            before.write_text(json.dumps(self.report([finding, finding])))
            original = report.read_bytes()
            add_validation_impact(impact, report, before)
            result = json.loads(impact.read_text())
            self.assertEqual(result["finding_reconciliation"]["state"], "comparable")
            self.assertEqual(result["finding_reconciliation"]["entries"][0]["not_observed_count"], 1)
            self.assertIn("owner.md", result["routing"]["candidate_context"])
            self.assertEqual(report.read_bytes(), original)
            before.write_text("[" * 1100)
            with self.assertRaisesRegex(ValueError, "invalid JSON"):
                add_validation_impact(impact, report, before)

    def test_malformed_comparison_fields_return_unknown_not_exceptions(self):
        finding = {"level": "error", "code": "X", "path": "owner.md", "message": "Failure"}
        baseline = self.report([finding])
        paths = [(key,) for key in ("target", "schema_version", "counts", "evidence", "comparison_context", "approval_archive", "findings")]
        paths.extend([("counts", "errors"), ("evidence", "observed_revision"), ("approval_archive", "mode"), ("findings", 0, "level"), ("findings", 0, "path"), ("findings", 0, "blocking")])
        for path in paths:
            for bad in (None, [], {}, True, 1.0, "unknown"):
                current = copy.deepcopy(baseline)
                execution_fixtures.set_path(current, path, bad)
                with self.subTest(path=path, bad=bad): self.assertIsInstance(reconcile_findings(current, baseline), dict)

    def test_public_doctor_frontier_is_advisory_and_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            index = root/".ai/assistant/active-tasks.json"
            index.parent.mkdir(parents=True)
            index.write_text(json.dumps(self.headers()))
            before = index.read_bytes()
            command = [sys.executable, "-B", str(ROOT/"tools/alatyr.py"), "doctor", "--target", str(root), "--json"]
            base = subprocess.run(command, capture_output=True, text=True)
            view = subprocess.run([*command, "--incident-frontier"], capture_output=True, text=True)
            original, enriched = json.loads(base.stdout), json.loads(view.stdout)
            self.assertEqual(enriched["incident_frontier"]["retained_active"], ["first", "next"])
            self.assertEqual(enriched["counts"], original["counts"])
            self.assertEqual(view.returncode, base.returncode)
            self.assertEqual(index.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()

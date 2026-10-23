from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import unittest

import tests.test_incident_quality as incident_fixtures
from tests.test_incident_quality import review_record, repair_policy
from repair_review import evidence_failures
from test_execution_contract import TestExecutionContract


def qualification_policy():
    value = repair_policy()
    value.update(schema_version=2, qualification={"assertions": [
        {"id": "actual-scenario", "boundary": "entrypoint", "command_ids": ["unit"],
         "artifact_pointer": "/observed/variant", "expected": "expiry-in-transit", "stage": "diagnosis", "control_pointer": None},
        {"id": "mechanism", "boundary": "producers-consumers", "command_ids": ["unit"],
         "artifact_pointer": "/observed/mechanism", "expected": "independent-producers", "stage": "diagnosis", "control_pointer": "/control/mechanism"},
        {"id": "original-flow", "boundary": "positive-preconditions", "command_ids": ["unit"],
         "artifact_pointer": "/observed/original_flow", "expected": True, "stage": "acceptance", "control_pointer": None},
    ], "performance": []})
    return value


def qualified_record():
    value = review_record()
    value.update(schema_version=2, repair_stage="acceptance", performance_comparisons=[], observations=[
        {"assertion_id": key, "run_ref": ref} for key, ref in (
            ("actual-scenario", "diagnostic.json"), ("mechanism", "diagnostic.json"), ("original-flow", "current.json"))])
    for boundary in value["fixture_boundaries"]:
        if boundary["id"] in {"entrypoint", "producers-consumers"}:
            boundary["evidence_refs"] = ["diagnostic.json"]
    return value


def observed():
    return {"observed": {"variant": "expiry-in-transit", "mechanism": "independent-producers", "original_flow": True},
            "control": {"mechanism": "serialized-substitute"}}


class RepairQualificationTests(unittest.TestCase):
    def setUp(self):
        fixture = incident_fixtures.RepairReviewTests()
        fixture.setUp()
        self.runs, self.schema = fixture.runs, fixture.schema
        self.policy, self.record = qualification_policy(), qualified_record()
        self.artifacts = {key: observed() for key in self.runs}

    def failures(self, *, completion=True):
        return evidence_failures(self.record, self.policy, self.runs, self.schema,
                                 completion=completion, artifacts=self.artifacts)

    def test_valid_qualification_and_legacy_contract(self):
        self.assertEqual(self.failures(), [])
        self.assertEqual(evidence_failures(review_record(), repair_policy(), self.runs, self.schema, completion=True), [])

    def test_wrong_actual_branch_and_topology_cannot_qualify(self):
        for key, value in (("variant", "after-client"), ("mechanism", "serialized-substitute")):
            with self.subTest(key=key):
                self.artifacts["diagnostic.json"] = observed()
                self.artifacts["diagnostic.json"]["observed"][key] = value
                self.assertTrue(self.failures())

    def test_missing_observations_and_unchanged_control_are_rejected(self):
        for artifact in ({}, [], None, {"observed": {"mechanism": "independent-producers"}, "control": {"mechanism": "independent-producers"}}):
            self.artifacts["diagnostic.json"] = artifact
            self.assertTrue(self.failures())
        self.artifacts["diagnostic.json"] = observed()
        self.record["observations"].pop()
        self.assertTrue(self.failures())

    def test_failed_diagnostic_can_qualify_without_premature_green(self):
        self.runs["diagnostic.json"].update(state="failed", claim="none")
        self.record["attempts"][0]["failure_class"] = "production"
        self.record.update(claim="component-only", repair_stage="qualified-repair")
        self.assertEqual(self.failures(completion=False), [])
        self.assertTrue(self.failures(completion=True))

    def test_unexecuted_investigation_is_allowed_but_not_qualified(self):
        self.record.update(claim="unverified", diagnosis=None, attempts=[], observations=[], repair_stage="diagnostic")
        for boundary in self.record["fixture_boundaries"]:
            boundary.update(state="unknown", reason="Investigation has not executed yet", evidence_refs=[])
        self.runs = {}
        self.assertEqual(self.failures(completion=False), [])
        self.record["repair_stage"] = "qualified-repair"
        self.assertTrue(self.failures(completion=False))

    def test_policy_v2_cannot_accept_legacy_evidence_or_boolean_numeric_aliases(self):
        self.record = review_record()
        self.assertTrue(self.failures())
        policy = qualification_policy()
        policy["qualification"]["assertions"][0]["expected"] = "unknown"
        target = {"commands": [{"id": "unit", "execution": {"proof_boundary": "end-to-end", "suite_scope": "full", "kind": "automated-test"}}]}
        from repair_review import policy_failures
        self.assertTrue(policy_failures(policy, target, self.schema))

    def test_selected_observations_reject_malformed_and_unrelated_bindings(self):
        for bad in (None, [], {}, True, 1, "unknown"):
            for key in ("assertion_id", "run_ref"):
                self.record = qualified_record()
                self.record["observations"][0][key] = bad
                self.assertTrue(self.failures())
        self.record = qualified_record()
        self.record["observations"][0]["run_ref"] = "current.json"
        self.assertTrue(self.failures())

    def test_boolean_numeric_coercion_and_missing_are_not_observations(self):
        self.policy["qualification"]["assertions"][-1]["expected"] = 1
        self.assertTrue(self.failures())
        self.artifacts["current.json"]["observed"]["original_flow"] = 1
        self.assertEqual(self.failures(), [])
        self.policy["qualification"]["assertions"][-1]["expected"] = False
        self.artifacts["current.json"]["observed"]["original_flow"] = False
        self.assertEqual(self.failures(), [])

    def test_policy_qualification_mutations_never_crash(self):
        from tests.test_test_execution_contract import policy, nested_paths, set_path
        base = policy(); base["repair_review"] = qualification_policy()
        contract = TestExecutionContract()
        for path in nested_paths(base["repair_review"]):
            for bad in (None, True, 2, "", [], {}, ["invalid"], float("nan"), float("inf")):
                value = copy.deepcopy(base)
                set_path(value["repair_review"], path, bad)
                with self.subTest(path=path, bad=bad):
                    self.assertIsInstance(contract.policy_failures(value), list)

    def test_json_pointer_escapes_arrays_and_missing_values(self):
        from repair_qualification import pointer_value, MISSING
        value = {"a/b": {"~": [False, 0, "actual"]}}
        self.assertEqual(pointer_value(value, "/a~1b/~0/2"), "actual")
        for pointer in ("", "/a~2b", "/a~1b/~0/01", "/a~1b/~0/-1", "/a~1b/~0/3", "/a~1b/~0/true", "/a~1b/~0/0/child"):
            self.assertIs(pointer_value(value, pointer), MISSING)

    def test_malformed_pointer_does_not_trigger_exponential_schema_backtracking(self):
        program = "from tests.test_repair_qualification import qualification_policy; from tests.test_test_execution_contract import policy; from test_execution_contract import TestExecutionContract; p=policy(); p['repair_review']=qualification_policy(); p['repair_review']['qualification']['assertions'][0]['artifact_pointer']='/a'*200+'~x'; failures=TestExecutionContract().policy_failures(p); assert any('artifact_pointer' in failure for failure in failures), failures"
        result = subprocess.run([sys.executable, "-B", "-c", program], cwd=incident_fixtures.ROOT,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_new_record_fields_reject_all_nested_json_mutations_without_crashing(self):
        from tests.test_test_execution_contract import nested_paths, set_path
        baseline = qualified_record()
        for path in nested_paths(baseline):
            for bad in (None, True, 3, "", [], {}, ["invalid"], {"wrong": []}):
                self.record = copy.deepcopy(baseline)
                set_path(self.record, path, bad)
                with self.subTest(path=path, bad=bad):
                    self.assertIsInstance(self.failures(), list)

    def test_retry_requires_actual_qualified_diagnostic_not_output_or_stage_label(self):
        failed = copy.deepcopy(self.runs["current.json"])
        failed.update(state="failed", claim="none", run_window={"started_at": "2026-10-22T09:00:00Z", "finished_at": "2026-10-22T09:00:30Z"})
        self.runs["failed.json"] = failed
        first = copy.deepcopy(self.record["attempts"][-1])
        first.update(run_ref="failed.json", failure_class="production")
        self.record["attempts"].insert(0, first)
        self.record["attempts"][1]["failure_ref"] = "failed.json"
        self.record["attempts"][-1]["reassessment_ref"] = "diagnostic.json"
        self.record["observations"].append({"assertion_id": "original-flow", "run_ref": "failed.json"})
        next(item for item in self.record["fixture_boundaries"] if item["id"] == "positive-preconditions")["evidence_refs"].append("failed.json")
        self.artifacts["failed.json"] = observed()
        self.assertEqual(self.failures(), [])
        self.artifacts["diagnostic.json"]["control"]["mechanism"] = "independent-producers"
        self.assertTrue(self.failures())

    def test_multiple_commands_require_only_applicable_assertions(self):
        self.policy["qualification"]["assertions"].append({**self.policy["qualification"]["assertions"][1], "id": "other-diagnostic", "command_ids": ["other"]})
        self.assertEqual(self.failures(), [])

    def test_qualified_diagnosis_requires_the_attempts_declared_hypothesis(self):
        self.record.update(claim="component-only", repair_stage="qualified-repair")
        for hypothesis in ("not-declared", "fixture"):
            self.record["diagnosis"]["hypothesis_id"] = hypothesis
            self.assertTrue(self.failures(completion=False))

    def test_assertions_bind_their_actual_fixture_boundary_and_cannot_be_not_applicable(self):
        boundary = next(item for item in self.record["fixture_boundaries"] if item["id"] == "entrypoint")
        boundary["evidence_refs"] = ["current.json"]
        self.assertTrue(self.failures())
        boundary.update(state="not-applicable", evidence_refs=["diagnostic.json"])
        self.assertTrue(self.failures())
        self.record["fixture_boundaries"] = []
        self.assertTrue(self.failures())


def metric():
    return {"id": "cpu", "artifact_pointer": "/metrics/cpu", "unit": "us",
            "direction": "lower-is-better", "max_regression_percent": 10, "min_samples": 3,
            "max_spread_percent": 20, "comparability_pointers": ["/mode", "/fixture", "/instrumentation"]}


class PerformanceQualificationTests(unittest.TestCase):
    def setUp(self):
        RepairQualificationTests.setUp(self)
        self.policy["qualification"]["performance"] = [metric()]
        self.record["performance_comparisons"] = [{"metric_id": "cpu", "baseline": {
            "run": {"path": "baseline.json", "sha256": "b" * 64},
            "policy": {"path": "baseline-policy.json", "sha256": "c" * 64}}, "candidate_run_ref": "current.json"}]
        self.runs["baseline.json"] = copy.deepcopy(self.runs["current.json"])
        self.runs["baseline.json"].update(run_window={"started_at": "2026-10-22T08:00:00Z", "finished_at": "2026-10-22T08:01:00Z"})
        self.runs["baseline.json"]["result_artifact"]["path"] = "baseline-result.txt"
        for ref in ("baseline.json", "current.json"):
            self.artifacts[ref] = {**observed(), "mode": "native", "fixture": "real-flow", "instrumentation": "off", "metrics": {"cpu": {"unit": "us", "samples": [100, 100, 100]}}}

    def failures(self, *, completion=True):
        return evidence_failures(self.record, self.policy, self.runs, self.schema, completion=completion,
                                 current_refs={"current.json", "diagnostic.json"}, artifacts=self.artifacts)

    def test_median_regression_below_at_and_above_limit(self):
        for value in (109, 110, 111):
            self.artifacts["current.json"]["metrics"]["cpu"]["samples"] = [value] * 3
            with self.subTest(value=value):
                self.assertEqual(bool(self.failures()), value > 110)

    def test_decimal_boundary_does_not_depend_on_binary_rounding(self):
        self.artifacts["baseline.json"]["metrics"]["cpu"]["samples"] = [100.1] * 3
        for value, rejected in ((110.109, False), (110.11, False), (110.111, True)):
            self.artifacts["current.json"]["metrics"]["cpu"]["samples"] = [value] * 3
            self.assertEqual(bool(self.failures()), rejected)

    def test_malformed_samples_and_conditions_fail_closed(self):
        for value in ([], {}, None, [True] * 3, [float("nan")] * 3, [float("inf")] * 3, [-1] * 3, [100] * 2, [100] * 257):
            self.artifacts["current.json"]["metrics"]["cpu"]["samples"] = value
            self.assertTrue(self.failures())
        self.artifacts["current.json"]["metrics"]["cpu"]["samples"] = [100] * 3
        for key, value in (("mode", "vm-fallback"), ("instrumentation", "profiler"), ("fixture", "substitute")):
            old = self.artifacts["current.json"][key]
            self.artifacts["current.json"][key] = value
            self.assertTrue(self.failures())
            self.artifacts["current.json"][key] = old

    def test_zero_baseline_units_spread_and_missing_comparisons(self):
        self.artifacts["baseline.json"]["metrics"]["cpu"]["samples"] = [0] * 3
        self.assertTrue(self.failures())
        self.artifacts["current.json"]["metrics"]["cpu"]["samples"] = [0] * 3
        self.assertEqual(self.failures(), [])
        self.artifacts["current.json"]["metrics"]["cpu"]["unit"] = "ms"
        self.assertTrue(self.failures())
        self.record["performance_comparisons"] = []
        self.assertTrue(self.failures())

    def test_higher_is_better_even_median_and_spread_budget(self):
        self.policy["qualification"]["performance"][0].update(direction="higher-is-better", min_samples=2)
        for samples, rejected in (([89, 89], True), ([90, 90], False), ([91, 91], False), ([0, 200], True)):
            self.artifacts["current.json"]["metrics"]["cpu"]["samples"] = samples
            self.assertEqual(bool(self.failures()), rejected)

    def test_performance_pass_does_not_waive_original_failure(self):
        self.runs["current.json"].update(state="failed", claim="none")
        self.record["attempts"][-1]["failure_class"] = "production"
        self.artifacts["current.json"]["metrics"]["cpu"]["samples"] = [50] * 3
        self.assertTrue(self.failures())

    def test_copied_candidate_cannot_masquerade_as_independent_baseline(self):
        self.runs["baseline.json"] = copy.deepcopy(self.runs["current.json"])
        self.assertTrue(self.failures())

    def test_measurement_baseline_cannot_qualify_fixture_boundaries(self):
        for boundary in self.record["fixture_boundaries"]:
            boundary["evidence_refs"] = ["baseline.json"]
        self.assertTrue(self.failures())


class RegisteredQualificationTests(incident_fixtures.task_fixtures.ActiveTaskFixture):
    save = incident_fixtures.RegisteredRepairReviewTests.save

    def configure(self):
        incident_fixtures.RegisteredRepairReviewTests.configure(self)
        self.helper.write(self.target, ".ai/assistant/templates/repair-qualification.json", (incident_fixtures.ROOT/"templates/target/.ai/assistant/templates/repair-qualification.json").read_text())
        self.run["input_sha256"][".ai/assistant/templates/repair-qualification.json"] = hashlib.sha256((self.target/".ai/assistant/templates/repair-qualification.json").read_bytes()).hexdigest()
        self.helper.write(self.target, ".ai/framework/repair-qualification.md", (incident_fixtures.ROOT/"framework/repair-qualification.md").read_text())
        self.run["input_sha256"][".ai/framework/repair-qualification.md"] = hashlib.sha256((self.target/".ai/framework/repair-qualification.md").read_bytes()).hexdigest()
        self.policy["repair_review"] = qualification_policy()
        self.review = qualified_record()
        self.write_artifact(observed())

    def write_artifact(self, value, *, raw=False):
        self.helper.write(self.target, "result.txt", value if raw else json.dumps(value))
        self.run["result_artifact"]["sha256"] = hashlib.sha256((self.target/"result.txt").read_bytes()).hexdigest()
        self.save()

    def test_public_active_task_path_checks_actual_child_scenario(self):
        self.configure()
        self.assertEqual(self.errors(self.check()), set())
        program = "import json,sys; print(json.dumps({'observed': {'variant':sys.argv[1], 'mechanism':'independent-producers', 'original_flow':True}, 'control':{'mechanism':'serialized-substitute'}}))"
        for variant in ("expiry-in-transit", "after-client"):
            result = subprocess.run([sys.executable, "-B", "-c", program, variant], capture_output=True, text=True, check=True)
            self.write_artifact(result.stdout, raw=True)
            findings = self.check()
            with self.subTest(variant=variant):
                self.assertEqual("TDD_EXECUTION_EVIDENCE" in self.errors(findings), variant != "expiry-in-transit", [item.message for item in findings.findings])

    def test_public_path_rejects_malformed_duplicate_and_stale_artifacts(self):
        self.configure()
        for raw in ("{", "[]", '{"observed":1,"observed":2}', '{"observed": NaN}', "[" * 1200 + "]" * 1200, " " * (128 * 1024 + 1)):
            self.write_artifact(raw, raw=True)
            self.assertTrue(self.errors(self.check()))
        self.write_artifact(observed())
        (self.target/"result.txt").write_text('{"changed":true}')
        self.assertIn("TDD_EXECUTION_EVIDENCE_STALE", self.errors(self.check()))

    def test_public_path_binds_run_and_policy(self):
        self.configure()
        self.review["attempts"][0]["run_sha256"] = "0" * 64
        self.helper.write(self.target, "repair.json", self.review)
        self.assertIn("TDD_EXECUTION_EVIDENCE_STALE", self.errors(self.check()))
        self.save()
        self.policy["repair_review"]["qualification"]["assertions"][0]["expected"] = "different-scenario"
        self.save()
        self.assertIn("TDD_EXECUTION_EVIDENCE", self.errors(self.check()))

    def test_public_measurement_baseline_is_bound_and_never_current_acceptance(self):
        self.configure()
        self.policy["repair_review"]["qualification"]["performance"] = [metric()]
        self.write_artifact({**observed(), "mode": "native", "fixture": "real-flow", "instrumentation": "off", "metrics": {"cpu": {"unit": "us", "samples": [100] * 3}}})
        baseline_policy = ".ai/assistant/task-evidence/baseline-policy.json"
        baseline_ref = ".ai/assistant/task-evidence/baseline.json"
        self.helper.write(self.target, baseline_policy, self.policy)
        captured = copy.deepcopy(self.run)
        captured["run_window"] = {"started_at": "2026-10-22T08:00:00Z", "finished_at": "2026-10-22T08:01:00Z"}
        baseline_output = ".ai/assistant/task-evidence/baseline-result.json"
        self.helper.write(self.target, baseline_output, (self.target/"result.txt").read_text())
        captured["result_artifact"] = self.bind(self.target/baseline_output)
        captured["policy_sha256"] = hashlib.sha256((self.target/baseline_policy).read_bytes()).hexdigest()
        self.helper.write(self.target, baseline_ref, captured)
        for path in (baseline_ref, baseline_policy, baseline_output):
            self.run["input_sha256"][path] = hashlib.sha256((self.target/path).read_bytes()).hexdigest()
        self.review["performance_comparisons"] = [{"metric_id": "cpu", "baseline": {
            "run": self.bind(self.target/baseline_ref), "policy": self.bind(self.target/baseline_policy)}, "candidate_run_ref": "current.json"}]
        self.save()
        self.assertEqual(self.errors(self.check()), set(), [item.message for item in self.check().findings])
        original = copy.deepcopy(captured)
        captured.update(run_window=self.run["run_window"], result_artifact=self.run["result_artifact"])
        self.helper.write(self.target, baseline_ref, captured)
        self.run["input_sha256"][baseline_ref] = hashlib.sha256((self.target/baseline_ref).read_bytes()).hexdigest()
        self.review["performance_comparisons"][0]["baseline"]["run"] = self.bind(self.target/baseline_ref)
        self.save()
        findings = self.check()
        self.assertTrue(any("distinct ordered" in item.message for item in findings.findings))
        self.helper.write(self.target, baseline_ref, original)
        self.run["input_sha256"][baseline_ref] = hashlib.sha256((self.target/baseline_ref).read_bytes()).hexdigest()
        self.review["performance_comparisons"][0]["baseline"]["run"] = self.bind(self.target/baseline_ref)
        original_boundaries = copy.deepcopy(self.review["fixture_boundaries"])
        for boundary in self.review["fixture_boundaries"]:
            boundary["evidence_refs"] = [baseline_ref]
        self.save()
        self.assertIn("TDD_EXECUTION_EVIDENCE", self.errors(self.check()))
        self.review["fixture_boundaries"] = original_boundaries
        self.review["performance_comparisons"][0]["baseline"]["run"]["sha256"] = "0" * 64
        self.helper.write(self.target, "repair.json", self.review)
        self.assertIn("TDD_EXECUTION_EVIDENCE_STALE", self.errors(self.check()))

    def test_public_path_preserves_known_red_without_premature_green(self):
        self.configure()
        self.policy["repair_review"] = qualification_policy()
        self.review.update(claim="component-only", repair_stage="qualified-repair")
        self.run.update(state="failed", claim="none", counts={"discovered": 1, "executed": 1, "passed": 0, "failed": 1, "skipped": 0})
        self.review["attempts"][-1]["failure_class"] = "production"
        self.model["original_case"]["status"] = "still-failing"
        self.write_model(); self.write_index(); self.save()
        diagnostic = json.loads((self.target/"diagnostic.json").read_bytes())
        diagnostic["claim"] = "none"
        self.helper.write(self.target, "diagnostic.json", diagnostic)
        self.review["attempts"][0].update(failure_class="production", run_sha256=hashlib.sha256((self.target/"diagnostic.json").read_bytes()).hexdigest())
        self.helper.write(self.target, "repair.json", self.review)
        self.assertEqual(self.errors(self.check()), set(), [item.message for item in self.check().findings])
        self.close()
        self.assertIn("TDD_EXECUTION_EVIDENCE", self.errors(self.check()))

    def test_captured_qualification_cannot_downgrade_or_rewrite_expectations(self):
        self.configure()
        incident_fixtures.task_fixtures.git(self.target, "add", ".")
        incident_fixtures.task_fixtures.git(self.target, "commit", "-qm", "capture active schema-2 qualification")
        self.policy["repair_review"] = repair_policy()
        self.review = review_record(); self.save()
        self.assertIn("TDD_EXECUTION_CONTRACT", self.errors(self.check()))
        self.policy["repair_review"] = qualification_policy()
        self.review = qualified_record()
        self.policy["repair_review"]["qualification"]["assertions"][0]["expected"] = "new-expectation"
        self.save()
        checked = self.check()
        self.assertTrue(any("cannot be removed or rewritten" in item.message for item in checked.findings))

    def test_qualified_repair_cannot_use_an_unrelated_hypothesis_or_missing_guidance(self):
        self.configure()
        self.review.update(claim="component-only", repair_stage="qualified-repair")
        self.review["diagnosis"]["hypothesis_id"] = "fixture"
        self.save()
        self.assertIn("TDD_EXECUTION_EVIDENCE", self.errors(self.check()))
        self.review["diagnosis"]["hypothesis_id"] = "queue"
        self.save()
        (self.target/".ai/framework/repair-qualification.md").unlink()
        self.assertIn("TDD_EXECUTION_CONTRACT", self.errors(self.check()))


class CanonicalIncidentViewTests(unittest.TestCase):
    def test_navigation_links_bound_owners_without_replacing_or_mutating_them(self):
        from incident_planning import incident_frontier
        index = incident_fixtures.IncidentPlanningTests().headers()
        index["tasks"][1]["problem_model"] = {"path": "model.json", "sha256": "a" * 64}
        original = copy.deepcopy(index)
        result = incident_frontier(index)
        selected = result["task_references"][1]
        self.assertEqual(selected["problem_model"], index["tasks"][1]["problem_model"])
        self.assertEqual(selected["next_check"], "inspect-bound-model-and-selected-run-evidence")
        self.assertEqual(selected["latest_failed_gate_id"], "original-failure")
        self.assertEqual(index, original)


if __name__ == "__main__":
    unittest.main()

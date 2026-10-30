from __future__ import annotations

import copy
import json
import subprocess
import sys
from unittest.mock import patch

from tests.active_task_fixture import ActiveTaskFixture
from tests.test_analysis_evidence import ROOT, add_evidence
from analysis_evidence import next_action_advice, probe_binding
from analysis_strategy_contract import (canonical_utf8_size, load_json_object,
                                        structured_word_count, validate_problem_model)
from check_change_packages import changed_index_validator
from current_task_view import current_task_view


class ExecutionFocusTests(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        self.artifact = add_evidence(self.model, self.target)
        self.schema = load_json_object(ROOT / "schemas/alatyr-problem-model.schema.json")

    def failures(self, model):
        return validate_problem_model(model, self.schema)

    def test_every_pack_ships_the_canonical_checkpoint_with_optional_leaf_fallback(self):
        from framework_packaging import resolve_framework_files
        owner = "task-decomposition.md"
        for pack in ("kernel", "core", "standard", "complete"):
            with self.subTest(pack=pack):
                self.assertIn(owner, resolve_framework_files(pack))
        content = (ROOT / "framework" / owner).read_text(encoding="utf-8")
        self.assertIn("otherwise use the bound active projection manually", content)

    def add_probe(self, identity, *, status="open", required=True, requires=()):
        proof = copy.deepcopy(self.model["proof_obligations"][0])
        proof.update(id=identity, status=status, required=required)
        self.model["proof_obligations"].append(proof)
        probe = copy.deepcopy(self.model["analysis_evidence"]["probes"][0])
        probe.update(obligation_id=identity, result=None)
        self.model["analysis_evidence"]["probes"].append(probe)
        self.model.setdefault("execution_dependencies", [
            {"obligation_id": row["id"], "requires": []}
            for row in self.model["proof_obligations"][:-1]
        ]).append({"obligation_id": identity, "requires": list(requires)})

    def selected(self):
        self.assertEqual(self.failures(self.model), [])
        self.write_model()
        self.write_index()
        return current_task_view(changed_index_validator(self.target), "fixture-task")

    def test_stale_artifact_clears_ready_and_focus_without_losing_duties(self):
        self.add_probe("next-proof")
        self.selected()
        (self.target / "design.md").write_bytes(b"changed accepted rule\n")
        view = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(view["next_action_advice"]["state"], "blocked-by-stale-evidence")
        readiness = view["execution_readiness"]
        self.assertEqual(readiness["state"], "blocked-by-stale-evidence")
        self.assertEqual(readiness["ready"], [])
        self.assertIn("next-proof", readiness["retained_unresolved"])
        self.assertIsNone(view["execution_focus"]["next_action"])
        self.assertFalse(view["execution_focus"]["authorization_granted"])

    def test_missing_selected_runtime_clears_action_candidates_but_retains_duties(self):
        from publish_active_task import prepare
        from support_write_transaction import SupportTransaction
        self.add_probe("next-proof")
        evidence = self.model["analysis_evidence"]
        retained_artifact = self.target / "probe-result.txt"
        retained_artifact.write_bytes((self.target / self.artifact).read_bytes())
        for key in ("proof_obligations", "hypotheses", "counterexamples"):
            for row in self.model[key]:
                row["evidence_refs"] = ["probe-result.txt" if path == self.artifact else path for path in row["evidence_refs"]]
        for artifact in (evidence["probes"][0]["result"]["artifacts"][0],
                         evidence["review_challenges"][0]["artifacts"][0]):
            artifact["path"] = "probe-result.txt"
        self.selected()
        draft = self.target / ".ai/.runtime/draft.json"
        draft.write_text(json.dumps(self.model))
        plan = prepare(self.target, "fixture-task", draft.relative_to(self.target).as_posix(), retention_review="reviewed-portable-evidence")
        SupportTransaction(self.target).apply(plan.outputs, expected_inputs=plan.inputs)
        projection = self.target / self.model["active_projection"]["path"]
        original = projection.read_bytes()
        projection.unlink()
        view = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(view["state"], "bound-recorded-disposition")
        self.assertEqual(view["execution_readiness"]["state"], "blocked-by-runtime-evidence")
        self.assertEqual(view["execution_readiness"]["ready"], [])
        self.assertIn("next-proof", view["execution_readiness"]["retained_unresolved"])
        self.assertEqual(view["next_action_advice"]["candidates"], [])
        self.assertEqual(view["execution_focus"]["state"], "blocked-by-runtime-evidence")
        self.assertIsNone(view["execution_focus"]["next_action"])
        projection.write_bytes(original)
        restored = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(restored["execution_focus"]["next_action"]["obligation_id"], "next-proof")

    def test_blocked_waiting_and_unconfigured_probes_are_not_action_candidates(self):
        self.add_probe("blocked", status="blocked")
        self.add_probe("waiting", requires=["blocked"])
        self.add_probe("ready-optional", required=False)
        view = self.selected()
        advice = view["next_action_advice"]
        self.assertEqual([row["obligation_id"] for row in advice["candidates"]], ["ready-optional"])
        retained = {row["obligation_id"]: row for row in advice["retained_candidates"]}
        self.assertEqual(retained["blocked"]["eligibility"], "blocked")
        self.assertEqual(retained["waiting"]["unsettled_prerequisites"], ["blocked"])
        self.assertIn("blocked", advice["unresolved_required"])
        self.assertEqual(view["execution_focus"]["next_action"]["obligation_id"], "ready-optional")
        self.model.pop("execution_dependencies")
        advice = next_action_advice(self.model, "a" * 64)
        self.assertEqual(advice["candidates"], [])
        self.assertTrue(all(row["eligibility"] == "dependency-unconfigured" for row in advice["retained_candidates"]))

    def test_action_has_task_digest_question_and_completion_condition(self):
        self.add_probe("next-proof")
        view = self.selected()
        focus = view["execution_focus"]
        self.assertEqual(focus["model"], view["model"])
        self.assertEqual(focus["task_id"], "fixture-task")
        self.assertEqual(focus["objective"], self.model["objective"])
        self.assertEqual(focus["scope"]["invariant_ids"], [row["id"] for row in self.model["invariants"]])
        self.assertEqual(focus["next_action"]["completion_condition"], self.model["proof_obligations"][-1]["statement"])
        self.assertEqual(focus["next_action"]["unknown_ids"], ["uncertainty"])
        self.assertEqual(focus["intent_currentness"], "primary-verification-required")
        self.assertEqual(focus["execution_interception"], "not-performed")
        self.assertFalse(focus["acceptance_granted"])

    def test_blocked_work_keeps_its_unsettled_prerequisites(self):
        self.add_probe("prerequisite", status="blocked")
        self.add_probe("blocked-dependent", status="blocked", requires=["prerequisite"])
        view = self.selected()
        self.assertEqual(view["execution_readiness"]["unsettled_prerequisites"]["blocked-dependent"], ["prerequisite"])
        retained = {row["obligation_id"]: row for row in view["next_action_advice"]["retained_candidates"]}
        self.assertEqual(retained["blocked-dependent"]["eligibility"], "blocked")
        self.assertEqual(retained["blocked-dependent"]["unsettled_prerequisites"], ["prerequisite"])

    def test_pending_revision_and_original_failure_require_reanchoring(self):
        self.add_probe("next-proof")
        self.model["analysis_evidence"]["updates"] = [{
            "id": "new-evidence", "reason": "An observation requires another test",
            "evidence_refs": [self.artifact], "hypothesis_ids": ["explanation"],
            "invalidated_assumption_ids": [], "reopened_obligation_ids": ["next-proof"],
            "artifacts": [self.bind(self.target / self.artifact)],
            "state": "pending", "resolution_evidence_refs": [],
        }]
        self.model["original_case"] = {"source_ref": "request:identity-regression", "actor": "developer",
            "input": "Complete original workflow", "expected_outcome": "Workflow succeeds",
            "status": "still-failing", "evidence_refs": [], "supersession": None}
        focus = self.selected()["execution_focus"]
        self.assertEqual(focus["state"], "reanchor-required")
        self.assertTrue(focus["next_action"]["reanchor_required"])
        self.assertIn("evidence-revision-pending", [row["reason"] for row in focus["reanchor_signals"]])
        self.assertEqual(focus["original_case_status"], "still-failing")
        self.assertIn("next-proof", focus["unresolved_required_ids"])

    def test_reanchor_signal_does_not_hide_independent_ready_work(self):
        self.add_probe("blocked", status="blocked")
        self.add_probe("independent", required=False)
        self.model["unresolved_decisions"] = ["decision:blocked-area"]
        focus = self.selected()["execution_focus"]
        self.assertEqual(focus["state"], "reanchor-required")
        self.assertEqual(focus["eligible_obligation_ids"], ["independent"])
        self.assertEqual(focus["next_action"]["obligation_id"], "independent")
        self.assertTrue(focus["next_action"]["reanchor_required"])
        self.assertIn("blocked", focus["unresolved_required_ids"])

    def test_closed_task_has_no_active_recommendation_or_acceptance_claim(self):
        self.write_model(); self.write_index()
        self.close()
        view = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(view["execution_focus"]["state"], "historical-disposition")
        self.assertIsNone(view["execution_focus"]["next_action"])
        self.assertFalse(view["execution_focus"]["acceptance_granted"])

    def test_missing_or_malformed_selected_model_never_exposes_focus(self):
        self.selected()
        for bad in (None, [], {"schema_version": True}, {"objective": {}}):
            with self.subTest(bad=bad):
                self.model_path.write_text(json.dumps(bad), encoding="utf-8")
                self.task["problem_model"] = self.bind(self.model_path)
                self.write_index()
                view = current_task_view(changed_index_validator(self.target), "fixture-task")
                self.assertEqual(view["state"], "unknown")
                self.assertNotIn("execution_focus", view)

    def test_recorded_unsettled_probe_requires_retry_review(self):
        self.add_probe("retry")
        probe = self.model["analysis_evidence"]["probes"][-1]
        probe["result"] = copy.deepcopy(self.model["analysis_evidence"]["probes"][0]["result"])
        probe["result"]["probe_sha256"] = probe_binding(self.model, probe)
        focus = self.selected()["execution_focus"]
        self.assertEqual(focus["state"], "reanchor-required")
        self.assertTrue(focus["next_action"]["retry_review_required"])
        self.assertIn("recorded-probe-needs-retry-review", [row["reason"] for row in focus["reanchor_signals"]])

    def test_reference_fallback_itself_obeys_the_portable_limits(self):
        import execution_focus
        self.add_probe("next-proof")
        view = self.selected()
        task = {**self.task, "task_id": "id " * 330}
        binding = {"path": "path " * 200, "sha256": "a" * 64}
        with patch.object(execution_focus, "MAX_FOCUS_WORDS", 500):
            focus = execution_focus.build_execution_focus(self.model, task, binding,
                view["execution_readiness"], view["next_action_advice"])
        self.assertLessEqual(structured_word_count(focus), 500)
        self.assertLessEqual(canonical_utf8_size(focus), execution_focus.MAX_FOCUS_BYTES)
        self.assertEqual(focus["model_sha256"], binding["sha256"])
        self.assertEqual(focus["state"], "reference-required")
        self.assertIsNone(focus["next_action"])

    def test_public_cli_reports_focus_and_stale_readiness_in_text_and_json(self):
        self.add_probe("next-proof")
        self.selected()
        command = [sys.executable, "-B", str(ROOT / "tools/report_adapter_health.py"),
                   "--target", str(self.target), "--current-task", "fixture-task"]
        good = subprocess.run([*command, "--json"], capture_output=True, text=True)
        focus = json.loads(good.stdout)["current_task"]["execution_focus"]
        self.assertEqual(focus["next_action"]["obligation_id"], "next-proof")
        (self.target / "design.md").write_bytes(b"changed accepted rule\n")
        stale = subprocess.run(command, capture_output=True, text=True)
        self.assertIn("Execution focus: blocked-by-stale-evidence", stale.stdout)
        self.assertNotIn("Declared ready obligations: next-proof", stale.stdout)

    def test_projection_boundaries_fall_back_to_references_without_truncation(self):
        import execution_focus
        self.add_probe("next-proof")
        view = self.selected()
        focus = view["execution_focus"]
        size, words = canonical_utf8_size(focus), structured_word_count(focus)
        for metric, limit in (("MAX_FOCUS_BYTES", size), ("MAX_FOCUS_WORDS", words)):
            with self.subTest(metric=metric, below=True), patch.object(execution_focus, metric, limit + 1):
                self.assertEqual(self.selected()["execution_focus"], focus)
            with self.subTest(metric=metric), patch.object(execution_focus, metric, limit):
                self.assertEqual(self.selected()["execution_focus"], focus)
            with self.subTest(metric=metric, exceeded=True), patch.object(execution_focus, metric, limit - 1):
                bounded = self.selected()["execution_focus"]
                self.assertEqual(bounded["state"], "reference-required")
                self.assertIsNone(bounded["next_action"])
                self.assertEqual(bounded["model"], focus["model"])
                self.assertEqual(bounded["unresolved_required_count"], len(focus["unresolved_required_ids"]))

    def test_focus_derivation_has_no_file_io_and_snapshot_failure_removes_it(self):
        import execution_focus
        self.add_probe("next-proof")
        view = self.selected()
        with patch("pathlib.Path.read_bytes", side_effect=AssertionError("focus must not read files")), \
             patch("pathlib.Path.read_text", side_effect=AssertionError("focus must not read files")):
            focus = execution_focus.build_execution_focus(self.model, self.task, view["model"],
                view["execution_readiness"], view["next_action_advice"])
        self.assertEqual(focus, view["execution_focus"])
        checked = changed_index_validator(self.target)
        with patch.object(checked.context, "finalize", return_value=["changed"]):
            invalid = current_task_view(checked, "fixture-task")
        self.assertNotIn("execution_focus", invalid)

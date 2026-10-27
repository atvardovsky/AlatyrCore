from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from analysis_evidence import (MAX_ARTIFACT_BYTES, next_action_advice, probe_binding,
                               revision_failures, verify_artifacts)
from analysis_strategy_contract import load_json_object, validate_problem_model
from publish_active_task import prepare
from support_write_transaction import SupportTransaction
from tests.active_task_fixture import ActiveTaskFixture


def add_evidence(model, target):
    artifact = target / ".ai/.runtime/probe-result.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"The discriminating negative and positive cases passed.\n")
    path = artifact.relative_to(target).as_posix()
    model["unknowns"] = [{"id": "uncertainty", "statement": "Does the selected explanation survive its counterexample?"}]
    model["hypotheses"] = [{"id": "explanation", "statement": "The boundary preserves identity", "status": "supported", "evidence_refs": [path]}]
    model["counterexamples"] = [{"id": "negative-case", "statement": "A distinct identity must not collide", "evidence_refs": [path]}]
    model["proof_obligations"][0]["evidence_refs"] = [path]
    probe = {"obligation_id": "proof-1", "unknown_ids": ["uncertainty"],
             "action_kind": "local-check",
             "method": "Run the smallest identity collision regression and its positive control",
             "input_paths": ["design.md"], "predictions": [{"hypothesis_id": "explanation",
                "supports": "Distinct identities remain distinct", "refutes": "Distinct identities collide"}],
             "estimated_tool_calls": 1, "result": None}
    artifact_binding = {"path": path, "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}
    probe["result"] = {"probe_sha256": probe_binding(model, probe),
                       "input_sha256": {"design.md": hashlib.sha256((target / "design.md").read_bytes()).hexdigest()},
                       "artifacts": [artifact_binding], "outcomes": [{"hypothesis_id": "explanation", "verdict": "supports"}],
                       "summary": "Both identity cases retain the required distinction"}
    model["analysis_evidence"] = {"schema_version": 1, "probes": [probe], "updates": [],
        "review_challenges": [{"id": "identity-challenge", "original_source_ref": "request:identity-regression",
            "normative_source_ref": "design.md", "counterexample_ids": ["negative-case"],
            "proof_obligation_ids": ["proof-1"], "artifacts": [artifact_binding],
            "status": "passed", "reviewer_kind": "primary-separate-pass"}]}
    return path


class AnalysisEvidenceIntegrationTests(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        self.artifact = add_evidence(self.model, self.target)
        self.write_model()
        self.write_index()
        self.schema = load_json_object(ROOT / "schemas/alatyr-problem-model.schema.json")

    def failures(self, model):
        return validate_problem_model(model, self.schema)

    def test_positive_record_passes_registered_target_validation(self):
        self.assertEqual(self.failures(self.model), [])
        self.assertEqual(self.errors(self.check()), set())

    def test_stale_input_or_result_fails_registered_validation(self):
        for path in ("design.md", self.artifact):
            target = self.target / path
            old = target.read_bytes()
            target.write_bytes(old + b"changed\n")
            with self.subTest(path=path):
                self.assertIn("ANALYSIS_EVIDENCE_ARTIFACT", self.errors(self.check()))
            target.write_bytes(old)
        self.assertEqual(self.errors(self.check()), set())

    def test_frozen_history_does_not_bypass_current_task_artifact_validation(self):
        self.close()
        self.assertEqual(self.errors(self.check()), set())
        (self.target / self.artifact).write_bytes(b"changed result after closure\n")
        self.assertIn("ANALYSIS_EVIDENCE_ARTIFACT", self.errors(self.check()))
        self.assertEqual(self.errors(self.check(selected=False)), set())

    def test_unrun_inconclusive_and_conflicting_observations_do_not_establish_cause(self):
        for mutation in ("unrun", "inconclusive", "binding", "unknown-hypothesis", "missing-input"):
            model = copy.deepcopy(self.model)
            probe = model["analysis_evidence"]["probes"][0]
            if mutation == "unrun":
                probe["result"] = None
            elif mutation == "inconclusive":
                probe["result"]["outcomes"][0]["verdict"] = "inconclusive"
            elif mutation == "binding":
                model["task_binding"]["task_ids"] = ["another-task"]
            elif mutation == "unknown-hypothesis":
                probe["result"]["outcomes"][0]["hypothesis_id"] = "missing"
            else:
                probe["result"]["input_sha256"] = {}
            with self.subTest(mutation=mutation):
                self.assertTrue(self.failures(model))
        model = copy.deepcopy(self.model)
        model["primary_strategy_id"] = "hypothesis-driven"
        model.pop("analysis_evidence")
        self.assertTrue(self.failures(model))

    def test_malformed_json_fields_produce_findings_without_exceptions(self):
        for value in ({}, [], None, True, 3, "unknown"):
            for field in ("verdict", "estimated_tool_calls", "status", "input_paths"):
                model = copy.deepcopy(self.model)
                probe = model["analysis_evidence"]["probes"][0]
                if field == "verdict":
                    probe["result"]["outcomes"][0][field] = value
                elif field == "status":
                    model["analysis_evidence"]["review_challenges"][0][field] = value
                else:
                    probe[field] = value
                if field == "estimated_tool_calls" and (value is None or type(value) is int):
                    continue
                with self.subTest(field=field, value=value):
                    self.assertTrue(self.failures(model))

    def test_registered_handler_reports_malformed_result_instead_of_crashing(self):
        self.model["analysis_evidence"]["probes"][0]["result"]["outcomes"][0]["verdict"] = {}
        self.write_model(); self.write_index()
        self.assertIn("ANALYSIS_PROBLEM_MODEL_INVALID", self.errors(self.check()))

    def test_pending_revision_retains_duties_without_changing_strategy(self):
        model = copy.deepcopy(self.model)
        model["hypotheses"][0].update(status="pending", evidence_refs=[])
        model["proof_obligations"][0].update(status="open", evidence_refs=[])
        model["review_results"][0].update(status="pending", evidence_refs=[])
        model["analysis_evidence"]["review_challenges"][0]["status"] = "pending"
        update = {"id": "new-observation", "reason": "The new observation reopens the explanation",
                  "evidence_refs": [self.artifact], "hypothesis_ids": ["explanation"],
                  "invalidated_assumption_ids": [], "reopened_obligation_ids": ["proof-1"],
                  "state": "pending", "resolution_evidence_refs": []}
        update["artifacts"] = []
        model["analysis_evidence"]["updates"] = [update]
        self.assertEqual(self.failures(model), [])
        self.assertEqual(revision_failures(self.model, model), [])
        from analysis_evidence import evidence_failures, active_evidence
        self.assertTrue(evidence_failures(model, completion=True))
        self.assertEqual(active_evidence(model)["pending_updates"], [update])
        self.assertTrue(revision_failures(model, self.model))
        self.assertEqual(model["strategy_transitions"], [])

    def test_resolution_references_and_captured_duties_cannot_disappear(self):
        model = copy.deepcopy(self.model)
        update = {"id": "revision", "reason": "Recheck observation", "evidence_refs": [self.artifact],
                  "hypothesis_ids": ["explanation"], "invalidated_assumption_ids": [],
                  "reopened_obligation_ids": ["proof-1"], "state": "resolved",
                  "resolution_evidence_refs": ["missing.json"], "artifacts": []}
        model["analysis_evidence"]["updates"] = [update]
        self.assertTrue(any("unbound resolution" in row for row in self.failures(model)))
        path = self.target / ".ai/.runtime/resolution.txt"
        path.write_bytes(b"A new discriminating check resolved the revision\n")
        relative = path.relative_to(self.target).as_posix()
        update["artifacts"] = [{"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}]
        update["resolution_evidence_refs"] = [relative]
        self.assertEqual(self.failures(model), [])
        self.model = model
        self.write_model(); self.write_index()
        path.write_bytes(b"changed after conclusion")
        self.assertIn("ANALYSIS_EVIDENCE_ARTIFACT", self.errors(self.check()))
        for collection, key in (("updates", "reopened_obligation_ids"), ("review_challenges", "counterexample_ids")):
            for mutation in ("delete", "rewrite"):
                current = copy.deepcopy(model)
                if mutation == "delete":
                    current["analysis_evidence"][collection] = []
                else:
                    current["analysis_evidence"][collection][0][key] = []
                with self.subTest(collection=collection, mutation=mutation):
                    self.assertTrue(revision_failures(model, current))

    def test_probe_question_and_result_revisions_are_not_silent(self):
        for mutation in ("delete", "question", "result"):
            changed = copy.deepcopy(self.model)
            probe = changed["analysis_evidence"]["probes"][0]
            if mutation == "delete":
                changed["analysis_evidence"]["probes"] = []
            elif mutation == "question":
                probe["method"] = "An unrelated question"
            else:
                probe["result"]["summary"] = "New observed outcome"
            with self.subTest(mutation=mutation):
                self.assertTrue(revision_failures(self.model, changed))

    def test_relabeling_referenced_claims_invalidates_the_observation_binding(self):
        for collection in ("hypotheses", "unknowns", "proof_obligations"):
            changed = copy.deepcopy(self.model)
            changed[collection][0]["statement"] = "A different claim requiring another observation"
            with self.subTest(collection=collection):
                self.assertTrue(any("task/question binding" in row for row in self.failures(changed)))

    def test_inconclusive_completed_probe_does_not_complete_hypothesis_analysis(self):
        from analysis_evidence import evidence_failures
        model = copy.deepcopy(self.model)
        model["primary_strategy_id"] = "hypothesis-driven"
        model["hypotheses"][0].update(status="pending", evidence_refs=[])
        probe = model["analysis_evidence"]["probes"][0]
        probe["result"]["outcomes"][0]["verdict"] = "inconclusive"
        self.assertEqual(evidence_failures(model), [])
        self.assertTrue(any("evidence-supported explanation" in item for item in evidence_failures(model, completion=True)))

    def test_advice_is_digest_bound_and_preserves_unknown_cost_and_required_duties(self):
        model = copy.deepcopy(self.model)
        model["proof_obligations"][0]["status"] = "open"
        model["analysis_evidence"]["probes"][0]["estimated_tool_calls"] = None
        model["execution_dependencies"] = [{"obligation_id": "proof-1", "requires": []}]
        advice = next_action_advice(model, "a" * 64)
        self.assertFalse(advice["authorization_granted"])
        self.assertEqual(advice["model_sha256"], "a" * 64)
        self.assertEqual(advice["unresolved_required"], ["proof-1"])
        self.assertIsNone(advice["candidates"][0]["estimated_tool_calls"])
        self.assertTrue(advice["candidates"][0]["dependency_ready"])
        model.pop("execution_dependencies")
        self.assertFalse(next_action_advice(model, "b" * 64)["candidates"][0]["dependency_ready"])

    def test_selected_task_view_blocks_advice_when_input_changes(self):
        from current_task_view import current_task_view
        from check_change_packages import changed_index_validator
        view = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(view["next_action_advice"]["artifact_binding_state"], "current-content-not-execution-proof")
        (self.target / "design.md").write_bytes(b"new rule\n")
        view = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(view["next_action_advice"]["state"], "blocked-by-stale-evidence")
        self.assertFalse(view["next_action_advice"]["authorization_granted"])

    def test_artifact_byte_boundary_is_enforced(self):
        model = copy.deepcopy(self.model)
        raw = b"x" * MAX_ARTIFACT_BYTES
        for row in model["analysis_evidence"]["probes"][0]["result"]["artifacts"]:
            row["sha256"] = hashlib.sha256(raw).hexdigest()
        model["analysis_evidence"]["probes"][0]["result"]["input_sha256"]["design.md"] = hashlib.sha256(raw).hexdigest()
        model["analysis_evidence"]["review_challenges"][0]["artifacts"][0]["sha256"] = hashlib.sha256(raw).hexdigest()
        for size in (MAX_ARTIFACT_BYTES - 1, MAX_ARTIFACT_BYTES, MAX_ARTIFACT_BYTES + 1):
            data = b"x" * size
            failures = verify_artifacts(model, lambda path, limit: data)
            with self.subTest(size=size):
                self.assertEqual(any("byte budget" in item for item in failures), size > MAX_ARTIFACT_BYTES)

    def test_publication_verifies_artifacts_and_binds_them_to_the_transaction(self):
        draft = self.target / ".ai/.runtime/draft.json"
        draft.write_text(json.dumps(self.model), encoding="utf-8")
        relative = draft.relative_to(self.target).as_posix()
        plan = prepare(self.target, "fixture-task", relative)
        self.assertIn(self.target / self.artifact, plan.inputs)
        old_model = self.model_path.read_bytes()
        (self.target / self.artifact).write_bytes(b"concurrent observation\n")
        with self.assertRaisesRegex(ValueError, "changed while planning"):
            SupportTransaction(self.target).apply(plan.outputs, expected_inputs=plan.inputs)
        self.assertEqual(self.model_path.read_bytes(), old_model)
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/publish_active_task.py"),
            "--target", str(self.target), "--task-id", "fixture-task", "--draft", relative], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("artifact digest changed", result.stderr)


if __name__ == "__main__":
    unittest.main()

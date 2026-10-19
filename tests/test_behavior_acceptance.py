from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from analysis_strategy_contract import validate_problem_model
from behavior_acceptance import behavior_failures
from check_analysis_strategies import sample_model


def behavior_model():
    model = sample_model("invariant-first")
    model["risk_classes"] = ["business-rule"]
    model["behavior_review"] = {"required": True, "reason": "An accepted assignment rule changes", "deltas": [{
        "fact_id": "change-1", "before": "One approved assignment is accepted", "after": "Restore the same accepted assignment",
        "effect": "restore", "authority_status": "approved", "authority_kind": "canonical-source",
        "authority_ref": "design/assignment.md#single-assignment", "decision_owner": "domain-owner",
        "scope": "One assignment; no new partial-day restriction", "evidence_refs": ["decision:accepted-assignment"]
    }]}
    return model


def original_case():
    return {"source_ref": "issue:assignment", "actor": "scheduler", "input": "One eligible person with a time note",
            "expected_outcome": "The accepted person is assigned", "status": "unverified", "evidence_refs": [], "supersession": None}


class BehaviorAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads((ROOT / "schemas/alatyr-problem-model.schema.json").read_text())

    def test_restoration_uses_existing_authority_without_new_approval(self):
        self.assertEqual(validate_problem_model(behavior_model(), self.schema), [])
        self.assertEqual(behavior_failures(behavior_model(), completion=True), [])

    def test_versions_reject_float_equivalents(self):
        for field in ("model", "projection"):
            model = behavior_model()
            if field == "model":
                model["schema_version"] = 5.0
            else:
                model["active_projection"]["schema_version"] = 4.0
            self.assertTrue(validate_problem_model(model, self.schema))

    def test_declared_inference_cannot_become_approved_by_tests_or_a_plan(self):
        for kind in ("inference", "test", "implementation", "plan"):
            model = behavior_model()
            model["behavior_review"]["deltas"][0].update(authority_kind=kind, evidence_refs=["tests/reject-partial.test"])
            with self.subTest(kind=kind):
                self.assertTrue(validate_problem_model(model, self.schema))

    def test_missing_hidden_duplicate_and_unresolved_rule_authority(self):
        for mutate in (
            lambda review: review.update(required=False),
            lambda review: review.update(deltas=[]),
            lambda review: review["deltas"].append(copy.deepcopy(review["deltas"][0])),
            lambda review: review["deltas"][0].update(authority_ref="unknown"),
            lambda review: review["deltas"][0].update(fact_id="unrelated-fact"),
        ):
            model = behavior_model()
            mutate(model["behavior_review"])
            self.assertTrue(validate_problem_model(model, self.schema))
        model = behavior_model()
        model["behavior_review"]["deltas"][0]["authority_status"] = "proposed"
        self.assertEqual(validate_problem_model(model, self.schema), [])
        self.assertTrue(behavior_failures(model, completion=True))

    def test_green_tests_do_not_close_original_unverified_or_failing_case(self):
        for status in ("unverified", "still-failing"):
            model = behavior_model()
            model["original_case"] = dict(original_case(), status=status)
            self.assertTrue(behavior_failures(model, completion=True))
        model["original_case"].update(status="verified-fixed", evidence_refs=["actual:original-input-result"])
        self.assertEqual(behavior_failures(model, completion=True), [])

    def test_owner_supersession_is_explicit_and_not_a_fabricated_fix(self):
        model = behavior_model()
        model["original_case"] = dict(original_case(), status="superseded-by-owner-decision", evidence_refs=["decision:replacement"])
        self.assertTrue(behavior_failures(model, completion=True))
        model["original_case"]["supersession"] = {"source_ref": "decision:replacement", "decision_owner": "domain-owner", "reason": "Owner accepted a different expected outcome"}
        self.assertEqual(behavior_failures(model, completion=True), [])
        model["original_case"]["status"] = "verified-fixed"
        self.assertTrue(behavior_failures(model, completion=True))

    def test_malformed_json_fields_return_findings_without_exceptions(self):
        for path in (("behavior_review",), ("original_case",), ("behavior_review", "deltas"), ("behavior_review", "deltas", 0, "authority_status"), ("behavior_review", "deltas", 0, "authority_kind")):
            for value in (None, {}, [], True, 7, "wrong"):
                model = behavior_model()
                cursor = model
                for part in path[:-1]:
                    cursor = cursor[part]
                cursor[path[-1]] = value
                with self.subTest(path=path, value=value):
                    self.assertIsInstance(validate_problem_model(model, self.schema), list)


if __name__ == "__main__":
    unittest.main()

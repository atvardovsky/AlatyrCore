from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from task_readiness import execution_readiness
from current_task_view import current_task_view
from check_change_packages import changed_index_validator
from analysis_strategy_contract import validate_problem_model
from target_adapter_validation.analysis_strategies import load_problem_model_schema
from tests.active_task_fixture import ActiveTaskFixture


def model():
    return {"proof_obligations": [{"id": key, "status": status} for key, status in (("a", "passed"), ("b", "open"), ("c", "blocked"), ("d", "open"))],
            "execution_dependencies": [{"obligation_id": key, "requires": deps} for key, deps in (("a", []), ("b", ["a"]), ("c", []), ("d", ["c"]))]}


class ReadinessTests(unittest.TestCase):
    def test_installed_delegate_forwards_exact_selector_without_changing_operation(self):
        path = ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"
        spec = importlib.util.spec_from_file_location("field_health_delegate", path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        for operation in ("status", "doctor"):
            args = module.build_parser().parse_args([operation, "--target", ".", "--current-task", "fixture-task"])
            argv = module.canonical_arguments(args, Path("target"), Path("source"))
            self.assertEqual(argv[0], operation)
            self.assertEqual(argv[-2:], ["--current-task", "fixture-task"])

    def test_absent_is_compatible_and_ready_does_not_mean_permission_or_proof(self):
        self.assertEqual(execution_readiness({})["state"], "not-configured")
        value = execution_readiness(model())
        self.assertEqual(value["ready"], ["b"])
        self.assertEqual(value["blocked"], ["c"])
        self.assertEqual(value["waiting"], [{"obligation_id": "d", "requires": ["c"]}])
        self.assertEqual(value["retained_unresolved"], ["b", "c", "d"])
        self.assertEqual(value["authority"], "none")
        self.assertFalse(value["evidence_verified"])

    def test_cycles_missing_duplicate_and_unfinished_dependencies_are_rejected(self):
        mutations = [lambda x: x["execution_dependencies"][0]["requires"].append("a"),
                     lambda x: x["execution_dependencies"][0]["requires"].append("b"),
                     lambda x: x["execution_dependencies"][3]["requires"].append("missing"),
                     lambda x: x["execution_dependencies"].pop(),
                     lambda x: x["execution_dependencies"].append(x["execution_dependencies"][0]),
                     lambda x: x["execution_dependencies"][1]["requires"].append("a"),
                     lambda x: x["execution_dependencies"][0]["requires"].append("c")]
        for mutate in mutations:
            value = model(); mutate(value)
            self.assertEqual(execution_readiness(value)["state"], "invalid")
            self.assertEqual(execution_readiness(value)["ready"], [])

    def test_malformed_json_fields_never_crash_or_become_unconfigured(self):
        from tests.test_test_execution_contract import nested_paths, set_path
        for path in nested_paths(model()):
            for bad in (None, True, 3, "unknown", [], {}, [{}]):
                value = model(); set_path(value, path, bad)
                result = execution_readiness(value)
                self.assertIsInstance(result, dict)
                if result["failures"]:
                    self.assertEqual(result["ready"], [])
        for bad in (None, True, 1, "", {}, []):
            self.assertEqual(execution_readiness({"execution_dependencies": bad})["state"], "invalid")

    def test_bounded_chain_below_at_above_limit(self):
        for count in (63, 64, 65):
            value = {"proof_obligations": [{"id": str(i), "status": "open"} for i in range(count)],
                     "execution_dependencies": [{"obligation_id": str(i), "requires": [str(i-1)] if i else []} for i in range(count)]}
            result = execution_readiness(value)
            self.assertEqual(bool(result["failures"]), count > 64)
            if count <= 64:
                self.assertEqual(result["ready"], ["0"])
                self.assertEqual(len(result["retained_unresolved"]), count)


class CurrentTaskTests(ActiveTaskFixture):
    def test_selected_current_disposition_uses_bound_model_without_historical_scan(self):
        checked = changed_index_validator(self.target)
        value = current_task_view(checked, "fixture-task")
        self.assertEqual(value["state"], "bound-recorded-disposition", value)
        self.assertFalse(value["acceptance_granted"])
        self.assertFalse(value["historical_narratives_loaded"])
        self.assertEqual(value["repair_evidence"]["state"], "not-verified")
        self.assertNotIn("execution_readiness", value)

    def test_stale_missing_duplicate_and_unsafe_models_fail_closed(self):
        for mutation in ("digest", "missing", "outside", "duplicate", "operation"):
            with self.subTest(mutation=mutation):
                original = copy.deepcopy(self.task)
                if mutation == "digest": self.task["problem_model"]["sha256"] = "0" * 64
                if mutation == "missing": self.task["problem_model"]["path"] = "missing.json"
                if mutation == "outside": self.task["problem_model"]["path"] = "../outside.json"
                if mutation == "operation": self.task["operation_id"] = "different-operation"
                self.write_index([self.task, self.task] if mutation == "duplicate" else None)
                self.assertEqual(current_task_view(changed_index_validator(self.target), "fixture-task")["state"], "unknown")
                self.task = original
        self.write_index()
        self.assertEqual(current_task_view(changed_index_validator(self.target), "not-registered")["state"], "unknown")

    def test_model_schema_and_projection_share_dependency_contract(self):
        self.model["execution_dependencies"] = [{"obligation_id": row["id"], "requires": []} for row in self.model["proof_obligations"]]
        self.assertEqual(validate_problem_model(self.model, load_problem_model_schema()), [])
        self.write_model(); self.write_index()
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["execution_readiness"]["state"], "declared-readiness")
        self.assertEqual(self.errors(self.check()), set())
        self.model["execution_dependencies"][0]["requires"] = [self.model["proof_obligations"][0]["id"]]
        self.assertTrue(validate_problem_model(self.model, load_problem_model_schema()))

    def test_health_cli_exposes_selection_failure_instead_of_ignoring_selector(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/report_adapter_health.py"), "--target", str(self.target), "--current-task", "missing", "--json"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        value = json.loads(result.stdout)
        self.assertEqual(value["current_task"]["state"], "unknown")
        self.assertTrue(value["current_task"]["diagnostics"])

    def test_closed_disposition_remains_historical_not_runtime_acceptance(self):
        self.close()
        self.closure["delivery"]["evidence_finalization"] = "provisional"
        self.write_closure()
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["state"], "bound-recorded-disposition", value)
        self.assertEqual(value["delivery"]["evidence_finalization"], "provisional")
        self.assertEqual(value["disposition_kind"], "recorded-closure-not-current-runtime")
        self.assertFalse(value["acceptance_granted"])
        self.assertEqual(value["disposition_source"], self.task["completion_evidence"])

    def test_invalid_closure_preservation_cannot_expose_a_healthy_delivery_view(self):
        self.close()
        self.closure["delivery"]["evidence_finalization"] = "provisional"
        self.closure["engineering_evidence"].update(materiality="material", preserved_owners=["design.md"],
            preservation=[{"fact_id": "change-1", "fact_type": "implementation", "owner": "design.md"}])
        self.write_closure()
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["state"], "unknown", value)
        self.assertTrue(value["diagnostics"])
        self.assertNotIn("delivery", value)
        self.assertNotIn("model", value)

    def test_original_failure_stays_visible_despite_green_component_obligations(self):
        from current_task_view import incident_outcome_view
        value = copy.deepcopy(self.model)
        value["original_case"] = {"source_ref": "original-run.json", "expected_outcome": "Original end-to-end flow completes", "status": "still-failing"}
        value["hypotheses"] = [{"id": "component-only-speedup", "status": "rejected"}]
        outcome = incident_outcome_view(value)
        self.assertEqual(outcome["state"], "original-case-unresolved")
        self.assertEqual(outcome["original_case"]["source_ref"], "original-run.json")
        self.assertEqual(outcome["rejected_hypothesis_ids"], ["component-only-speedup"])
        self.assertFalse(outcome["evidence_verified"])
        self.assertEqual(outcome["authority"], "none")

    def test_bound_original_outcome_is_available_through_public_health_cli(self):
        self.model["original_case"] = {"source_ref": "original-run.json", "actor": "end user",
            "input": "Original workflow request", "expected_outcome": "Original end-to-end flow completes",
            "status": "still-failing", "evidence_refs": [], "supersession": None}
        self.write_model(); self.write_index()
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["state"], "bound-recorded-disposition", value)
        self.assertEqual(value["incident_outcome"]["state"], "original-case-unresolved")
        command = [sys.executable, "-B", str(ROOT / "tools/report_adapter_health.py"),
                   "--target", str(self.target), "--current-task", "fixture-task", "--json"]
        result = subprocess.run(command, capture_output=True, text=True)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["current_task"]["incident_outcome"]["state"], "original-case-unresolved")
        self.assertFalse(payload["current_task"]["acceptance_granted"])
        from report_adapter_health import render_text
        for mode in ("status", "doctor"):
            text = render_text(payload, mode=mode)
            self.assertIn("Original incident outcome: original-case-unresolved", text)
            self.assertIn("Original end-to-end flow completes", text)

    def test_snapshot_failure_removes_every_derived_evidence_claim(self):
        self.close()
        checked = changed_index_validator(self.target)
        checked.repair_review_observations = {"fixture-task": {"state": "record-consistent", "claim": "incident-fixed"}}
        with patch.object(checked.context, "finalize", return_value=["changed"]):
            value = current_task_view(checked, "fixture-task")
        self.assertEqual(value["state"], "unknown")
        self.assertEqual(value["repair_evidence"]["state"], "not-verified")
        for key in ("delivery", "model", "disposition_source", "execution_readiness", "incident_controls", "task_state", "incident_outcome"):
            self.assertNotIn(key, value)

    def test_default_health_does_not_load_selected_task_view(self):
        from report_adapter_health import health_payload
        with patch("current_task_view.current_task_view", side_effect=AssertionError("default health expanded selected task")):
            value = health_payload(target=self.target)
        self.assertNotIn("current_task", value)

    def test_control_adoption_is_not_inferred_from_template_presence(self):
        from tests.test_test_execution_contract import RegisteredTestingExecutionTests
        helper = RegisteredTestingExecutionTests()
        policy, _ = helper.fixture(self.target)
        helper.write(self.target, ".ai/project/testing/test-first-policy.json", policy)
        helper.write(self.target, ".ai/assistant/templates/repair-qualification.json", {})
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["incident_controls"]["adoption"], "not-adopted")
        self.assertTrue(value["incident_controls"]["installed_templates"]["2"])
        self.assertEqual(value["incident_controls"]["exercised"], "not-verified")
        self.assertFalse(value["incident_controls"]["automatic_enablement"])
        for bad in (None, True, 1, "enabled", [], {}):
            policy["repair_review"] = bad
            helper.write(self.target, ".ai/project/testing/test-first-policy.json", policy)
            value = current_task_view(changed_index_validator(self.target), "fixture-task")
            self.assertEqual(value["incident_controls"]["adoption"], "unknown")


if __name__ == "__main__":
    unittest.main()

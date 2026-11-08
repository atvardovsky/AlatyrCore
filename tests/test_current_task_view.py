from __future__ import annotations

import copy
import hashlib
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
    def add_predecessor(self):
        from tests.test_behavior_acceptance import original_case
        from target_adapter_validation.harness_scenarios.analysis_strategies import _write_model
        prior = copy.deepcopy(self.model)
        prior.update(model_id="prior-model", operation_id="prior-operation", original_case=original_case())
        prior["task_binding"]["task_ids"] = ["prior-task"]
        prior["active_projection"]["path"] = ".ai/.runtime/problem-model-projections/prior-model.json"
        prior["incident"].update(mode="new", family_id="incident-family", trigger="reported-defect",
                                 corrective_iteration=0, predecessor_model_ids=[])
        path = self.target / ".ai/.runtime/problem-models/prior-model.json"
        _write_model(self.target, path, prior)
        header = copy.deepcopy(self.task)
        header.update(task_id="prior-task", operation_id="prior-operation", problem_model=self.bind(path),
                      incident_family_id="incident-family", predecessor_task_ids=[])
        self.model["original_case"] = original_case()
        self.model["incident"].update(mode="continuation", family_id="incident-family",
            trigger="reported-defect", corrective_iteration=1, predecessor_model_ids=["prior-model"])
        self.task.update(incident_family_id="incident-family", predecessor_task_ids=["prior-task"])
        self.write_model(); self.write_index([self.task, header])
        return prior, header, path

    def test_valid_predecessor_is_bound_in_lifecycle_and_unrelated_models_are_not_loaded(self):
        from lifecycle_checkpoints import selected_task
        _, header, path = self.add_predecessor()
        unrelated = copy.deepcopy(header)
        unrelated.update(task_id="unrelated-task", operation_id="unrelated-operation", incident_family_id="none")
        irrelevant = self.target / ".ai/.runtime/problem-models/unrelated.json"
        irrelevant.write_text("malformed history")
        unrelated["problem_model"] = self.bind(irrelevant)
        self.write_index([self.task, header, unrelated])
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["state"], "bound-recorded-disposition", value)
        checkpoint = selected_task(self.target, "fixture-task")
        self.assertIn(path.relative_to(self.target).as_posix(), checkpoint["checkpoint_inputs"])
        self.assertFalse(any("unrelated.json" in key for key in checkpoint["checkpoint_inputs"]))

    def test_predecessor_mutation_during_lookup_clears_selected_view(self):
        from target_adapter_validation.active_tasks import lineage_model
        _, _, path = self.add_predecessor()
        def changing(validator, header):
            model = lineage_model(validator, header)
            path.write_bytes(path.read_bytes() + b" ")
            return model
        with patch("target_adapter_validation.active_tasks.lineage_model", side_effect=changing):
            value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["state"], "unknown", value)
        self.assertFalse(value["acceptance_granted"])

    def test_active_predecessor_runtime_conflict_invalidates_durable_handoff_view(self):
        from lifecycle_checkpoints import selected_task
        prior, header, path = self.add_predecessor()
        directory = self.target / ".ai/assistant/task-evidence/prior-task"
        directory.mkdir(parents=True)
        retained = directory / "model.json"
        projection = directory / "projection.json"
        retained.write_bytes(path.read_bytes())
        projection.write_bytes((self.target / prior["active_projection"]["path"]).read_bytes())
        header["analysis_handoff"] = {"model": self.bind(retained), "projection": self.bind(projection),
                                      "retention_review": "fixture:reviewed"}
        self.write_index([self.task, header])
        self.assertEqual(current_task_view(changed_index_validator(self.target), "fixture-task")["state"], "bound-recorded-disposition")
        path.write_bytes(path.read_bytes() + b" ")
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["state"], "unknown", value)
        with self.assertRaises(ValueError): selected_task(self.target, "fixture-task")

    def test_selected_view_checks_transitive_predecessor_model_edges(self):
        from lifecycle_checkpoints import selected_task
        from target_adapter_validation.harness_scenarios.analysis_strategies import _write_model
        prior, header, path = self.add_predecessor()
        prior["incident"]["predecessor_model_ids"] = ["unrepresented-grandparent"]
        _write_model(self.target, path, prior)
        header["problem_model"] = self.bind(path)
        self.write_model(); self.write_index([self.task, header])
        self.assertIn("ACTIVE_TASK_PREDECESSOR", self.errors(self.check()))
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["state"], "unknown", value)
        self.assertTrue(any("prior-task" in message for message in value["diagnostics"]))
        with self.assertRaises(ValueError): selected_task(self.target, "fixture-task")

    def test_malformed_selected_or_predecessor_models_fail_all_routes_without_crashing(self):
        from lifecycle_checkpoints import selected_task
        for malformed in (None, [None], [{}]):
            for selected in (True, False):
                with self.subTest(value=malformed, selected=selected):
                    prior, header, path = self.add_predecessor()
                    if selected:
                        value = copy.deepcopy(self.model)
                        value["proof_obligations"] = malformed
                        self.model_path.write_text(json.dumps(value))
                        self.task["problem_model"] = self.bind(self.model_path)
                    else:
                        prior["proof_obligations"] = malformed
                        path.write_text(json.dumps(prior))
                        header["problem_model"] = self.bind(path)
                    self.write_index([self.task, header])
                    value = current_task_view(changed_index_validator(self.target), "fixture-task")
                    self.assertEqual(value["state"], "unknown", value)
                    self.assertTrue(self.errors(self.check()))
                    with self.assertRaises(ValueError): selected_task(self.target, "fixture-task")

    def test_schema_invalid_selected_task_ids_are_diagnostics_not_exceptions(self):
        from lifecycle_checkpoints import selected_task
        for malformed in (None, True, 3, {}, "fixture-task"):
            with self.subTest(value=malformed):
                self.model["task_binding"]["task_ids"] = malformed
                self.write_model(); self.write_index()
                value = current_task_view(changed_index_validator(self.target), "fixture-task")
                self.assertEqual(value["state"], "unknown", value)
                self.assertTrue(value["diagnostics"])
                with self.assertRaises(ValueError): selected_task(self.target, "fixture-task")

    def test_schema_invalid_predecessor_task_ids_are_diagnostics_not_exceptions(self):
        from lifecycle_checkpoints import selected_task
        prior, header, path = self.add_predecessor()
        prior["task_binding"]["task_ids"] = None
        path.write_text(json.dumps(prior))
        header["problem_model"] = self.bind(path)
        self.write_index([self.task, header])
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["state"], "unknown", value)
        with self.assertRaises(ValueError): selected_task(self.target, "fixture-task")

    def test_closed_predecessor_requires_durable_witness_and_never_requires_runtime_files(self):
        from lifecycle_checkpoints import selected_task
        from target_adapter_validation.harness_scenarios.analysis_strategies import _write_model
        prior, header, path = self.add_predecessor()
        prior["original_case"].update(status="verified-fixed", evidence_refs=["fixture:accepted-original-case"])
        _write_model(self.target, path, prior)
        header["problem_model"] = self.bind(path)
        selected = copy.deepcopy(self.task)
        self.close()
        closure = copy.deepcopy(self.closure)
        self.task = selected
        directory = self.target / ".ai/assistant/task-evidence/prior-task"
        directory.mkdir(parents=True)
        retained = directory / "model.json"
        projection = directory / "projection.json"
        retained.write_bytes(path.read_bytes())
        runtime_projection = self.target / prior["active_projection"]["path"]
        projection.write_bytes(runtime_projection.read_bytes())
        closure.update(task_id="prior-task", operation_id="prior-operation", incident_family_id="incident-family",
            predecessor_task_ids=[], analysis_witness={"model": self.bind(retained), "projection": self.bind(projection),
                                                       "retention_review": "fixture:reviewed"})
        closure_path = directory / "closure.json"
        closure_path.write_text(json.dumps(closure))
        header.update(state="closed", completion_evidence=self.bind(closure_path))
        self.write_index([self.task, header])
        path.unlink(); runtime_projection.unlink()
        self.assertEqual(current_task_view(changed_index_validator(self.target), "fixture-task")["state"], "bound-recorded-disposition")
        self.assertEqual(selected_task(self.target, "fixture-task")["task_state"], "active")
        self.assertEqual(self.errors(self.check()), set())
        retained_projection = projection.read_bytes()
        projection.write_text("{}")
        closure["analysis_witness"]["projection"] = self.bind(projection)
        closure_path.write_text(json.dumps(closure))
        header["completion_evidence"] = self.bind(closure_path)
        self.write_index([self.task, header])
        self.assertEqual(current_task_view(changed_index_validator(self.target), "fixture-task")["state"], "unknown")
        with self.assertRaises(ValueError): selected_task(self.target, "fixture-task")
        self.assertIn("ANALYSIS_PROBLEM_MODEL_PROJECTION_INVALID", self.errors(self.check()))
        projection.write_bytes(retained_projection)
        closure["analysis_witness"]["projection"] = self.bind(projection)
        path.write_bytes(retained.read_bytes())
        closure.pop("analysis_witness")
        closure_path.write_text(json.dumps(closure))
        header["completion_evidence"] = self.bind(closure_path)
        self.write_index([self.task, header])
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["state"], "unknown", value)
        self.assertTrue(any("durable" in message for message in value["diagnostics"]))
        with self.assertRaises(ValueError): selected_task(self.target, "fixture-task")

    def test_selected_view_and_lifecycle_reject_unrepresented_model_predecessor(self):
        from lifecycle_checkpoints import selected_task
        from tests.test_behavior_acceptance import original_case
        self.model["original_case"] = original_case()
        self.model["incident"].update(mode="continuation", family_id="incident-family",
            trigger="reported-defect", corrective_iteration=1,
            predecessor_model_ids=["unrepresented-model"])
        self.task["incident_family_id"] = "incident-family"
        self.write_model(); self.write_index()
        self.assertIn("ACTIVE_TASK_PREDECESSOR", self.errors(self.check()))
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["state"], "unknown", value)
        self.assertTrue(any("predecessor" in message for message in value["diagnostics"]))
        with self.assertRaisesRegex(ValueError, "predecessor"):
            selected_task(self.target, "fixture-task")

    def test_selected_checkpoint_binding_invalidates_focus_without_history_scan(self):
        path = ".ai/.runtime/selected-checkpoint.json"
        artifact = self.target / path
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text('{"phase":"diagnose"}\n')
        for review in self.model["review_results"]:
            review["status"] = "pending"
        self.model["original_case"] = {"source_ref": "reported-original-case", "actor": "fixture caller",
            "input": "original input", "expected_outcome": "original flow succeeds",
            "status": "still-failing", "evidence_refs": [], "supersession": None}
        self.model["analysis_evidence"] = {"schema_version": 1, "probes": [],
            "updates": [], "review_challenges": [],
            "selected_context": [{"path": path, "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}]}
        self.write_model(); self.write_index()
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["state"], "bound-recorded-disposition", value)
        self.assertEqual(value["selected_context"]["state"], "current-content-not-execution-proof")
        self.assertFalse(value["selected_context"]["content_loaded_into_view"])
        (self.target / "unrelated-history.md").write_text("unrelated historical content")
        self.assertEqual(current_task_view(changed_index_validator(self.target), "fixture-task")["selected_context"]["state"],
                         "current-content-not-execution-proof")
        artifact.write_text('{"phase":"contradictory-result"}\n')
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["selected_context"]["state"], "stale-or-unavailable")
        self.assertEqual(value["execution_focus"]["state"], "blocked-by-stale-evidence")
        self.assertIsNone(value["execution_focus"]["next_action"])
        self.assertEqual(value["incident_outcome"]["state"], "original-case-unresolved")
        self.assertFalse(value["acceptance_granted"])
        self.assertIn("ANALYSIS_EVIDENCE_ARTIFACT", self.errors(self.check()))

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
        preflight = payload["current_task"]["repair_preflight"]
        self.assertEqual(preflight["original_input"], "Original workflow request")
        self.assertEqual(preflight["expected_outcome"], "Original end-to-end flow completes")
        self.assertFalse(preflight["authorization_granted"])
        self.assertFalse(preflight["unrelated_work_blocked"])
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
        for key in ("delivery", "model", "disposition_source", "execution_readiness", "incident_controls", "task_state", "incident_outcome", "repair_preflight"):
            self.assertNotIn(key, value)

    def test_default_health_does_not_load_selected_task_view(self):
        from report_adapter_health import health_payload
        with patch("current_task_view.current_task_view", side_effect=AssertionError("default health expanded selected task")), patch("report_adapter_health.work_overview", side_effect=AssertionError("default health expanded coordination")):
            value = health_payload(target=self.target)
        self.assertNotIn("current_task", value)
        self.assertNotIn("work_overview", value)

    def test_control_adoption_is_not_inferred_from_template_presence(self):
        from tests.test_test_execution_contract import RegisteredTestingExecutionTests
        helper = RegisteredTestingExecutionTests()
        policy, _ = helper.fixture(self.target)
        helper.write(self.target, ".ai/project/testing/test-first-policy.json", policy)
        helper.write(self.target, ".ai/assistant/templates/repair-qualification.json", {})
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["incident_controls"]["adoption"], "not-adopted")
        self.assertTrue(value["incident_controls"]["installed_templates"]["2"])

    def prepare_incident(self, *, reserved=False):
        from tests.test_behavior_acceptance import original_case
        self.model["incident"].update(mode="new", family_id="fixture-incident", trigger="reported-defect")
        self.model["original_case"] = original_case()
        self.task["incident_family_id"] = "fixture-incident"
        if reserved:
            self.model["proof_obligations"].append(dict(self.model["proof_obligations"][0], id="repair-evidence-review"))
            self.task["repair_review_required"] = True
        self.write_model(); self.write_index()

    def test_core_incident_does_not_require_optional_control_adoption(self):
        self.prepare_incident()
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["incident_controls"]["adoption"], "not-adopted")
        self.assertEqual(value["repair_preflight"]["next_action"], "continue-core-repair-with-generic-obligations")
        self.assertFalse(value["repair_preflight"]["captured_requirement"])

    def test_unreadable_policy_is_not_reported_as_unadopted(self):
        self.prepare_incident()
        path = self.target / ".ai/project/testing/test-first-policy.json"
        path.mkdir(parents=True)
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["incident_controls"]["adoption"], "unknown")
        self.assertEqual(value["repair_preflight"]["next_action"], "resolve-canonical-repair-control-policy")
        self.assertFalse(value["acceptance_granted"])

    def test_captured_requirement_without_policy_has_read_only_owner_recovery_guidance(self):
        self.prepare_incident(reserved=True)
        before = {path: path.read_bytes() for path in (self.model_path, self.target / ".ai/assistant/active-tasks.json")}
        command = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "doctor", "--target", str(self.target),
                   "--current-task", "fixture-task", "--json"]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        preflight = payload["current_task"]["repair_preflight"]
        self.assertEqual(preflight["state"], "captured-requirement-needs-review")
        self.assertEqual(preflight["next_action"], "review-captured-repair-policy-and-history")
        self.assertTrue(preflight["captured_requirement"])
        self.assertFalse(preflight["automatic_rewrite"])
        self.assertFalse(preflight["historical_applicability_verified"])
        self.assertIn("not proof of mistaken capture", preflight["recovery_guidance"])
        self.assertTrue(any(row["code"] == "TDD_EXECUTION_CONTRACT" for row in payload["findings"]))
        from report_adapter_health import render_text
        self.assertIn(preflight["recovery_guidance"], render_text(payload))
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.assertFalse((self.target / ".ai/project/testing/test-first-policy.json").exists())

    def test_captured_requirement_does_not_hide_invalid_or_deferred_policy(self):
        from tests.test_test_execution_contract import policy
        from tests.test_incident_quality import repair_policy
        self.prepare_incident(reserved=True)
        value = policy()
        value["commands"][0]["execution"]["proof_boundary"] = "end-to-end"
        value["repair_review"] = repair_policy()
        path = self.target / ".ai/project/testing/test-first-policy.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        for state in ("enabled", "deferred", "disabled", {}, [], None, True, 1, "invalid"):
            proposed = copy.deepcopy(value)
            proposed["repair_review"]["state"] = state
            if state in ("deferred", "disabled"):
                proposed["repair_review"]["records"] = []
            path.write_text(json.dumps(proposed), encoding="utf-8")
            with self.subTest(state=state):
                result = current_task_view(changed_index_validator(self.target), "fixture-task")
                expected = "review-before-related-repair" if state == "enabled" else "captured-requirement-needs-review"
                self.assertEqual(result["repair_preflight"]["state"], expected)
                self.assertFalse(result["acceptance_granted"])

    def test_retained_header_without_marker_cannot_produce_core_only_guidance(self):
        self.prepare_incident()
        path = self.target / ".ai/assistant/active-tasks.json"
        index = json.loads(path.read_text(encoding="utf-8"))
        index["tasks"][0]["repair_review_required"] = True
        path.write_text(json.dumps(index), encoding="utf-8")
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["state"], "unknown")
        self.assertTrue(value["diagnostics"])
        self.assertNotIn("repair_preflight", value)
        self.assertFalse(value["acceptance_granted"])

    def test_repair_preflight_preserves_explicit_deferred_or_disabled_decisions(self):
        from tests.test_test_execution_contract import RegisteredTestingExecutionTests
        helper = RegisteredTestingExecutionTests()
        policy, _ = helper.fixture(self.target)
        self.model["original_case"] = {"source_ref": "original-run.json", "actor": "end user",
            "input": "Original request", "expected_outcome": "Original flow completes",
            "status": "still-failing", "evidence_refs": [], "supersession": None}
        self.write_model(); self.write_index()
        for state in ("deferred", "disabled"):
            policy["repair_review"] = {"schema_version": 1, "state": state, "acceptance_command_ids": [], "records": []}
            helper.write(self.target, ".ai/project/testing/test-first-policy.json", policy)
            value = current_task_view(changed_index_validator(self.target), "fixture-task")
            self.assertEqual(value["repair_preflight"]["control_adoption"], state)
            self.assertEqual(value["repair_preflight"]["next_action"], "respect-recorded-repair-control-decision")
        self.assertEqual(value["incident_controls"]["exercised"], "not-verified")
        self.assertFalse(value["incident_controls"]["automatic_enablement"])
        for bad in (None, True, 1, "enabled", [], {}):
            policy["repair_review"] = bad
            helper.write(self.target, ".ai/project/testing/test-first-policy.json", policy)
            value = current_task_view(changed_index_validator(self.target), "fixture-task")
            self.assertEqual(value["incident_controls"]["adoption"], "unknown")


if __name__ == "__main__":
    unittest.main()

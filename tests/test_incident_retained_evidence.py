"""Incident and task evidence share exact retained bindings, not authority."""
import copy
import json
from pathlib import Path

from tests.active_task_fixture import ActiveTaskFixture
from check_change_packages import changed_index_validator


class IncidentRetainedEvidenceTests(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        self.close()
        incident = self.model["incident"]
        self.package = {"status": "blocked", "evidence_classification": "historical-record", "incident_continuity": {
            **{key: copy.deepcopy(incident[key]) for key in ("mode", "family_id", "trigger", "corrective_iteration", "latest_failed_gate")},
            "predecessors": [], "problem_model": self.task["problem_model"],
            "lifecycle_model_required": self.model["lifecycle_model"]["required"],
            "retained_evidence": {"task_id": "fixture-task", **self.closure["analysis_witness"]}}}
        self.relative = ".ai/assistant/change-packages/fixture.json"
        self.package["package_id"] = "fixture-package"
        self.package["operation"] = {"id": self.task["operation_id"]}
        path = self.target / self.relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.package))

    def validate(self, *, selected=None):
        checked = changed_index_validator(self.target)
        if selected == "package":
            checked.change_packages = [self.target / self.relative]
        elif selected == "task":
            checked.current_task_id = "fixture-task"
        elif selected == "same-operation":
            checked.current_task_id = "other-task"
        checked.validate_package_incident_continuity(self.package, self.relative,
            status=self.package["status"], indexed_entries=[])
        return checked

    def test_nonselected_package_resolves_exact_archived_pair_without_runtime(self):
        self.model_path.unlink()
        checked = self.validate()
        self.assertEqual(self.errors(checked), set(), checked.findings)
        self.assertIn("PACKAGE_INCIDENT_RETAINED", {x.code for x in checked.findings})
        self.assertFalse(self.model_path.exists())
        self.assertEqual(self.package["status"], "blocked")

    def test_selected_work_requires_runtime_and_existing_conflicts_fail(self):
        self.model_path.unlink()
        for selected in ("package", "task"):
            self.assertIn("PACKAGE_INCIDENT_MODEL_MISSING", self.errors(self.validate(selected=selected)))
        self.model_path.write_text("{}")
        self.assertIn("PACKAGE_INCIDENT_MODEL_DIGEST", self.errors(self.validate()))

    def test_task_alias_cannot_promote_current_operation_to_historical(self):
        self.model_path.unlink()
        alias = copy.deepcopy(self.task)
        alias["task_id"] = "other-task"
        self.write_index([self.task, alias])
        self.assertIn("PACKAGE_INCIDENT_MODEL_MISSING", self.errors(self.validate(selected="same-operation")))

    def test_no_implicit_search_or_null_witness_and_invalid_bindings_fail_closed(self):
        self.model_path.unlink()
        original = copy.deepcopy(self.package["incident_continuity"]["retained_evidence"])
        self.package["incident_continuity"].pop("retained_evidence")
        self.assertIn("PACKAGE_INCIDENT_MODEL_MISSING", self.errors(self.validate()))
        for bad in (None, {}, [], True, 3, "unknown"):
            self.package["incident_continuity"]["retained_evidence"] = bad
            self.assertTrue(self.errors(self.validate()), bad)
        for field in original:
            for bad in (None, {}, [], True, 3, "unknown"):
                witness = copy.deepcopy(original); witness[field] = bad
                self.package["incident_continuity"]["retained_evidence"] = witness
                self.assertTrue(self.errors(self.validate()), (field, bad))

    def test_retained_model_projection_and_task_identity_substitution_reject(self):
        retained = self.package["incident_continuity"]["retained_evidence"]
        for key in ("model", "projection"):
            original = copy.deepcopy(retained[key])
            retained[key]["sha256"] = "f" * 64
            self.assertTrue(self.errors(self.validate()))
            retained[key] = original
        retained["task_id"] = "different-task"
        self.assertTrue(self.errors(self.validate()))

    def test_historical_use_is_explicit_and_cannot_hide_incident_drift(self):
        self.package["evidence_classification"] = "current"
        self.assertIn("PACKAGE_INCIDENT_RETAINED", self.errors(self.validate()))
        self.package["evidence_classification"] = "historical-record"
        self.package["incident_continuity"]["family_id"] = "other-family"
        self.assertIn("PACKAGE_INCIDENT_MODEL_DRIFT", self.errors(self.validate()))

    def test_malformed_incident_enums_never_crash_the_registered_method(self):
        from change_package_contract import incident_continuity_failures
        for key in ("mode", "trigger"):
            for bad in ({}, [], None, True, 3):
                value = copy.deepcopy(self.package)
                value["incident_continuity"][key] = bad
                self.assertTrue(incident_continuity_failures(value))

from __future__ import annotations

import copy
import json
from unittest.mock import patch

from tests.active_task_fixture import ActiveTaskFixture, ROOT
from check_change_packages import changed_index_validator
from finalize_target_support import build_steps
from target_adapter_validation.current_change import package_requirement, required_package_for_finalization


class PackageApplicabilityTests(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        (self.target / ".ai/alatyr.yaml").write_text(
            "modules:\n  selected: [change-packages]\n  enabled: [change-packages]\n", encoding="utf-8")
        router = self.target / ".ai/assistant/context-router.json"
        router.write_bytes((ROOT / "templates/target/.ai/assistant/context-router.json").read_bytes())
        descriptor = self.target / ".ai/assistant/context/profiles/code-local.json"
        descriptor.parent.mkdir(parents=True, exist_ok=True)
        descriptor.write_bytes((ROOT / "templates/target/.ai/assistant/context/profiles/code-local.json").read_bytes())
        report = self.target / "evidence/result.json"
        report.parent.mkdir(parents=True)
        report.write_text(json.dumps({"task_id": "fixture-task", "result": "bounded local evidence"}), encoding="utf-8")
        self.claim = {"schema_version": 1, "decision": "not-required",
            "reason": "One local fact in one area, evidenced by the ordinary operation result",
            "profile_id": "code-local", "project_area": "local-ui", "router": self.bind(router),
            "profile": self.bind(descriptor),
            "ordinary_result": self.bind(report), "activation": {
                "material_multisurface_approval": False, "architecture_or_contract": False,
                "multiple_facts_or_areas": False, "reproducible_case": False}}
        self.model["analysis_evidence"] = {"schema_version": 1, "probes": [], "updates": [],
            "review_challenges": [], "package_applicability": self.claim}
        for review in self.model["review_results"]:
            review["status"] = "pending"
        self.save()

    def save(self):
        self.write_model(); self.write_index()

    def validator(self):
        checked = changed_index_validator(self.target)
        checked.current_task_id = self.task["task_id"]
        checked.current_task_class = self.task["task_class"]
        checked.require_task_acceptance = True
        return checked

    def decision(self, **changes):
        return package_requirement(self.validator(), module_enabled=True, automatic=True, **changes)

    def finalizer(self):
        return build_steps(target=self.target, write=False, migration_staging=False, diff_ref=self.base,
            approval_records=[self.target / "approval.json"], change_packages=[], require_current_change=True,
            task_id=self.task["task_id"], task_class=self.task["task_class"], require_task_acceptance=True)

    def test_valid_bound_local_task_agrees_through_both_entrypoints(self):
        decision = self.decision()
        self.assertFalse(decision["required"], decision)
        self.assertEqual(decision["failures"], [])
        steps = self.finalizer()
        self.assertNotIn("--enforce-change-package", steps[-1].arguments)
        for argument in ("--enforce-approval-scope", "--require-task-acceptance", "--diff-ref", "--task-class"):
            self.assertIn(argument, steps[-1].arguments)
        checked = self.validator()
        checked.validation_phase = "acceptance"
        checked.run()
        self.assertFalse(checked.enforce_change_package)
        self.assertIn("PACKAGE_NOT_REQUIRED", {finding.code for finding in checked.findings})
        # Incomplete target installation still cannot acquire acceptance from an exemption.
        self.assertTrue(any(finding.level == "error" for finding in checked.findings))

    def test_no_claim_preserves_enabled_default_without_reading_optional_artifacts(self):
        self.model.pop("analysis_evidence"); self.save()
        with patch("current_task_view.current_task_view", side_effect=AssertionError("unadopted view expansion")):
            self.assertTrue(self.decision()["required"])
        with self.assertRaisesRegex(ValueError, "--change-package"):
            self.finalizer()

    def test_explicit_enforcement_overrides_valid_exemption(self):
        self.assertTrue(self.decision(explicit=True)["required"])
        checked = self.validator(); checked.enforce_change_package = True
        checked.validation_phase = "acceptance"; checked.run()
        self.assertTrue(checked.enforce_change_package)

    def test_each_positive_activation_condition_defeats_exemption(self):
        for key in self.claim["activation"]:
            with self.subTest(key=key):
                self.claim["activation"][key] = True; self.save()
                value = self.decision()
                self.assertTrue(value["required"], value)
                self.assertTrue(value["failures"])
                with self.assertRaisesRegex(ValueError, "activation"):
                    self.finalizer()
                self.claim["activation"][key] = False

    def test_wrong_profile_router_and_stale_result_fail_closed(self):
        original = copy.deepcopy(self.claim)
        for field, value in (("profile_id", "absent-profile"),
                             ("router", {**self.claim["router"], "path": "evidence/result.json"}),
                             ("ordinary_result", {**self.claim["ordinary_result"], "sha256": "0" * 64})):
            with self.subTest(field=field):
                self.model["analysis_evidence"]["package_applicability"] = {**original, field: value}
                self.save()
                result = self.decision()
                self.assertTrue(result["required"], result)
                self.assertTrue(result["failures"])

    def test_zero_multiple_and_mismatched_changed_facts_do_not_exempt(self):
        original = copy.deepcopy(self.model["changed_facts"])
        for count in (0, 2):
            self.model["changed_facts"] = [{**original[0], "id": f"change-{index+1}"} for index in range(count)]
            self.task["changed_fact_ids"] = [row["id"] for row in self.model["changed_facts"]]
            self.save()
            self.assertTrue(self.decision()["required"])
        self.model["changed_facts"] = original; self.task["changed_fact_ids"] = ["another-fact"]
        self.save(); self.assertTrue(self.decision()["required"])

    def test_named_task_acceptance_and_matching_class_cannot_be_omitted(self):
        for task_class, required in ((None, True), ("small-task", True), (self.task["task_class"], False)):
            with self.subTest(task_class=task_class, required=required), self.assertRaisesRegex(ValueError, "task"):
                required_package_for_finalization(self.target, self.task["task_id"], task_class,
                    require_task_acceptance=required)

    def test_malformed_claims_return_findings_not_tracebacks(self):
        original = copy.deepcopy(self.claim)
        for field in original:
            for value in ({}, [], None, True, 0):
                with self.subTest(field=field, value=value):
                    self.model["analysis_evidence"]["package_applicability"] = {**original, field: value}
                    self.save()
                    result = self.decision()
                    self.assertTrue(result["required"], result)
                    self.assertTrue(result["failures"])

    def test_capability_disabled_and_unselected_paths_keep_legacy_defaults(self):
        checked = self.validator()
        self.assertFalse(package_requirement(checked, module_enabled=False, automatic=True)["required"])
        self.assertFalse(package_requirement(checked, module_enabled=True, automatic=False)["required"])
        checked.current_task_id = None
        self.assertTrue(package_requirement(checked, module_enabled=True, automatic=True)["required"])

    def test_changed_package_plans_remain_checked_during_exemption(self):
        plan = self.target / ".ai/assistant/change-packages/plan.md"
        plan.parent.mkdir(parents=True); plan.write_text("unindexed changed plan", encoding="utf-8")
        checked = self.validator(); checked.enforce_change_package = False
        checked.check_change_packages()
        self.assertIn("PACKAGE_ACTIVE_PLAN_UNINDEXED", {finding.code for finding in checked.findings})

    def test_explicit_selected_package_does_not_consult_exemption(self):
        self.claim["activation"]["architecture_or_contract"] = True; self.save()
        steps = build_steps(target=self.target, write=False, migration_staging=False, diff_ref=self.base,
            approval_records=[self.target / "approval.json"], change_packages=[self.target / "package.json"],
            require_current_change=True, task_id=self.task["task_id"], task_class=self.task["task_class"],
            require_task_acceptance=True)
        self.assertIn("--enforce-change-package", steps[-1].arguments)
        checked = self.validator()
        checked.change_packages = [self.target / "package.json"]
        checked.validation_phase = "acceptance"
        checked.run()
        self.assertTrue(checked.enforce_change_package)
        self.assertFalse({"PACKAGE_APPLICABILITY", "PACKAGE_NOT_REQUIRED"} &
                         {finding.code for finding in checked.findings})

    def test_router_representation_uses_canonical_selection_without_tracebacks(self):
        path = self.target / self.claim["router"]["path"]
        original = json.loads(path.read_bytes())
        for index in (None, [], {}, {"code-local": None}, {"code-local": {"descriptor": []}},
                      {"code-local": {"descriptor": "missing.json"}}):
            for version in (2, original["schema_version"]):
                with self.subTest(index=index, version=version):
                    value = {"schema_version": version, "profiles": {"code-local": {}}, "profile_index": index}
                    path.write_text(json.dumps(value), encoding="utf-8")
                    self.claim["router"] = self.bind(path)
                    self.claim["profile"] = None
                    self.save()
                    result = self.decision()
                    self.assertEqual(result["required"], version != 2, result)

    def test_inline_legacy_and_malformed_routers(self):
        path = self.target / self.claim["router"]["path"]
        for profiles in ({"code-local": {}}, None, [], 7):
            with self.subTest(profiles=profiles):
                path.write_text(json.dumps({"schema_version": 2, "profiles": profiles}), encoding="utf-8")
                self.claim["router"] = self.bind(path); self.claim["profile"] = None; self.save()
                result = self.decision()
                self.assertEqual(result["required"], not isinstance(profiles, dict), result)

    def test_missing_changed_and_foreign_profile_descriptors(self):
        path = self.target / self.claim["profile"]["path"]
        original = path.read_bytes()
        for change in ("missing", "changed", "wrong-identity"):
            with self.subTest(change=change):
                if change == "missing": path.unlink()
                elif change == "changed": path.write_bytes(b"{}")
                else:
                    value = json.loads(original); value["profile"] = "another-profile"
                    path.write_text(json.dumps(value), encoding="utf-8"); self.claim["profile"] = self.bind(path); self.save()
                self.assertTrue(self.decision()["required"])
                path.write_bytes(original)

    def test_selected_profile_does_not_open_other_descriptors(self):
        checked = self.validator()
        observed = []
        real = checked.load_context_descriptor
        def selected(entry, *args):
            observed.append(entry["descriptor"])
            return real(entry, *args)
        with patch.object(checked, "load_context_descriptor", side_effect=selected):
            result = package_requirement(checked, module_enabled=True, automatic=True)
        self.assertFalse(result["required"], result)
        self.assertEqual(observed, [self.claim["profile"]["path"]])

    def test_closed_task_exemption_still_checks_each_bound_artifact(self):
        self.close()
        self.assertFalse(self.decision()["required"])
        for key in ("router", "profile", "ordinary_result"):
            path = self.target / self.claim[key]["path"]
            original = path.read_bytes()
            for change in ("changed", "missing"):
                with self.subTest(key=key, change=change):
                    if change == "changed":
                        path.write_bytes(original + b"\n")
                    else:
                        path.unlink()
                    self.assertTrue(self.decision()["required"])
                    with self.assertRaises(ValueError):
                        self.finalizer()
                    path.write_bytes(original)

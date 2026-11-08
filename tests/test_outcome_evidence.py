from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from unittest.mock import patch

from tests.active_task_fixture import ActiveTaskFixture, ROOT
from tests.test_analysis_evidence import add_evidence

sys.path.insert(0, str(ROOT / "tools"))
from analysis_evidence import active_evidence, evidence_failures, revision_failures, verify_artifacts
from analysis_strategy_contract import load_json_object, validate_problem_model
from current_task_view import current_task_view
from check_change_packages import changed_index_validator
from outcome_evidence import case_binding
from publish_active_task import prepare


def add_outcome(model, target):
    result = target / "evidence/outcome.json"
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_bytes(b'{"original_case":"observed","fixture_only":true}\n')
    result_path = result.relative_to(target).as_posix()
    scope = {"actor": "ordinary caller", "system": "owned PostgreSQL fixture",
             "entrypoint": "normal producer-to-consumer entry", "conditions": "representative input volume",
             "surfaces": ["src/example.txt"]}
    case = {"id": "original-flow", "source_ref": "request:original-flow", "oracle": {
                "path": "design.md", "sha256": hashlib.sha256((target / "design.md").read_bytes()).hexdigest()},
            "expected_result": "Every requested input has its required terminal outcome",
            "rejected_substitute": "Green component tests with an incomplete reporting pipeline",
            "scope": scope, "evidence_class": "original-case", "proof_obligation_ids": ["proof-1"],
            "observation": None}
    case["observation"] = {"case_sha256": case_binding(model, case), "scope": copy.deepcopy(scope),
        "evidence_class": "original-case", "status": "supported", "decisive_check_reached": True,
        "actual_result": "The fixture's retained original outcome was observed",
        "input_sha256": {path: hashlib.sha256((target / path).read_bytes()).hexdigest() for path in scope["surfaces"]},
        "artifacts": [{"path": result_path, "sha256": hashlib.sha256(result.read_bytes()).hexdigest()}]}
    model["proof_obligations"][0]["evidence_refs"].append(result_path)
    model["analysis_evidence"]["outcome_checks"] = [case]
    return case


class OutcomeEvidenceTests(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        add_evidence(self.model, self.target)
        self.case = add_outcome(self.model, self.target)
        self.schema = load_json_object(ROOT / "schemas/alatyr-problem-model.schema.json")
        self.write_model(); self.write_index()

    def failures(self, model=None):
        return validate_problem_model(self.model if model is None else model, self.schema)

    def pending(self):
        self.model["proof_obligations"][0]["status"] = "open"
        self.model["review_results"][0]["status"] = "pending"
        self.model["analysis_evidence"]["review_challenges"][0]["status"] = "pending"

    def test_valid_check_passes_registered_phase_and_selected_view(self):
        self.assertEqual(self.failures(), [])
        self.assertEqual(self.errors(self.check()), set())
        value = current_task_view(changed_index_validator(self.target), "fixture-task")
        self.assertEqual(value["state"], "bound-recorded-disposition", value)
        self.assertFalse(value["acceptance_granted"])
        summary = active_evidence(self.model)["outcome_checks"][0]
        self.assertEqual(summary["qualification"], "record-consistent-not-semantic-proof")
        self.assertEqual(summary["case_sha256"], case_binding(self.model, self.case))
        self.assertEqual(summary["diagnostics"], [])
        self.close()
        self.assertEqual(self.errors(self.check()), set())

    def test_wrong_system_scope_component_counts_and_unreached_assertions_cannot_pass_proof(self):
        mutations = (("system", "owned MongoDB fixture"), ("surfaces", []), ("conditions", "empty fixture"),
                     ("actor", "privileged shortcut"), ("entrypoint", "post-boundary injection"))
        for key, value in mutations:
            model = copy.deepcopy(self.model)
            model["analysis_evidence"]["outcome_checks"][0]["observation"]["scope"][key] = value
            with self.subTest(key=key): self.assertTrue(self.failures(model))
        for key, value in (("evidence_class", "component-execution"), ("decisive_check_reached", False),
                           ("status", "contradicted"), ("status", "inconclusive")):
            model = copy.deepcopy(self.model)
            model["analysis_evidence"]["outcome_checks"][0]["observation"][key] = value
            with self.subTest(key=key, value=value): self.assertTrue(self.failures(model))
        self.case["observation"] = None
        self.assertTrue(any("unobserved" in message for message in self.failures()))

    def test_honest_inconclusive_progress_is_valid_but_cannot_close_task(self):
        self.pending()
        self.case["observation"].update(status="inconclusive", decisive_check_reached=False,
                                        evidence_class="component-execution")
        self.assertEqual(self.failures(), [])
        self.assertTrue(evidence_failures(self.model, completion=True))
        self.write_model(); self.write_index()
        self.assertEqual(self.errors(self.check()), set())
        self.close()
        self.assertTrue(self.errors(self.check()))

    def test_characterizing_38_missing_scopes_does_not_repair_original_outcome(self):
        self.case["observation"].update(status="contradicted", actual_result="Component suite passes; 38 required scopes remain missing")
        self.assertTrue(self.failures())
        self.pending()
        self.assertEqual(self.failures(), [])
        self.assertTrue(evidence_failures(self.model, completion=True))

    def test_projection_does_not_promote_supported_wrong_scope_or_unreached_check(self):
        self.pending()
        self.case["observation"]["decisive_check_reached"] = False
        summary = active_evidence(self.model)["outcome_checks"][0]
        self.assertEqual(summary["qualification"], "unverified")
        self.assertTrue(any("not reached" in message for message in summary["diagnostics"]))

    def test_request_rows_are_the_coverage_owner_even_for_partial_answers(self):
        from request_brief import action_failures
        from tests.test_request_brief import action_fixture, brief_fixture
        brief = brief_fixture(self.model["objective"], "proof-1")
        brief.update(source_ref=self.case["source_ref"], task_id="fixture-task")
        brief["outcomes"][0].update(id=self.case["id"], statement=self.case["expected_result"],
                                   rejection_case=self.case["rejected_substitute"])
        action = action_fixture(task_id="fixture-task", kind="answer", phase="inspect", paths=[],
                                outcome_ids=[self.case["id"]])
        def review():
            return action_failures(brief, action, self.model, request_id=brief["request_id"], task_id="fixture-task")
        self.assertEqual(review(), [])
        for key in ("source_ref", "statement", "rejection_case"):
            candidate = copy.deepcopy(brief)
            if key == "source_ref": candidate[key] = "different source"
            else: candidate["outcomes"][0][key] = "an easier result"
            self.assertTrue(action_failures(candidate, action, self.model,
                request_id=brief["request_id"], task_id="fixture-task"))
        brief["outcomes"].append({**brief["outcomes"][0], "id": "omitted-host"})
        self.assertTrue(any("no captured" in message for message in review()))

    def test_successor_cannot_drop_or_relax_original_outcomes_without_bound_owner_supersession(self):
        from outcome_evidence import inherited_failures
        from tests.test_behavior_acceptance import original_case
        candidate = copy.deepcopy(self.model)
        candidate["analysis_evidence"].pop("outcome_checks")
        self.assertTrue(inherited_failures(self.model, candidate))
        candidate = copy.deepcopy(self.model)
        candidate["analysis_evidence"]["outcome_checks"][0]["expected_result"] = "Owner changed the required result"
        self.assertTrue(inherited_failures(self.model, candidate))
        candidate["original_case"] = original_case()
        decision = {"source_ref": "decisions/changed-requirement.md", "decision_owner": "project owner",
                    "reason": "Explicit scoped change to the original requirement"}
        candidate["original_case"].update(status="superseded-by-owner-decision", supersession=decision,
                                         evidence_refs=[decision["source_ref"]])
        self.assertTrue(inherited_failures(self.model, candidate))
        candidate["analysis_evidence"]["selected_context"] = [{"path": decision["source_ref"], "sha256": "a" * 64}]
        self.assertTrue(inherited_failures(self.model, candidate))
        decision["outcome_changes"] = [{"case_id": self.case["id"],
            "predecessor_sha256": case_binding(self.model, self.case),
            "replacement_sha256": case_binding(candidate, candidate["analysis_evidence"]["outcome_checks"][0])}]
        self.assertEqual(inherited_failures(self.model, candidate), [])
        candidate["analysis_evidence"]["outcome_checks"][0]["evidence_class"] = "component-execution"
        self.assertTrue(inherited_failures(self.model, candidate))

    def test_decision_artifact_must_contain_the_exact_declared_supersession_scope(self):
        from outcome_evidence import supersession_artifact_failures
        from tests.test_behavior_acceptance import original_case
        self.model["original_case"] = original_case()
        decision = {"source_ref": "decisions/scope.json", "decision_owner": "project owner", "reason": "Owner changed scope",
            "outcome_changes": [{"case_id": "original-flow", "predecessor_sha256": "a" * 64, "replacement_sha256": "b" * 64}]}
        self.model["original_case"].update(status="superseded-by-owner-decision", supersession=decision)
        raw = json.dumps({"decision_owner": decision["decision_owner"], "outcome_changes": decision["outcome_changes"]}).encode()
        self.assertEqual(supersession_artifact_failures(self.model, decision["source_ref"], raw), [])
        decision["outcome_changes"][0]["replacement_sha256"] = "c" * 64
        self.assertTrue(supersession_artifact_failures(self.model, decision["source_ref"], raw))
        for raw in (b"not JSON", b"[]", b'{"outcome_changes":[],"outcome_changes":[]}'):
            self.assertTrue(supersession_artifact_failures(self.model, decision["source_ref"], raw))

    def test_rehashed_proof_rewording_requires_scoped_supersession(self):
        from analysis_evidence import probe_binding
        from outcome_evidence import inherited_failures
        candidate = copy.deepcopy(self.model)
        candidate["proof_obligations"][0]["statement"] = "Accept only component progress instead"
        case = candidate["analysis_evidence"]["outcome_checks"][0]
        case["observation"]["case_sha256"] = case_binding(candidate, case)
        probe = candidate["analysis_evidence"]["probes"][0]
        probe["result"]["probe_sha256"] = probe_binding(candidate, probe)
        self.assertEqual(self.failures(candidate), [])
        self.assertTrue(revision_failures(self.model, candidate))
        self.assertTrue(inherited_failures(self.model, candidate))
        path = self.target / ".ai/.runtime/candidate.json"
        path.write_text(json.dumps(candidate))
        with self.assertRaisesRegex(ValueError, "outcome"):
            prepare(self.target, "fixture-task", ".ai/.runtime/candidate.json")

    def test_supersession_requires_retained_decision_binding_and_cannot_disappear(self):
        from outcome_evidence import retention_failures
        from tests.test_behavior_acceptance import original_case
        self.model["original_case"] = original_case()
        self.model["original_case"]["source_ref"] = self.case["source_ref"]
        self.model["analysis_evidence"]["review_challenges"][0]["original_source_ref"] = self.case["source_ref"]
        decision = {"source_ref": "evidence/decision.json", "decision_owner": "project owner", "reason": "Owner changed scope",
            "outcome_changes": [{"case_id": self.case["id"], "predecessor_sha256": "a" * 64,
                                 "replacement_sha256": case_binding(self.model, self.case)}]}
        self.model["original_case"].update(status="superseded-by-owner-decision", supersession=decision,
                                          evidence_refs=[decision["source_ref"]])
        path = self.target / decision["source_ref"]
        path.write_text(json.dumps({key: decision[key] for key in ("decision_owner", "outcome_changes")}))
        self.model["analysis_evidence"]["selected_context"] = [self.bind(path)]
        self.case["observation"]["case_sha256"] = case_binding(self.model, self.case)
        self.assertEqual(self.failures(), [])
        self.assertEqual(active_evidence(self.model)["outcome_checks"][0]["qualification"], "record-consistent-not-semantic-proof")
        second = copy.deepcopy(self.case)
        second["id"] = "second-original-flow"
        second["observation"]["case_sha256"] = case_binding(self.model, second)
        self.model["analysis_evidence"]["outcome_checks"].append(second)
        decision["outcome_changes"].append({"case_id": second["id"], "predecessor_sha256": "b" * 64,
                                           "replacement_sha256": case_binding(self.model, second)})
        path.write_text(json.dumps({key: decision[key] for key in ("decision_owner", "outcome_changes")}))
        self.model["analysis_evidence"]["selected_context"] = [self.bind(path)]
        self.assertEqual(self.failures(), [])
        self.assertEqual([row["qualification"] for row in active_evidence(self.model)["outcome_checks"]],
                         ["record-consistent-not-semantic-proof"] * 2)
        second["observation"]["status"] = "inconclusive"
        self.assertEqual([row["qualification"] for row in active_evidence(self.model)["outcome_checks"]],
                         ["record-consistent-not-semantic-proof", "unverified"])
        second["observation"]["status"] = "supported"
        self.assertEqual(verify_artifacts(self.model, lambda name, limit: (self.target / name).read_bytes(), historical_outcomes=True), [])
        for mutation in ("missing-context", "missing-source", "missing-changes"):
            candidate = copy.deepcopy(self.model)
            if mutation == "missing-context": candidate["analysis_evidence"].pop("selected_context")
            elif mutation == "missing-source": candidate["analysis_evidence"]["selected_context"][0]["path"] = "design.md"
            else: candidate["original_case"]["supersession"].pop("outcome_changes")
            with self.subTest(mutation=mutation):
                self.assertTrue(self.failures(candidate))
                self.assertTrue(retention_failures(candidate, lambda _: False))
        candidate = copy.deepcopy(self.model)
        candidate["original_case"].update(status="verified-fixed", supersession=None)
        self.assertTrue(revision_failures(self.model, candidate))

    def test_historical_outcomes_keep_oracle_and_result_but_do_not_recheck_current_source(self):
        self.close()
        (self.target / "src/example.txt").write_bytes(b"a later unrelated implementation revision\n")
        self.assertEqual(self.errors(self.check(selected=False)), set())
        result = self.target / "evidence/outcome.json"
        result.write_bytes(b"changed historical observation\n")
        self.assertIn("ANALYSIS_EVIDENCE_ARTIFACT", self.errors(self.check(selected=False)))

    def test_archive_rejects_ignored_or_missing_results_and_binds_retained_inputs(self):
        from archive_task_evidence import prepare as archive
        self.close()
        plan = archive(self.target, "fixture-task", "owner:retention-review")
        self.assertIn(self.target / "evidence/outcome.json", plan.inputs)
        root_ignore = self.target / ".gitignore"
        root_ignore.write_text("evidence/outcome.json\n")
        with self.assertRaisesRegex(ValueError, "retainable"):
            archive(self.target, "fixture-task", "owner:retention-review")
        root_ignore.unlink()
        (self.target / "evidence/outcome.json").unlink()
        with self.assertRaisesRegex(ValueError, "missing retained outcome"):
            archive(self.target, "fixture-task", "owner:retention-review")

    def test_a_falsely_supported_text_claim_is_not_semantically_authenticated(self):
        self.case["observation"]["actual_result"] = "A self-authored claim contradicts the human outcome"
        self.assertEqual(self.failures(), [])
        # This explicit limit needs an independent oracle; do not add prose matching.

    def test_source_review_and_expected_safe_rejection_are_not_forced_to_execute_product(self):
        self.case.update(evidence_class="source-review", expected_result="Unproven identity is safely held without writes")
        self.case["observation"].update(evidence_class="source-review",
            actual_result="Source review retains the identity hold and unresolved reconciliation")
        self.case["observation"]["case_sha256"] = case_binding(self.model, self.case)
        self.assertEqual(self.failures(), [])
        self.assertEqual(evidence_failures(self.model, completion=True), [])

    def test_missing_or_waived_outcome_obligation_cannot_establish_completion(self):
        for ids in (["unknown"], ["proof-1", "unknown"]):
            model = copy.deepcopy(self.model)
            model["analysis_evidence"]["outcome_checks"][0]["proof_obligation_ids"] = ids
            self.assertTrue(self.failures(model))
        self.pending()
        self.model["proof_obligations"][0].update(status="waived", waiver={
            "decision_owner": "primary-assistant", "authority_ref": "review:waiver", "evidence_refs": ["review:waiver"]})
        self.assertTrue(any("not waived" in message for message in evidence_failures(self.model, completion=True)))

    def test_original_source_and_exact_case_digest_cannot_be_substituted(self):
        for mutate in (lambda m, c: c.update(expected_result="Accept partial reports"),
                       lambda m, c: m["proof_obligations"][0].update(statement="An easier proof"),
                       lambda m, c: m["task_binding"].update(task_ids=["other-task"])):
            model = copy.deepcopy(self.model)
            case = model["analysis_evidence"]["outcome_checks"][0]
            mutate(model, case)
            self.assertTrue(any("stale oracle/case" in message for message in self.failures(model)))
        from tests.test_behavior_acceptance import original_case
        self.model["original_case"] = original_case()
        self.assertTrue(any("original request source" in message for message in self.failures()))

    def test_oracle_surface_and_result_staleness_share_existing_artifact_verification(self):
        for path in ("design.md", "src/example.txt", "evidence/outcome.json"):
            target = self.target / path
            previous = target.read_bytes()
            target.write_bytes(previous + b"changed\n")
            with self.subTest(path=path): self.assertIn("ANALYSIS_EVIDENCE_ARTIFACT", self.errors(self.check()))
            target.write_bytes(previous)
        self.assertEqual(self.errors(self.check()), set())

    def test_actual_public_cli_rejects_unreached_decisive_check(self):
        self.case["observation"]["decisive_check_reached"] = False
        self.write_model(); self.write_index()
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/validate_target_adapter.py"),
            "--target", str(self.target), "--task-id", "fixture-task", "--task-class", "standard-task",
            "--validation-phase", "migration-staging", "--json"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("ANALYSIS_PROBLEM_MODEL_INVALID", {row["code"] for row in payload["findings"]})

    def test_oracle_or_coverage_cannot_be_erased_on_publication(self):
        self.write_model(); self.write_index()
        for mutation in ("remove", "scope", "expectation"):
            model = copy.deepcopy(self.model)
            case = model["analysis_evidence"]["outcome_checks"][0]
            if mutation == "remove": del model["analysis_evidence"]["outcome_checks"]
            elif mutation == "scope": case["scope"]["surfaces"] = ["design.md"]
            else: case["expected_result"] = "Accept missing outputs"
            if mutation != "remove": case["observation"] = None
            model["proof_obligations"][0]["status"] = "open"
            model["review_results"][0]["status"] = "pending"
            model["analysis_evidence"]["review_challenges"][0]["status"] = "pending"
            self.assertTrue(revision_failures(self.model, model))
            candidate = self.target / ".ai/.runtime/candidate.json"
            candidate.write_text(json.dumps(model))
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, "outcome"):
                prepare(self.target, "fixture-task", ".ai/.runtime/candidate.json")

    def test_digest_verification_is_deduplicated_and_legacy_route_does_not_load_cases(self):
        calls = []
        def read(path, limit):
            calls.append(path)
            return (self.target / path).read_bytes()
        self.assertEqual(verify_artifacts(self.model, read), [])
        self.assertEqual(calls.count("design.md"), 1)
        self.assertEqual(calls.count("src/example.txt"), 1)
        del self.model["analysis_evidence"]["outcome_checks"]
        with patch("outcome_evidence.outcome_failures", side_effect=AssertionError("unselected checks")):
            self.assertEqual(self.failures(), [])

    def test_malformed_and_boundary_fields_return_findings_through_registered_handler(self):
        for field in ("evidence_class", "status", "decisive_check_reached", "input_sha256", "artifacts"):
            for bad in (None, True, 3, "unknown", [], {}, [{}]):
                if field == "decisive_check_reached" and bad is True: continue
                model = copy.deepcopy(self.model)
                model["analysis_evidence"]["outcome_checks"][0]["observation"][field] = bad
                with self.subTest(field=field, bad=bad): self.assertTrue(self.failures(model))
        for count in (15, 16, 17):
            model = copy.deepcopy(self.model)
            rows = [copy.deepcopy(self.case) for _ in range(count)]
            for index, row in enumerate(rows):
                row["id"] = f"case-{index}"
                row["observation"]["case_sha256"] = case_binding(model, row)
            model["analysis_evidence"]["outcome_checks"] = rows
            # Keep the portable total-size ceilings; schema count is tested separately.
            import jsonschema
            self.assertEqual(not list(jsonschema.Draft7Validator(self.schema).iter_errors(model)), count <= 16)
        self.case["observation"]["status"] = {}
        self.write_model(); self.write_index()
        self.assertIn("ANALYSIS_PROBLEM_MODEL_INVALID", self.errors(self.check()))

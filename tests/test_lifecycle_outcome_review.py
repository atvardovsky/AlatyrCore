from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from unittest.mock import patch

from tests.active_task_fixture import ActiveTaskFixture, ROOT
from tests.test_analysis_evidence import add_evidence
from tests.test_outcome_evidence import add_outcome
from tests.test_request_brief import action_fixture, brief_fixture

sys.path.insert(0, str(ROOT / "tools"))
from analysis_evidence import evidence_readiness, verify_artifacts
from lifecycle_checkpoints import review_request


class LifecycleOutcomeReviewTests(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        add_evidence(self.model, self.target)
        self.case = add_outcome(self.model, self.target)
        self.brief = brief_fixture(self.model["objective"], "proof-1")
        self.brief["source_ref"] = self.case["source_ref"]
        self.brief["outcomes"][0].update(id=self.case["id"], statement=self.case["expected_result"],
                                        rejection_case=self.case["rejected_substitute"])
        self.brief_path = ".ai/.runtime/request.json"
        self.save()

    def save(self):
        self.write_model(); self.write_index()
        (self.target / self.brief_path).write_text(json.dumps(self.brief), encoding="utf-8")

    def action(self, **changes):
        value = action_fixture(outcome_ids=[self.case["id"]], **changes)
        if self.brief.get("focus_control"):
            value.update(brief_sha256=hashlib.sha256((self.target / self.brief_path).read_bytes()).hexdigest(),
                         obligation_ids=self.brief["outcomes"][0]["proof_obligation_ids"])
        return value

    def run_delegate(self, action):
        command = [sys.executable, "-B", str(ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"),
                   "lifecycle-checkpoint", "--target", str(self.target), "--framework-source", str(ROOT),
                   "review", "--request-brief", self.brief_path]
        result = subprocess.run(command, input=json.dumps(action), capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def pending(self):
        self.model["proof_obligations"][0]["status"] = "open"
        self.model["review_results"][0]["status"] = "pending"
        self.model["analysis_evidence"]["review_challenges"][0]["status"] = "pending"

    def test_installed_delegate_before_after_mutation_for_answer_work_and_completion(self):
        for kind, phase, paths in (("answer", "inspect", []), ("work", "modify", ["src/example.txt"]),
                                   ("complete", "inspect", [])):
            with self.subTest(stage="current", kind=kind):
                code, value = self.run_delegate(self.action(kind=kind, phase=phase, paths=paths))
                self.assertEqual(code, 0, value)
                self.assertEqual(value["evidence_readiness"]["state"], "current-content-not-execution-proof")
        (self.target / "evidence/outcome.json").write_bytes(b"changed result\n")
        before = {p.relative_to(self.target): p.read_bytes() for p in self.target.rglob("*")
                  if p.is_file() and ".git" not in p.parts}
        for kind, phase, paths, expected in (("answer", "inspect", [], 0), ("work", "inspect", [], 0),
                                            ("work", "modify", ["src/example.txt"], 1), ("complete", "inspect", [], 2)):
            with self.subTest(stage="stale", kind=kind, phase=phase):
                code, value = self.run_delegate(self.action(kind=kind, phase=phase, paths=paths))
                self.assertEqual(code, expected, value)
                self.assertFalse(value["authorization_granted"])
                self.assertFalse(value["acceptance_granted"])
                if kind != "complete":
                    self.assertEqual(value["evidence_readiness"]["state"], "stale-or-unavailable")
                    self.assertIn("evidence/outcome.json", str(value["evidence_readiness"]["diagnostics"]))
                    self.assertEqual(value["request_progress"]["remaining_outcome_ids"], [self.case["id"]])
        after = {p.relative_to(self.target): p.read_bytes() for p in self.target.rglob("*")
                 if p.is_file() and ".git" not in p.parts}
        self.assertEqual(before, after)

    def test_adopted_focus_also_rejects_stale_evidence_without_freezing_inspection(self):
        self.pending()
        self.model["execution_dependencies"] = [{"obligation_id": row["id"], "requires": []}
                                                 for row in self.model["proof_obligations"]]
        self.brief.update(schema_version=3, delivery_control=None, focus_control="dependency-readiness")
        self.save()
        self.assertEqual(self.run_delegate(self.action())[0], 0)
        (self.target / "evidence/outcome.json").write_bytes(b"changed result\n")
        self.assertEqual(self.run_delegate(self.action())[0], 1)
        code, value = self.run_delegate(self.action(kind="answer", phase="inspect", paths=[]))
        self.assertEqual(code, 0, value)
        self.assertEqual(value["evidence_readiness"]["action_state"], "read-only-recovery")

    def test_component_latency_cannot_replace_original_click_to_usable_scope(self):
        from outcome_evidence import case_binding
        self.case["scope"].update(entrypoint="ordinary tab click to usable list",
            conditions="representative full-volume workload with ordinary background requests")
        self.case["observation"]["scope"] = copy.deepcopy(self.case["scope"])
        self.case["observation"]["case_sha256"] = case_binding(self.model, self.case)
        self.save()
        self.assertEqual(self.run_delegate(self.action(kind="complete", phase="inspect", paths=[]))[0], 0)
        self.case["observation"]["scope"].update(entrypoint="response received to render",
            conditions="small isolated fixture with background work disabled")
        self.save()
        self.assertNotEqual(self.run_delegate(self.action(kind="complete", phase="inspect", paths=[]))[0], 0)

    def independent_outcome(self):
        proof = copy.deepcopy(self.model["proof_obligations"][0])
        proof.update(id="independent", status="open", evidence_refs=[])
        self.model["proof_obligations"].append(proof)
        self.brief["outcomes"].append({**self.brief["outcomes"][0], "id": "independent",
                                      "proof_obligation_ids": ["independent"]})
        case = copy.deepcopy(self.case)
        case.update(id="independent", proof_obligation_ids=["independent"], observation=None)
        self.model["analysis_evidence"]["outcome_checks"].append(case)
        self.model["execution_dependencies"] = [{"obligation_id": row["id"], "requires": []}
                                                 for row in self.model["proof_obligations"]]
        self.save()

    def test_independent_branch_remains_available_but_stale_prerequisite_does_not(self):
        self.independent_outcome()
        (self.target / "evidence/outcome.json").write_bytes(b"changed result\n")
        action = action_fixture(outcome_ids=["independent"])
        value = review_request(self.target, self.brief_path, action)
        self.assertEqual(value["status"], "request-consistent", value)
        self.assertEqual(value["evidence_readiness"]["action_state"], "not-relied-upon")
        self.assertIn("independent", value["request_progress"]["ready_outcome_ids"])
        self.model["execution_dependencies"][-1]["requires"] = ["proof-1"]
        self.save()
        value = review_request(self.target, self.brief_path, action)
        self.assertEqual(value["status"], "request-review-required", value)

    def test_shared_context_and_writing_a_stale_artifact_require_review(self):
        self.independent_outcome()
        action = action_fixture(outcome_ids=["independent"])
        (self.target / "design.md").write_bytes(b"changed shared oracle\n")
        self.assertTrue(review_request(self.target, self.brief_path, action)["checkpoint_required"])
        (self.target / "design.md").write_bytes(b"accepted design\n")
        self.brief["write_scope"].append({"path": "evidence", "recursive": True})
        self.save()
        (self.target / "evidence/outcome.json").write_bytes(b"changed result\n")
        self.assertTrue(review_request(self.target, self.brief_path,
                                      {**action, "paths": ["evidence/outcome.json"]})["checkpoint_required"])

    def test_unconfigured_dependencies_cannot_establish_independence(self):
        self.independent_outcome()
        self.model.pop("execution_dependencies")
        self.save()
        (self.target / "evidence/outcome.json").write_bytes(b"changed result\n")
        value = review_request(self.target, self.brief_path, action_fixture(outcome_ids=["independent"]))
        self.assertEqual(value["status"], "request-review-required", value)

    def test_missing_artifact_is_visible_during_read_only_recovery(self):
        (self.target / "evidence/outcome.json").unlink()
        value = review_request(self.target, self.brief_path, self.action(kind="answer", phase="inspect", paths=[]))
        self.assertEqual(value["status"], "request-consistent", value)
        self.assertEqual(value["evidence_readiness"]["state"], "stale-or-unavailable")
        self.assertTrue(value["evidence_readiness"]["global_review_required"])
        self.assertTrue(value["evidence_readiness"]["diagnostics"])

    def test_independent_branch_with_adopted_focus_retains_original_digest(self):
        self.independent_outcome()
        self.brief.update(schema_version=3, delivery_control=None, focus_control="dependency-readiness")
        self.save()
        (self.target / "evidence/outcome.json").write_bytes(b"changed result\n")
        action = action_fixture(outcome_ids=["independent"], obligation_ids=["independent"],
            brief_sha256=hashlib.sha256((self.target / self.brief_path).read_bytes()).hexdigest())
        code, value = self.run_delegate(action)
        self.assertEqual(code, 0, value)
        self.assertEqual(value["evidence_readiness"]["action_state"], "not-relied-upon")
        action["brief_sha256"] = "0" * 64
        self.assertEqual(self.run_delegate(action)[0], 1)

    def test_aliased_stale_artifacts_cannot_escape_file_or_directory_write_review(self):
        self.independent_outcome()
        original = self.case["observation"]["artifacts"][0]["path"]
        self.brief["write_scope"].append({"path": "evidence", "recursive": True})
        for alias in ("./evidence/outcome.json", "evidence//outcome.json"):
            self.case["observation"]["artifacts"][0]["path"] = alias
            self.model["proof_obligations"][0]["evidence_refs"].append(alias)
            self.save()
            (self.target / original).write_bytes(b"changed result\n")
            for path in ("evidence/outcome.json", "evidence"):
                with self.subTest(alias=alias, action_path=path):
                    code, value = self.run_delegate(action_fixture(outcome_ids=["independent"], paths=[path]))
                    self.assertEqual(code, 2 if path == "evidence" else 1, value)
                    self.assertTrue(value["checkpoint_required"])
                    if path != "evidence": self.assertTrue(value["evidence_readiness"]["checkpoint_required"])

    def test_independent_sibling_proof_within_one_outcome_is_not_hidden(self):
        self.independent_outcome()
        self.model["analysis_evidence"].pop("outcome_checks")
        self.brief["outcomes"].pop()
        self.brief["outcomes"][0]["proof_obligation_ids"].append("independent")
        self.brief.update(schema_version=3, delivery_control=None, focus_control="dependency-readiness")
        self.brief["authorized_phases"].extend(["commit", "publish", "live-external"])
        self.brief["effect_scope"] = ["selected-effect"]
        self.save()
        (self.target / ".ai/.runtime/probe-result.txt").write_bytes(b"changed result\n")
        action = action_fixture(outcome_ids=[self.case["id"]], obligation_ids=["independent"],
            brief_sha256=hashlib.sha256((self.target / self.brief_path).read_bytes()).hexdigest())
        for phase in ("modify", "commit", "publish", "live-external"):
            with self.subTest(phase=phase):
                selected = {**action, "phase": phase, "paths": ["src/example.txt"] if phase == "modify" else [],
                            "effects": [] if phase == "modify" else ["selected-effect"]}
                code, value = self.run_delegate(selected)
                self.assertEqual(code, 0, value)
                self.assertEqual(value["evidence_readiness"]["action_state"], "not-relied-upon")
                self.assertEqual(value["request_progress"]["outcomes"][0]["ready_obligation_ids"], ["independent"])
                self.assertEqual(value["request_progress"]["remaining_outcome_ids"], [self.case["id"]])
        self.model["execution_dependencies"][-1]["requires"] = ["proof-1"]
        self.save()
        self.assertEqual(self.run_delegate(action)[0], 1)

    def test_symlink_artifact_alias_uses_the_existing_read_identity(self):
        self.independent_outcome()
        alias = self.target / "evidence/linked.json"
        try:
            alias.symlink_to("outcome.json")
        except OSError as exc:
            self.skipTest(f"symlink capability unavailable: {exc}")
        self.case["observation"]["artifacts"][0]["path"] = "evidence/linked.json"
        self.model["proof_obligations"][0]["evidence_refs"].append("evidence/linked.json")
        self.brief["write_scope"].append({"path": "evidence", "recursive": True})
        self.save()
        (self.target / "evidence/outcome.json").write_bytes(b"changed result\n")
        code, value = self.run_delegate(action_fixture(outcome_ids=["independent"], paths=["evidence/outcome.json"]))
        self.assertEqual(code, 1, value)
        self.assertTrue(value["evidence_readiness"]["checkpoint_required"])
        self.assertEqual(value["evidence_readiness"]["diagnostics"][0]["identity"], "evidence/outcome.json")

    def test_all_state_changing_phases_and_non_outcome_artifacts_share_the_guard(self):
        self.brief["authorized_phases"].extend(["commit", "publish", "live-external"])
        self.brief["effect_scope"] = ["selected-effect"]
        self.save()
        for artifact in (".ai/.runtime/probe-result.txt", "evidence/outcome.json", "design.md"):
            path = self.target / artifact
            original = path.read_bytes()
            path.write_bytes(original + b"changed\n")
            for phase in ("modify", "commit", "publish", "live-external"):
                with self.subTest(artifact=artifact, phase=phase):
                    action = self.action(phase=phase, paths=["src/example.txt"] if phase == "modify" else [],
                                         effects=[] if phase == "modify" else ["selected-effect"])
                    value = review_request(self.target, self.brief_path, action)
                    self.assertEqual(value["status"], "request-review-required", value)
                    self.assertTrue(value["evidence_readiness"]["checkpoint_required"])
            path.write_bytes(original)
        self.assertEqual(review_request(self.target, self.brief_path, self.action())["status"], "request-consistent")

    def test_incomplete_verification_and_diagnostic_overflow_cannot_prove_independence(self):
        issues = []
        def missing(path, limit):
            raise ValueError("missing evidence")
        self.assertTrue(verify_artifacts(self.model, missing, issues=issues))
        self.assertTrue(evidence_readiness(self.model, issues)["global_review_required"])
        issues = [{"path": "evidence/outcome.json", "message": "changed"}] * 9
        value = evidence_readiness(self.model, issues)
        self.assertTrue(value["global_review_required"])
        self.assertEqual(len(value["diagnostics"]), 8)
        self.assertEqual(value["failure_count"], 9)

    def test_review_does_not_read_each_artifact_twice(self):
        from target_adapter_validation.context import TargetRepositoryView
        original = TargetRepositoryView.read_bytes_result
        reads = []
        def observe(view, path, **kwargs):
            if path.name == "outcome.json": reads.append(path)
            return original(view, path, **kwargs)
        with patch.object(TargetRepositoryView, "read_bytes_result", observe):
            value = review_request(self.target, self.brief_path, self.action())
        self.assertEqual(value["status"], "request-consistent", value)
        self.assertEqual(len(reads), 1)

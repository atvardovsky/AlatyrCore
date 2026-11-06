from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import request_brief as requests
from request_focus import focus_failures


class RequestFocusTests(unittest.TestCase):
    def setUp(self):
        from tests.test_request_brief import brief_fixture, action_fixture
        self.brief = brief_fixture("Deliver the requested result", "result")
        self.brief.update(schema_version=3, delivery_control=None,
                          focus_control="dependency-readiness")
        self.model = {"objective": self.brief["objective"], "proof_obligations": [
            {"id": key, "required": True, "status": status}
            for key, status in (("result", "open"), ("prerequisite", "passed"), ("unrelated", "open"))],
            "execution_dependencies": [
                {"obligation_id": "result", "requires": ["prerequisite"]},
                {"obligation_id": "prerequisite", "requires": []},
                {"obligation_id": "unrelated", "requires": []}]}
        self.action = action_fixture(obligation_ids=["result"])

    def check(self, **changes):
        raw = json.dumps(self.brief).encode()
        brief = requests.parse_brief(raw)
        action = requests.parse_action({**self.action, "brief_sha256": hashlib.sha256(raw).hexdigest(), **changes})
        failures = requests.action_failures(brief, action, self.model,
            request_id=brief["request_id"], task_id=brief["task_id"])
        return failures + focus_failures(brief, action, self.model, hashlib.sha256(raw).hexdigest())

    def test_general_domains_use_the_same_guard(self):
        for domain in ("Explain module ownership", "Preserve API idempotency", "Repair data lineage",
                       "Document the accepted architecture", "Diagnose a failed service"):
            with self.subTest(domain=domain):
                self.brief["objective"] = self.model["objective"] = domain
                self.brief["outcomes"][0].update(statement=domain,
                    rejection_case="An unrelated improvement cannot replace this result")
                self.assertEqual(self.check(), [])
                self.assertTrue(self.check(obligation_ids=["unrelated"]))

    def test_prerequisite_closure_includes_transitive_supporting_work(self):
        self.model["proof_obligations"].append({"id": "root", "required": True, "status": "open"})
        self.model["execution_dependencies"].append({"obligation_id": "root", "requires": []})
        self.model["execution_dependencies"][1]["requires"] = ["root"]
        self.model["proof_obligations"][1]["status"] = "open"
        self.assertEqual(self.check(obligation_ids=["root"]), [])
        self.assertTrue(any("ready" in row for row in self.check()))

    def test_waiting_and_blocked_mutations_do_not_block_inspection(self):
        for status in ("open", "blocked"):
            with self.subTest(status=status):
                self.model["proof_obligations"][1]["status"] = status
                self.assertTrue(any("ready" in row for row in self.check()))
                self.assertEqual(self.check(phase="inspect", paths=[]), [])
        self.model["proof_obligations"][1]["status"] = "passed"
        self.model["proof_obligations"][0]["status"] = "blocked"
        self.assertTrue(self.check())

    def test_unknown_unrelated_and_missing_obligations_are_rejected(self):
        for ids in (["missing-id"], ["unrelated"], ["result", "unrelated"]):
            with self.subTest(ids=ids): self.assertTrue(self.check(obligation_ids=ids))
        self.action.pop("obligation_ids")
        self.assertTrue(any("obligation_ids" in row for row in self.check()))
        self.assertEqual(self.check(kind="answer", phase="inspect", paths=[]), [])

    def test_stale_worker_binding_cannot_be_relabelled_by_current_task_ids(self):
        previous = hashlib.sha256(json.dumps(self.brief).encode()).hexdigest()
        self.brief["constraints"].append("Keep the newly clarified boundary")
        self.assertTrue(any("brief" in row for row in self.check(brief_sha256=previous)))
        self.assertEqual(self.check(), [])
        self.assertTrue(self.check(request_id="superseded"))
        self.assertTrue(self.check(task_id="different-task"))

    def test_every_action_kind_requires_its_original_digest(self):
        raw = json.dumps(self.brief).encode()
        for kind in ("work", "answer", "complete"):
            action = requests.parse_action({**self.action, "kind": kind, "phase": "inspect", "paths": []})
            self.assertTrue(any("brief_sha256" in row for row in focus_failures(
                self.brief, action, self.model, hashlib.sha256(raw).hexdigest())))
        self.action.pop("obligation_ids")
        self.assertEqual(self.check(kind="answer", phase="inspect", paths=[]), [])
        self.model["proof_obligations"][0]["status"] = "passed"
        self.assertEqual(self.check(kind="complete", phase="inspect", paths=[]), [])

    def test_dependency_control_requires_a_valid_explicit_mapping(self):
        for value in (None, [], [{"obligation_id": "result", "requires": ["result"]}]):
            with self.subTest(value=value):
                self.model["execution_dependencies"] = value
                self.assertTrue(self.check())
        self.model.pop("execution_dependencies")
        self.assertTrue(self.check())

    def test_readiness_preserves_shared_waived_prerequisites_and_failed_retry(self):
        self.model["proof_obligations"][1]["status"] = "waived"
        self.model["proof_obligations"][0]["status"] = "failed"
        self.assertEqual(self.check(), [])
        self.model["execution_dependencies"][2]["requires"] = ["prerequisite"]
        self.assertTrue(self.check(obligation_ids=["unrelated"]))
        self.model["proof_obligations"][0]["status"] = "open"
        self.model["execution_dependencies"][2]["requires"] = ["result"]
        self.assertTrue(self.check(obligation_ids=["unrelated"]))

    def test_live_work_uses_readiness_without_granting_authority(self):
        self.brief["authorized_phases"].append("live-external")
        self.brief["effect_scope"] = ["approved-observation"]
        self.assertEqual(self.check(phase="live-external", effects=["approved-observation"]), [])
        self.model["proof_obligations"][1]["status"] = "open"
        self.assertTrue(self.check(phase="live-external", effects=["approved-observation"]))

    def test_cross_domain_oracles_reject_convenient_substitutes(self):
        cases = (
            ("API retries", {"effects": 1}, {"effects": 2}, lambda row: row["effects"] == 1),
            ("Data repair", {"identity_proven": True}, {"identity_proven": False}, lambda row: row["identity_proven"]),
            ("Architecture explanation", {"decision": "accepted"}, {"decision": "observed"}, lambda row: row["decision"] == "accepted"),
            ("Documentation update", {"owner": "canonical"}, {"owner": "parallel-guide"}, lambda row: row["owner"] == "canonical"),
            ("Read-only diagnosis", {"causal_evidence": True}, {"causal_evidence": False}, lambda row: row["causal_evidence"]),
        )
        for name, original, substitute, oracle in cases:
            for observed, expected in ((original, False), (substitute, True)):
                with self.subTest(domain=name, observed=observed):
                    self.model["proof_obligations"][0]["status"] = "passed" if oracle(observed) else "failed"
                    # This fixture supplies an independent oracle, not semantic inference by Core.
                    self.assertEqual(bool(self.check(kind="complete", phase="inspect", paths=[])), expected)

    def test_settled_obligations_do_not_reopen_but_git_phases_keep_separate_authority(self):
        self.model["proof_obligations"][0]["status"] = "passed"
        self.assertTrue(self.check())
        for phase in ("commit", "publish", "live-external"):
            self.assertTrue(any("phase" in row for row in self.check(phase=phase, effects=["origin/main"])))
        self.brief["authorized_phases"].extend(["commit", "publish"])
        self.brief["effect_scope"] = ["origin/main"]
        for phase in ("commit", "publish"):
            self.assertEqual(self.check(phase=phase, effects=["origin/main"]), [])
            self.assertTrue(self.check(phase=phase, effects=["unapproved-destination"]))
        self.assertEqual(self.check(kind="complete", phase="inspect", paths=[]), [])
        self.model["proof_obligations"][0]["status"] = "waived"
        self.assertTrue(any("unverified" in row for row in self.check(kind="complete", phase="inspect", paths=[])))

    def test_malformed_optional_fields_fail_diagnostically(self):
        for value in ({}, [], None, True, 1, "unknown", "A" * 64, "0" * 63):
            with self.subTest(value=value), self.assertRaises(ValueError):
                requests.parse_action({**self.action, "brief_sha256": value})
        for value in ({}, None, True, ["result", "result"], [{}], []):
            with self.subTest(value=value), self.assertRaises(ValueError):
                requests.parse_action({**self.action, "obligation_ids": value})
        for value in ({}, [], True, 1, "unknown"):
            raw = json.dumps({**self.brief, "focus_control": value}).encode()
            with self.subTest(value=value), self.assertRaises(ValueError): requests.parse_brief(raw)

    def test_legacy_and_null_controls_require_no_dependency_graph_or_bindings(self):
        for version in (1, 2, 3):
            brief = copy.deepcopy(self.brief)
            brief["schema_version"] = version
            if version == 1: brief.pop("delivery_control")
            if version < 3: brief.pop("focus_control")
            else: brief["focus_control"] = None
            parsed = requests.parse_brief(json.dumps(brief).encode())
            action = requests.parse_action({key: value for key, value in self.action.items() if key != "obligation_ids"})
            with patch("request_focus.execution_readiness", side_effect=AssertionError("unadopted graph read")):
                self.assertEqual(focus_failures(parsed, action, {}, "0" * 64), [])
                self.assertTrue(focus_failures(parsed, {**action, "obligation_ids": ["result"]}, {}, "0" * 64))
            action["brief_sha256"] = "1" * 64
            self.assertTrue(focus_failures(parsed, action, {}, "0" * 64))

    def test_obligation_count_boundary_and_duplicate_selections(self):
        for size in (31, 32, 33):
            action = {**self.action, "obligation_ids": [f"proof-{index}" for index in range(size)]}
            if size <= 32: self.assertEqual(len(requests.parse_action(action)["obligation_ids"]), size)
            else:
                with self.assertRaises(ValueError): requests.parse_action(action)


if __name__ == "__main__":
    unittest.main()

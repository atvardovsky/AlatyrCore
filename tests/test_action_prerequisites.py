from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from tests.active_task_fixture import ActiveTaskFixture, ROOT
from tests.test_request_brief import action_fixture, brief_fixture

sys.path.insert(0, str(ROOT / "tools"))
from action_prerequisites import terminal_policy_digest, terminal_prerequisite_failures
from lifecycle_checkpoints import review_request
from request_brief import parse_brief
from target_adapter_validation.context import TargetRepositoryView


class TerminalPrerequisiteTests(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.candidate = self.put("evidence/candidate.json", {"revision": self.result, "tree": "selected source"})
        self.environment = self.put("evidence/environment.json", {"target": "isolated", "configuration": "verified"})
        output = self.put("evidence/verification.json", {"result": "passed", "observed": "exact candidate"})
        self.receipt = {"schema_version": 1, "record_kind": "alatyr-delivery-run-receipt",
            "request_id": "request-1", "task_id": "fixture-task", "command_id": "verify-previous-stage",
            "started_at": (self.now - timedelta(seconds=10)).isoformat(), "finished_at": self.now.isoformat(),
            "result": "passed", "exit_code": 0,
            "input_sha256": {row["path"]: row["sha256"] for row in (self.candidate, self.environment)},
            "result_artifact": output}
        binding = self.put("evidence/receipt.json", self.receipt)
        self.brief = brief_fixture(self.model["objective"], "proof-1")
        self.brief.update(schema_version=3, delivery_control=None, focus_control=None,
            authorized_phases=["inspect", "modify", "commit", "publish", "live-external"],
            effect_scope=["release:next", "release:independent"], terminal_control={"schema_version": 1, "rules": [
                {"id": "previous-stage", "phase": "publish", "effects": ["release:next"],
                 "proof_id": "proof-1", "command_id": "verify-previous-stage", "receipt": binding,
                 "candidate": self.candidate, "environment": self.environment, "max_age_seconds": 900}]})
        self.model["proof_obligations"][0].update(status="passed", evidence_refs=[binding["path"]])
        self.action = action_fixture(phase="publish", paths=[], effects=["release:next"])
        self.brief_path = ".ai/.runtime/terminal-request.json"
        self.save()

    def put(self, path, value):
        destination = self.target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(value), encoding="utf-8")
        return self.bind(destination)

    def save(self):
        self.write_model(); self.write_index()
        self.put(self.brief_path, self.brief)
        self.action["brief_sha256"] = hashlib.sha256((self.target / self.brief_path).read_bytes()).hexdigest()

    def save_receipt(self):
        self.brief["terminal_control"]["rules"][0]["receipt"] = self.put("evidence/receipt.json", self.receipt)
        self.save()

    def failures(self, *, now=None, action=None):
        brief = parse_brief(json.dumps(self.brief).encode())
        context = TargetRepositoryView(self.target)
        return terminal_prerequisite_failures(context, self.target, brief, action or self.action,
            self.model, {}, now=self.now.timestamp() if now is None else now)

    def delegate(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"),
            "lifecycle-checkpoint", "--target", str(self.target), "--framework-source", str(ROOT),
            "review", "--request-brief", self.brief_path], input=json.dumps(self.action),
            capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def test_valid_terminal_result_passes_registered_and_delegate_routes_without_authority(self):
        self.assertEqual(self.failures(), [])
        value = review_request(self.target, self.brief_path, self.action)
        self.assertEqual(value["status"], "request-consistent", value)
        self.assertFalse(value["authorization_granted"])
        self.assertFalse(value["acceptance_granted"])
        code, value = self.delegate()
        self.assertEqual(code, 0, value)
        self.assertFalse(value["native_interception_verified"])

    def test_running_failed_interrupted_and_inconsistent_results_block_publication(self):
        original = copy.deepcopy(self.receipt)
        for result, code in (("running", None), ("failed", 1), ("interrupted", None), ("passed", None),
                             ("passed", True), ("passed", 1), ({}, 0), ([], 0)):
            with self.subTest(result=result, code=code):
                self.receipt = {**original, "result": result, "exit_code": code}
                self.save_receipt()
                self.assertTrue(self.failures())
                value = review_request(self.target, self.brief_path, self.action)
                self.assertTrue(value["checkpoint_required"], value)
        self.receipt = {"session_id": 123, "output": "still running"}
        self.save_receipt()
        code, value = self.delegate()
        self.assertEqual(code, 1, value)
        self.assertIn("terminal prerequisite", value["reason"])

    def test_current_task_request_command_and_exact_context_bindings_are_required(self):
        original = copy.deepcopy(self.receipt)
        for field in ("task_id", "request_id", "command_id"):
            with self.subTest(field=field):
                self.receipt = {**original, field: "unrelated"}; self.save_receipt()
                self.assertTrue(self.failures())
        for binding in (self.candidate, self.environment):
            self.receipt = copy.deepcopy(original)
            self.receipt["input_sha256"][binding["path"]] = "0" * 64
            self.save_receipt()
            self.assertTrue(self.failures())

    def test_missing_and_changed_artifacts_fail_through_public_review(self):
        for path in ("evidence/receipt.json", "evidence/verification.json", self.candidate["path"], self.environment["path"]):
            source = self.target / path
            original = source.read_bytes()
            for mutation in ("changed", "missing"):
                with self.subTest(path=path, mutation=mutation):
                    if mutation == "changed": source.write_bytes(b"changed")
                    else: source.unlink()
                    value = review_request(self.target, self.brief_path, self.action)
                    self.assertTrue(value["checkpoint_required"], value)
                    source.write_bytes(original)
        self.assertEqual(self.failures(), [])

    def test_freshness_boundary_and_future_results(self):
        for age, valid in ((899, True), (900, True), (901, False), (-1, False)):
            with self.subTest(age=age):
                self.assertEqual(not self.failures(now=self.now.timestamp() + age), valid)

    def test_result_artifact_byte_ceiling(self):
        from analysis_evidence import MAX_ARTIFACT_BYTES
        path = self.target / self.receipt["result_artifact"]["path"]
        for size in (MAX_ARTIFACT_BYTES - 1, MAX_ARTIFACT_BYTES, MAX_ARTIFACT_BYTES + 1):
            with self.subTest(size=size):
                path.write_bytes(b"x" * size)
                self.receipt["result_artifact"] = self.bind(path); self.save_receipt()
                self.assertEqual(not self.failures(), size <= MAX_ARTIFACT_BYTES)

    def test_unpassed_waived_unknown_and_unassociated_proofs_do_not_qualify(self):
        for status in ("open", "failed", "blocked", "waived"):
            self.model["proof_obligations"][0]["status"] = status
            self.assertTrue(self.failures())
        self.model["proof_obligations"][0]["status"] = "passed"
        self.model["proof_obligations"][0]["evidence_refs"] = []
        self.assertTrue(self.failures())
        self.brief["terminal_control"]["rules"][0]["proof_id"] = "missing-proof"
        self.assertTrue(self.failures())

    def test_effect_selection_cannot_skip_rule_by_selecting_other_outcomes(self):
        self.receipt["result"] = "failed"; self.receipt["exit_code"] = 1; self.save_receipt()
        self.brief["outcomes"].append({**self.brief["outcomes"][0], "id": "supporting"})
        self.assertTrue(self.failures(action={**self.action, "outcome_ids": ["supporting"]}))
        self.assertEqual(self.failures(action={**self.action, "effects": ["release:independent"]}), [])
        self.assertEqual(self.failures(action={**self.action, "phase": "inspect", "effects": []}), [])

    def test_absent_null_and_inspection_paths_read_no_receipts(self):
        for control in (None, self.brief["terminal_control"]):
            self.brief["terminal_control"] = control
            with patch("action_prerequisites.read_bound", side_effect=AssertionError("unexpected read")):
                action = {**self.action, "phase": "inspect", "effects": []} if control else self.action
                self.assertEqual(self.failures(action=action), [])
        self.brief.pop("terminal_control")
        with patch("action_prerequisites.read_bound", side_effect=AssertionError("absent control read")):
            self.assertEqual(self.failures(), [])

    def test_malformed_rules_and_count_boundaries(self):
        original = copy.deepcopy(self.brief["terminal_control"])
        for field in ("id", "phase", "effects", "proof_id", "command_id", "receipt", "candidate", "environment", "max_age_seconds"):
            for value in ({}, [], None, True, 0, "unknown"):
                self.brief["terminal_control"] = copy.deepcopy(original)
                self.brief["terminal_control"]["rules"][0][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    parse_brief(json.dumps(self.brief).encode())
        for count in (0, 1, 16, 17):
            self.brief["terminal_control"] = {"schema_version": 1, "rules": [
                {**original["rules"][0], "id": f"rule-{index}"} for index in range(count)]}
            if 1 <= count <= 16: parse_brief(json.dumps(self.brief).encode())
            else:
                with self.assertRaises(ValueError): parse_brief(json.dumps(self.brief).encode())

    def test_policy_digest_allows_fresh_artifacts_not_silent_policy_removal(self):
        control = self.brief["terminal_control"]
        previous = terminal_policy_digest(control)
        control["rules"][0]["receipt"]["sha256"] = "0" * 64
        self.assertEqual(terminal_policy_digest(control), previous)
        control["rules"][0]["max_age_seconds"] += 1
        self.assertNotEqual(terminal_policy_digest(control), previous)
        self.assertIsNone(terminal_policy_digest(None))

    def test_stale_queued_action_does_not_follow_a_refreshed_candidate(self):
        old = dict(self.action)
        self.candidate = self.put("evidence/candidate.json", {"revision": "new exact source"})
        self.brief["terminal_control"]["rules"][0]["candidate"] = self.candidate
        self.receipt["input_sha256"][self.candidate["path"]] = self.candidate["sha256"]
        self.save_receipt()
        value = review_request(self.target, self.brief_path, old)
        self.assertTrue(value["checkpoint_required"], value)
        self.assertIn("brief digest", value["reason"])
        self.assertFalse(review_request(self.target, self.brief_path, self.action)["checkpoint_required"])
        omitted = {key: value for key, value in self.action.items() if key != "brief_sha256"}
        self.assertTrue(review_request(self.target, self.brief_path, omitted)["checkpoint_required"])

    def test_append_only_retry_can_select_a_new_receipt_path(self):
        before = terminal_policy_digest(self.brief["terminal_control"])
        old_bytes = (self.target / "evidence/receipt.json").read_bytes()
        self.brief["terminal_control"]["rules"][0]["receipt"] = self.put("evidence/retry.json", self.receipt)
        self.model["proof_obligations"][0]["evidence_refs"].append("evidence/retry.json")
        self.save()
        self.assertEqual(terminal_policy_digest(self.brief["terminal_control"]), before)
        self.assertEqual((self.target / "evidence/receipt.json").read_bytes(), old_bytes)
        self.assertEqual(self.failures(), [])

    def test_expiry_during_artifact_verification_does_not_pass(self):
        from action_prerequisites import read_bound
        clock = [self.now.timestamp()]
        def delayed(*args, **kwargs):
            result = read_bound(*args, **kwargs)
            if args[2]["path"] == "evidence/verification.json":
                clock[0] += 901
            return result
        with patch("action_prerequisites.time.time", side_effect=lambda: clock[0]), \
                patch("action_prerequisites.read_bound", side_effect=delayed):
            value = review_request(self.target, self.brief_path, self.action)
        self.assertTrue(value["checkpoint_required"], value)
        self.assertIn("expired", value["reason"])

    def test_all_mutating_effect_phases_use_terminal_rules(self):
        for phase in ("commit", "publish", "live-external"):
            self.brief["terminal_control"]["rules"][0]["phase"] = phase
            self.action["phase"] = phase; self.save_receipt()
            self.assertFalse(review_request(self.target, self.brief_path, self.action)["checkpoint_required"])
            self.receipt["result"] = "failed"; self.receipt["exit_code"] = 1; self.save_receipt()
            self.assertTrue(review_request(self.target, self.brief_path, self.action)["checkpoint_required"])
            self.receipt["result"] = "passed"; self.receipt["exit_code"] = 0

    def setup_checkpoint(self):
        import lifecycle_checkpoints as hooks
        from inspect_session_context import TARGET_ANCHORS
        from tests.test_target_validator_installation_state import write_state, write_accepted_record
        for name in TARGET_ANCHORS:
            path = self.target / name
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b"{}\n")
        write_state(self.target, "accepted"); write_accepted_record(self.target)
        policy = json.loads((ROOT / "templates/target" / hooks.POLICY).read_bytes())
        policy.update(enabled=True, provider="procedural")
        policy["request_guard"] = {"required": True, "file_tools": []}
        self.put(hooks.POLICY, policy)
        request = hooks.handle(self.target, "procedural", "request", {"session_id": "terminal-fixture"})
        self.brief["request_id"] = self.receipt["request_id"] = request["request_id"]
        self.action["request_id"] = request["request_id"]
        self.save_receipt()
        self.recapture()
        return self.bind_checkpoint()

    def recapture(self, omit=()):
        import lifecycle_checkpoints as hooks
        from inspect_session_context import capture
        selected = hooks.selected_task(self.target, "fixture-task", request_review=True)
        paths = {*selected["checkpoint_inputs"], hooks.POLICY, self.brief_path,
                 self.candidate["path"], self.environment["path"], self.receipt["result_artifact"]["path"],
                 self.brief["terminal_control"]["rules"][0]["receipt"]["path"]} if self.brief.get("terminal_control") else {
                     *selected["checkpoint_inputs"], hooks.POLICY, self.brief_path}
        self.put(".ai/.runtime/terminal-baseline.json", capture(self.target, sorted(paths - set(omit)))[0])

    def bind_checkpoint(self):
        import lifecycle_checkpoints as hooks
        return hooks.handle(self.target, "procedural", "before-action", {"session_id": "terminal-fixture"},
            bind={"request_id": self.brief["request_id"], "task_id": "fixture-task",
                  "baseline": ".ai/.runtime/terminal-baseline.json", "request_brief": self.brief_path})

    def test_bound_checkpoint_requires_all_terminal_inputs_and_blocks_policy_drop(self):
        import lifecycle_checkpoints as hooks
        self.assertEqual(self.setup_checkpoint()["status"], "bound")
        payload = {"session_id": "terminal-fixture", "alatyr_action": self.action}
        self.assertFalse(hooks.handle(self.target, "procedural", "before-action", payload)["checkpoint_required"])
        self.recapture(omit=[self.environment["path"]]); self.bind_checkpoint()
        self.assertTrue(hooks.handle(self.target, "procedural", "before-action", payload)["checkpoint_required"])
        self.brief["terminal_control"] = None; self.save(); self.recapture()
        with self.assertRaisesRegex(ValueError, "cannot drop"):
            self.bind_checkpoint()

    def test_bound_checkpoint_accepts_append_only_retry_and_rejects_old_dispatch(self):
        import lifecycle_checkpoints as hooks
        self.setup_checkpoint()
        previous = dict(self.action)
        previous_policy = terminal_policy_digest(self.brief["terminal_control"])
        receipt = self.put("evidence/second-run.json", self.receipt)
        self.brief["terminal_control"]["rules"][0]["receipt"] = receipt
        self.model["proof_obligations"][0]["evidence_refs"].append(receipt["path"])
        self.save(); self.recapture()
        self.assertEqual(terminal_policy_digest(self.brief["terminal_control"]), previous_policy)
        self.assertEqual(self.bind_checkpoint()["status"], "bound")
        for action, blocked in ((self.action, False), (previous, True)):
            result = hooks.handle(self.target, "procedural", "before-action",
                {"session_id": "terminal-fixture", "alatyr_action": action})
            self.assertEqual(result["checkpoint_required"], blocked, result)

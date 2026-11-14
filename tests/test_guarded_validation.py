from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from tests.test_request_brief import RequestLifecycleFixture, delivery_fixture, validation_fixture
from tests.test_test_execution_contract import policy as testing_policy, record as execution_record

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import lifecycle_checkpoints as hooks
from guarded_validation import POLICY, run_validation
from inspect_session_context import capture
from lifecycle_policy import enforcement_status


class GuardedValidationTests(RequestLifecycleFixture):
    def setUp(self):
        super().setUp()
        self.history = delivery_fixture(self.brief)
        self.testing = testing_policy()
        self.testing["commands"][0]["argv"] = [sys.executable, "-c",
            "from pathlib import Path; Path('child-started.txt').write_text('selected check ran')"]
        self.testing["commands"][0]["execution"]["suite_scope"] = "selected"
        self.record_path = ".ai/.runtime/pre-run.json"
        self.record = execution_record()
        self.record.update(state="authored", claim="none", result_artifact=None,
            repository_revision=self.result, authorization_source=self.brief["source_ref"],
            counts={"discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0})
        self.record["files"]["executed"] = []
        self.put("tests/a.py", b"# selected synthetic fixture\n")
        self.put("test.cfg", b"synthetic config\n")
        self.record["input_sha256"] = {p: hashlib.sha256((self.target / p).read_bytes()).hexdigest()
                                      for p in ("tests/a.py", "test.cfg")}
        self.validation = validation_fixture(command_id="unit", execution_evidence=self.record_path)
        self.current_action = self.action(phase="inspect", paths=[], validation=self.validation)
        self.prepare()

    def put(self, path, data):
        target = self.target / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())

    def prepare(self):
        self.put(POLICY, self.testing)
        self.record["policy_sha256"] = hashlib.sha256((self.target / POLICY).read_bytes()).hexdigest()
        self.put(self.record_path, self.record)
        self.put(self.brief["delivery_control"]["validation_history"], self.history)
        self.write_brief()
        selected = hooks.selected_task(self.target, "fixture-task", request_review=True)
        paths = set(selected["checkpoint_inputs"]) | {hooks.POLICY, self.brief_path, POLICY,
            self.record_path, self.brief["delivery_control"]["validation_history"], "test.cfg", "tests/a.py"}
        self.put(self.baseline, capture(self.target, sorted(paths))[0])
        self.assertEqual(self.bind_request()["status"], "bound")

    def launch(self, argv=None, delegate=False):
        entry = ROOT / ("templates/target/.ai/assistant/tools/alatyr_delegate.py" if delegate else "tools/alatyr.py")
        command = [sys.executable, "-B", str(entry), "lifecycle-checkpoint", "--target", str(self.target)]
        if delegate:
            command += ["--framework-source", str(ROOT)]
        command += ["run-validation", "--", *(self.testing["commands"][0]["argv"] if argv is None else argv)]
        result = subprocess.run(command, input=json.dumps({"session_id": "request-fixture", "alatyr_action": self.current_action}),
                                capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def test_actual_cli_and_installed_delegate_launch_only_the_registered_child(self):
        for delegate in (False, True):
            with self.subTest(delegate=delegate):
                code, result = self.launch(delegate=delegate)
                self.assertEqual(code, 0, result)
                self.assertTrue(result["command_started"])
                self.assertFalse(result["acceptance_granted"])
                self.assertFalse(result["authorization_granted"])
                self.assertEqual((self.target / "child-started.txt").read_text(), "selected check ran")

    def test_missing_permission_wrong_timing_and_unavailable_prerequisites_never_launch(self):
        original = copy.deepcopy(self.record)
        for key, value in (("authorization", "not-authorized"), ("authorization", "awaiting-review"),
                           ("timing_disposition", "not-run"), ("availability", "unavailable"),
                           ("prerequisites_satisfied", False), ("authorization_source", "previous request")):
            self.record = {**original, key: value}; self.prepare()
            code, result = self.launch()
            self.assertNotEqual(code, 0, result)
            self.assertFalse(result.get("command_started"), result)
            self.assertFalse((self.target / "child-started.txt").exists())

    def test_argument_changes_echo_and_disabled_delivery_cannot_bypass_the_guard(self):
        for argv in (["echo", "unit"], self.testing["commands"][0]["argv"] + ["--extra"], []):
            code, result = self.launch(argv)
            self.assertNotEqual(code, 0, result)
            self.assertFalse((self.target / "child-started.txt").exists())
        self.policy["enabled"] = False; self.write_policy()
        code, result = self.launch()
        self.assertNotEqual(code, 0)
        self.assertFalse(result["command_started"])

    def test_stale_inputs_revision_and_policy_fail_closed(self):
        original = copy.deepcopy(self.record)
        for key, value in (("repository_revision", "0" * 40), ("policy_sha256", "0" * 64)):
            self.record = copy.deepcopy(original); self.prepare()
            self.record[key] = value; self.put(self.record_path, self.record)
            code, result = self.launch()
            self.assertNotEqual(code, 0, result)
            self.assertFalse((self.target / "child-started.txt").exists())
        self.record = original; self.prepare()
        self.put("tests/a.py", b"changed after approval")
        self.assertNotEqual(self.launch()[0], 0)
        self.assertFalse((self.target / "child-started.txt").exists())

    def test_retry_requires_diagnosis_and_full_suite_cannot_consume_focused_budget(self):
        self.history["attempts"] = [{"evidence_ref": "first-failure.json", "result": "failed", "scope": "focused",
            "duration_seconds": 1, "expected_red_proof_id": None}]
        self.prepare()
        self.assertNotEqual(self.launch()[0], 0)
        self.history["attempts"] = []
        self.testing["commands"][0]["execution"]["suite_scope"] = "full"; self.prepare()
        self.assertNotEqual(self.launch()[0], 0)
        self.assertFalse((self.target / "child-started.txt").exists())

    def test_malformed_authority_and_argv_have_diagnostics_not_crashes(self):
        original = copy.deepcopy(self.record)
        for bad in ({}, [], None, True, 1, "unknown"):
            self.record = {**original, "authorization": bad}; self.prepare()
            code, result = self.launch()
            self.assertNotEqual(code, 0, result)
            self.assertNotIn("Traceback", str(result))

    def test_changed_inputs_after_child_keep_the_attempt_visible_without_acceptance(self):
        def child(argv, **options):
            self.put("tests/a.py", b"changed by the child")
            return subprocess.CompletedProcess(argv, 0)
        result = run_validation(self.target, "procedural",
            {"session_id": "request-fixture", "alatyr_action": self.current_action},
            self.testing["commands"][0]["argv"], runner=child)
        self.assertEqual(result["status"], "execution-unverified")
        self.assertTrue(result["command_started"])
        self.assertTrue(result["checkpoint_required"])

    def test_guard_status_does_not_equate_configuration_with_interception(self):
        self.assertEqual(enforcement_status(None)["state"], "absent")
        self.assertEqual(enforcement_status(b"{}")["state"], "invalid")
        for enabled, provider, mode, expected in ((False, "procedural", "observe", "disabled"),
                (True, "procedural", "observe", "procedural-only"), (True, "codex", "observe", "observe-only"),
                (True, "codex", "checkpoint", "checkpoint-unverified")):
            raw = json.dumps({**self.policy, "enabled": enabled, "provider": provider, "mode": mode}).encode()
            status = enforcement_status(raw)
            self.assertEqual(status["state"], expected)
            self.assertFalse(status["native_interception_verified"])

    def test_authorized_static_check_is_not_blocked_by_product_review_timing(self):
        self.testing["commands"][0]["execution"].update(kind="static-analysis", proof_boundary="static-metadata")
        self.record.update(proof_boundary="static-metadata", timing_disposition="not-run")
        self.prepare()
        code, result = self.launch()
        self.assertEqual(code, 0, result)
        self.assertTrue(result["command_started"])

    def test_external_effects_cannot_be_authorized_by_a_test_record(self):
        self.testing["commands"][0]["execution"]["environment"] = "external"
        self.record["environment"] = "external"
        self.prepare()
        code, result = self.launch()
        self.assertNotEqual(code, 0, result)
        self.assertIn("separately authorized", result["reason"])
        self.assertFalse((self.target / "child-started.txt").exists())

    def test_malformed_registered_argument_vectors_are_rejected_before_launch(self):
        from lifecycle_checkpoints import review_request
        for bad in ({}, [], None, True, [1], ["echo", "bad\0argument"]):
            self.testing["commands"][0]["argv"] = bad
            self.prepare()
            result = review_request(self.target, self.brief_path, self.current_action)
            self.assertTrue(result["checkpoint_required"], result)
            self.assertFalse((self.target / "child-started.txt").exists())

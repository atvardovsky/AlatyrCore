from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.test_request_brief import RequestLifecycleFixture, delivery_fixture, validation_fixture
from tests.test_test_execution_contract import policy as testing_policy, record as execution_record

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import lifecycle_checkpoints as hooks
from guarded_validation import POLICY, run_validation
from inspect_session_context import capture
from lifecycle_policy import enforcement_status
from validation_lane_policy import POLICY as LANES


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
        paths.update(getattr(self, "additional_context", []))
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
                self.assertFalse((self.target / ".git/alatyr-validation-lanes").exists())

    def opt_in_lane(self, observed=("case-a", "case-b"), cleanup="passed", artifact=False):
        command = self.testing["commands"][0]
        command["execution"]["prerequisites"].append("alatyr:validation-lane:proof")
        preflight = copy.deepcopy(command)
        preflight["id"] = "discover"
        preflight["execution"].update(kind="metadata-check", proof_boundary="static-metadata",
                                      environment="none", effects=[], resources=[], prerequisites=[])
        preflight["argv"] = [sys.executable, "-c", f"print({json.dumps({'schema_version': 1, 'cases': observed})!r})"]
        self.testing["commands"].append(preflight)
        if artifact:
            self.testing["execution_contract"]["schema_version"] = 4
            self.record["schema_version"] = 4
            command["execution"].update(kind="static-analysis", proof_boundary="static-metadata",
                                        harness_inputs=["test.cfg"])
            self.record.update(proof_boundary="static-metadata", timing_disposition="not-run")
            command["argv"] = [sys.executable, "-c",
                "from pathlib import Path; Path('build-receipt.json').write_text('built'); "
                "Path('standalone-output.txt').write_text('real artifact')"]
            expected = []
            verifier = copy.deepcopy(preflight)
            verifier["id"] = "verify-artifact"
            verifier["argv"] = [sys.executable, "-c",
                "from pathlib import Path; import json; assert Path('build-receipt.json').read_text() == 'built'; "
                "assert Path('standalone-output.txt').read_text() == 'real artifact'; "
                "print(json.dumps({'schema_version':1,'cases':[]}))"]
            self.testing["commands"].append(verifier)
        else:
            expected = ["case-a", "case-b"]
            output = {"schema_version": 1, "cases": {case: "passed" for case in expected}, "cleanup": cleanup}
            command["argv"] = [sys.executable, "-c",
                "import os; from pathlib import Path; Path('child-started.txt').write_text('started'); "
                f"Path(os.environ['ALATYR_VALIDATION_CASE_RESULT']).write_text({json.dumps(output)!r})"]
        entries = {"unit": {"probe": "discover", "expected_cases": expected, "material_inputs": {"inputs": "test.cfg"},
                            "artifact": {"receipt": "build-receipt.json", "verifier": "verify-artifact"} if artifact else None}}
        self.lane_policy = {"schema_version": 1, "objectives": {"proof": {"max_attempts": 2, "max_seconds": 100,
                                                                          "commands": entries}}}
        self.put(LANES, self.lane_policy)
        self.additional_context = [LANES]
        self.prepare()

    def test_case_discovery_failure_does_not_start_setup_or_child(self):
        self.opt_in_lane(observed=("case-a",))
        code, result = self.launch(delegate=True)
        self.assertNotEqual(code, 0, result)
        self.assertEqual(result["status"], "discovery-failed")
        self.assertIn("exact approved case selection", result["reason"])
        self.assertFalse((self.target / "child-started.txt").exists())
        code, repeat = self.launch()
        self.assertNotEqual(code, 0, repeat)
        self.assertEqual(repeat["previous_attempt"], result["attempt_id"])

    def test_cleanup_failure_retains_passing_cases_without_claiming_success(self):
        self.opt_in_lane(cleanup="failed")
        code, result = self.launch()
        self.assertNotEqual(code, 0, result)
        self.assertTrue(result["command_started"])
        self.assertEqual(result["status"], "cleanup-failed")
        self.assertEqual(result["case_counts"], {"passed": 2, "failed": 0, "not-run": 0})
        self.assertFalse(result["acceptance_granted"])
        artifact = self.target / ".git/alatyr-validation-lanes" / (result["attempt_id"] + ".cases.json")
        self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(), result["case_sha256"])

    def test_missing_case_result_and_changed_inputs_cannot_pass_with_zero_exit(self):
        self.opt_in_lane()
        payload = {"session_id": "request-fixture", "alatyr_action": self.current_action}
        argv = self.testing["commands"][0]["argv"]
        def mutate(*args, **options):
            self.put("tests/a.py", b"changed after the child started")
            return subprocess.CompletedProcess(argv, 0)
        result = run_validation(self.target, "procedural", payload, argv, runner=mutate)
        self.assertTrue(result["command_started"])
        self.assertTrue(result["checkpoint_required"])
        self.assertIn(result["status"], {"unverified", "execution-unverified"})
        self.assertNotIn("case_counts", result)

    def test_build_artifact_reuse_bypasses_only_the_equivalent_build(self):
        self.opt_in_lane(observed=(), artifact=True)
        code, before = self.launch()
        self.assertEqual(code, 0, before)
        self.assertEqual(before["status"], "command-finished")
        self.assertEqual(before["artifact"]["path"], "build-receipt.json")
        code, reused = self.launch(delegate=True)
        self.assertEqual(code, 0, reused)
        self.assertEqual(reused["status"], "artifact-available")
        self.assertEqual(reused["artifact"], before["artifact"])
        self.assertFalse(reused["command_started"])
        self.assertFalse(reused["tests_reused"])
        self.assertFalse(reused["acceptance_granted"])
        self.assertNotIn("lane", reused["validation_command"])
        self.put("standalone-output.txt", b"changed without changing its receipt")
        code, stale = self.launch()
        self.assertNotEqual(code, 0, stale)
        self.assertIn("verification failed", stale["reason"])
        self.assertFalse(stale["command_started"])
        self.put("build-receipt.json", b"changed")
        code, stale = self.launch()
        self.assertNotEqual(code, 0, stale)
        self.assertFalse(stale["command_started"])

    def test_probe_cannot_use_a_mutating_registered_command(self):
        self.opt_in_lane()
        execution = self.testing["commands"][1]["execution"]
        execution["effects"] = ["temporary-files"]
        execution["resources"] = self.testing["commands"][0]["execution"]["resources"]
        self.prepare()
        code, result = self.launch()
        self.assertNotEqual(code, 0, result)
        self.assertIn("read-only metadata", result["reason"])
        self.assertFalse((self.target / "child-started.txt").exists())

    def test_wrapper_and_worktree_rotation_preserve_the_same_attempt_and_caps(self):
        from validation_lane import run_lane
        from lifecycle_checkpoints import review_request

        self.opt_in_lane(observed=("case-a",))
        code, result = self.launch()
        self.assertNotEqual(code, 0, result)
        self.assertEqual(result["status"], "discovery-failed")
        self.addCleanup(lambda: subprocess.run(["git", "worktree", "remove", str(sibling)],
                                               cwd=self.target, capture_output=True))
        sibling = self.target / "linked-worktree"
        subprocess.run(["git", "worktree", "add", "--detach", str(sibling), "HEAD"],
                       cwd=self.target, check=True, capture_output=True)
        selected = review_request(self.target, self.brief_path, self.current_action)["validation_command"]["lane"]
        def child(*args, **kwargs):
            self.fail("wrapper rotation must not launch a child")
        changed = {**selected, "retry": {"previous_attempt": result["attempt_id"], "reason": "changed-input"}}
        blocked = run_lane(sibling, changed, ["renamed-wrapper"], {}, lambda: None, lambda: None, child)
        self.assertIn("different material", blocked["reason"])
        self.assertEqual(blocked["previous_attempt"], result["attempt_id"])
        self.assertFalse(blocked["command_started"])

    def test_lane_budget_boundary_and_unresolved_child(self):
        from validation_lane import run_lane
        from local_file_lock import file_lock

        self.opt_in_lane()
        from lifecycle_checkpoints import review_request
        lane = review_request(self.target, self.brief_path, self.current_action)["validation_command"]["lane"]
        lane.update(limits=(1, 10), estimate=10)
        seen = []
        def timeout(argv, **kwargs):
            seen.append(kwargs["timeout"])
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        def launch(plan):
            return run_lane(self.target, plan, ["exact-child"], {}, lambda: None, lambda: None, timeout)
        first = launch(lane)
        self.assertEqual(first["status"], "unverified", first)
        self.assertTrue(first["command_started"])
        self.assertTrue(0 < seen[0] <= 10)
        plan = {**lane, "limits": (32, 86400),
                "retry": {"previous_attempt": first["attempt_id"], "reason": "execution-repair",
                          "cleanup_confirmed": False}}
        self.assertIn("unresolved", launch(plan)["reason"])
        plan["retry"]["cleanup_confirmed"] = True
        self.assertIn("budget exhausted", launch(plan)["reason"])
        hub = self.target / ".git/alatyr-validation-lanes"
        with file_lock(hub / "heavy.lock"):
            self.assertIn("lock timed out", launch({**lane, "objective": "other"})["reason"])
        self.assertEqual(len(seen), 1)

    def test_required_retry_binds_the_real_attempt_and_changed_condition(self):
        self.opt_in_lane(observed=("case-a",))
        code, first = self.launch()
        self.assertNotEqual(code, 0, first)
        changed_path = ".ai/.runtime/repair-condition.json"
        retry = ".ai/.runtime/lane-retry.json"
        self.put(changed_path, {"repair": "use the registered runner that collects both cases"})
        self.put(retry, {"previous_attempt": first["attempt_id"], "reason": "execution-repair",
                         "condition": "replaced the broken discovery configuration",
                         "condition_input": {"path": changed_path,
                             "sha256": hashlib.sha256((self.target / changed_path).read_bytes()).hexdigest()},
                         "cleanup_confirmed": True})
        self.additional_context.extend([retry, changed_path])
        self.validation.update(lane_retry=retry, diagnosis_proof_id="diagnosis")
        self.testing["commands"][1]["argv"][-1] = "print('{\"schema_version\":1,\"cases\":[\"case-a\",\"case-b\"]}')"
        self.model["proof_obligations"].append({"id": "diagnosis", "statement": "Check the repaired discovery runner",
            "required": True, "status": "passed", "evidence_owner": "primary", "acceptance_owner": "primary",
            "evidence_refs": [retry, changed_path], "waiver": None})
        self.write_model()
        self.write_index()
        self.prepare()
        code, result = self.launch(delegate=True)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["case_counts"], {"passed": 2, "failed": 0, "not-run": 0})
        self.assertNotEqual(result["attempt_id"], first["attempt_id"])
        code, stale = self.launch()
        self.assertNotEqual(code, 0, stale)
        self.assertEqual(stale["previous_attempt"], result["attempt_id"])

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

    def test_registered_launch_rechecks_the_current_team_record_after_binding(self):
        self.put(".ai/assistant/team/tasks/context-index.json", {"entries": []})
        self.put(".ai/assistant/team/tasks/arbitrary-filename.json",
                 {"id": "fixture-task", "status": "blocked", "blockers": ["Owner stopped testing"]})
        code, result = self.launch()
        self.assertNotEqual(code, 0, result)
        self.assertFalse(result["command_started"])
        self.assertEqual(result["reason"], "task-not-runnable")
        self.assertFalse((self.target / "child-started.txt").exists())

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

    def test_harness_prerequisite_blocks_actual_child_without_a_current_passed_receipt(self):
        def bound(path, value):
            self.put(path, value)
            return {"path": path, "sha256": hashlib.sha256((self.target / path).read_bytes()).hexdigest()}
        now = datetime.now(timezone.utc)
        candidate = bound("prerequisite/candidate.json", {"inputs": self.record["input_sha256"]})
        environment = bound("prerequisite/environment.json", {"kind": "disposable"})
        output = bound("prerequisite/result.json", {"native_syntax": "passed"})
        receipt = {"schema_version": 1, "record_kind": "alatyr-delivery-run-receipt",
            "request_id": self.brief["request_id"], "task_id": self.brief["task_id"], "command_id": "native-syntax",
            "started_at": (now - timedelta(seconds=2)).isoformat(), "finished_at": now.isoformat(),
            "result": "passed", "exit_code": 0, "input_sha256": {r["path"]: r["sha256"] for r in (candidate, environment)},
            "result_artifact": output}
        evidence = bound("prerequisite/receipt.json", receipt)
        proof = self.model["proof_obligations"][0]
        proof.update(status="passed", evidence_refs=[evidence["path"]])
        self.write_model(); self.write_index()
        self.brief.update(schema_version=3, focus_control=None, terminal_control={"schema_version": 1, "rules": [
            {"id": "syntax-before-browser", "phase": "validation", "validation_command_id": "unit", "effects": [],
             "proof_id": proof["id"], "command_id": "native-syntax", "receipt": evidence,
             "candidate": candidate, "environment": environment, "max_age_seconds": 900}]})
        self.additional_context = [r["path"] for r in (candidate, environment, output, evidence)]
        self.prepare()
        code, result = self.launch(delegate=True)
        self.assertEqual(code, 0, result)
        (self.target / "child-started.txt").unlink()
        receipt.update(result="failed", exit_code=1)
        self.brief["terminal_control"]["rules"][0]["receipt"] = bound("prerequisite/receipt.json", receipt)
        self.prepare()
        code, result = self.launch(delegate=True)
        self.assertNotEqual(code, 0, result)
        self.assertFalse((self.target / "child-started.txt").exists())
        self.assertIn("terminal prerequisite", result["reason"])

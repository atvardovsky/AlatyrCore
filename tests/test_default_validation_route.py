"""Actual default-route evidence stays separate from canonical acceptance."""
import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from tests.active_task_fixture import ActiveTaskFixture
import tests.test_test_execution_contract as execution_fixtures
from check_change_packages import changed_index_validator
from target_adapter_validation.harness_scenarios.common import parse_manifest
from target_adapter_validation.validation_contract import validate_validation_contract
from verify_target_upgrade import acceptance_failures
import tests.test_verify_target_upgrade as upgrade_fixtures


class DefaultValidationRouteTests(ActiveTaskFixture):
    def configure(self):
        helper = execution_fixtures.RegisteredTestingExecutionTests()
        self.policy, self.run = helper.fixture(self.target)
        self.contract = json.loads((ROOT / "templates/target/.ai/assistant/validation-contract.json").read_text())
        helper.write(self.target, ".ai/assistant/tools/alatyr_delegate.py",
                     (ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py").read_text())
        helper.write(self.target, ".ai/alatyr.yaml", 'framework:\n  version: "0.1.0-alpha.123"\n  source_commit: "' + self.result + '"\n')
        self.route = {"command_id": "unit", "argv": [sys.executable, "checks.py"],
                      "input_paths": ["checks.py"], "execution_record": "default-run.json"}
        self.policy["commands"][0]["argv"] = self.route["argv"]
        helper.write(self.target, ".ai/project/testing/test-first-policy.json", json.dumps(self.policy))
        self.run["policy_sha256"] = hashlib.sha256((self.target / ".ai/project/testing/test-first-policy.json").read_bytes()).hexdigest()
        self.contract["default_route"] = self.route
        helper.write(self.target, ".ai/assistant/validation-contract.json", json.dumps(self.contract))
        helper.write(self.target, "checks.py", 'print("actual default check")\n')
        started = datetime.now(timezone.utc).isoformat()
        command = subprocess.run(self.route["argv"], cwd=self.target, capture_output=True, text=True)
        finished = datetime.now(timezone.utc).isoformat()
        self.assertEqual(command.returncode, 0)
        self.observation = {"argv": self.route["argv"], "cwd": ".", "task_id": "fixture-task", "task_class": "standard-task",
            "framework_version": "0.1.0-alpha.123", "framework_source_commit": self.result,
            "injected_overrides": False, "exit_code": command.returncode,
            "run_window": {"started_at": started, "finished_at": finished}}
        self.run["repository_revision"] = self.result
        self.run["input_sha256"] = {p.relative_to(self.target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in self.target.rglob("*") if p.is_file() and ".git" not in p.relative_to(self.target).parts
            and p.name not in {"result.txt", "default-run.json"}}
        self.save()

    def save(self):
        (self.target / "result.txt").write_text(json.dumps(self.observation))
        self.run["result_artifact"] = {"path": "result.txt", "sha256": hashlib.sha256((self.target / "result.txt").read_bytes()).hexdigest()}
        (self.target / "default-run.json").write_text(json.dumps(self.run))

    def validate(self, selected=True):
        checked = changed_index_validator(self.target)
        checked.current_task_id = "fixture-task" if selected else None
        checked.current_task_class = "standard-task" if selected else None
        validate_validation_contract(checked, parse_manifest(self.target / ".ai/alatyr.yaml"))
        return checked

    def test_real_default_command_passes_and_no_selection_is_explicit_not_verified(self):
        self.configure()
        checked = self.validate()
        self.assertNotIn("DEFAULT_ROUTE_EVIDENCE", self.errors(checked), [x.message for x in checked.findings])
        self.assertIn("DEFAULT_ROUTE_VERIFIED", {x.code for x in checked.findings})
        unselected = self.validate(False)
        self.assertIn("DEFAULT_ROUTE_NOT_SELECTED", {x.code for x in unselected.findings})
        self.assertNotIn("DEFAULT_ROUTE_VERIFIED", {x.code for x in unselected.findings})

    def test_unadopted_route_does_not_load_execution_records(self):
        self.configure()
        self.contract.pop("default_route")
        (self.target / ".ai/assistant/validation-contract.json").write_text(json.dumps(self.contract))
        with patch("default_validation_route.validate_default_route", side_effect=AssertionError("unadopted route expanded")):
            checked = self.validate()
        self.assertNotIn("DEFAULT_ROUTE_VERIFIED", {x.code for x in checked.findings})

    def test_override_substitution_wrong_task_failure_and_missing_window_reject(self):
        self.configure()
        original = copy.deepcopy(self.observation)
        for key, bad in (("injected_overrides", True), ("argv", ["echo", "passed"]),
                         ("cwd", "elsewhere"), ("task_id", "other-task"), ("task_class", "small-task"),
                         ("framework_source_commit", "f" * 40), ("exit_code", 1),
                         ("exit_code", False), ("run_window", {"complete": True})):
            self.observation = dict(original, **{key: bad}); self.save()
            self.assertIn("DEFAULT_ROUTE_EVIDENCE", self.errors(self.validate()), (key, bad))

    def test_declaration_cannot_substitute_another_command_for_the_canonical_argv(self):
        self.configure()
        self.contract["default_route"]["argv"] = ["echo", "not-validation"]
        (self.target / ".ai/assistant/validation-contract.json").write_text(json.dumps(self.contract))
        self.observation["argv"] = self.contract["default_route"]["argv"]
        self.run["input_sha256"][".ai/assistant/validation-contract.json"] = hashlib.sha256((self.target / ".ai/assistant/validation-contract.json").read_bytes()).hexdigest()
        self.save()
        checked = self.validate()
        self.assertTrue(any("canonical execution command" in x.message for x in checked.findings))

    def test_stale_input_missing_record_and_malformed_policy_do_not_pass_or_crash(self):
        self.configure()
        (self.target / "checks.py").write_text("changed default wrapper\n")
        self.assertIn("DEFAULT_ROUTE_EVIDENCE", self.errors(self.validate()))
        (self.target / "default-run.json").unlink()
        self.assertIn("DEFAULT_ROUTE_EVIDENCE", self.errors(self.validate()))
        self.save()
        policy_path = self.target / ".ai/project/testing/test-first-policy.json"
        for value in ({"commands": True}, {"commands": [None]}, {}, []):
            policy_path.write_text(json.dumps(value))
            self.assertTrue(any(x.code.startswith("DEFAULT_ROUTE") for x in self.validate().findings if x.level == "error"))

    def test_observation_json_is_unambiguous_and_malformed_fields_never_crash(self):
        self.configure()
        original = copy.deepcopy(self.observation)
        for key in original:
            for bad in ({}, [], None, True, 3, "unknown"):
                if bad == original[key] and type(bad) is type(original[key]):
                    continue
                self.observation = dict(original, **{key: bad}); self.save()
                self.assertIn("DEFAULT_ROUTE_EVIDENCE", self.errors(self.validate()), (key, bad))
        for raw in ('{"exit_code":0,"exit_code":1}', '{"exit_code":NaN}', '[]'):
            (self.target / "result.txt").write_text(raw)
            self.run["result_artifact"]["sha256"] = hashlib.sha256((self.target / "result.txt").read_bytes()).hexdigest()
            (self.target / "default-run.json").write_text(json.dumps(self.run))
            self.assertIn("DEFAULT_ROUTE_EVIDENCE", self.errors(self.validate()))

    def test_structural_validation_never_executes_target_commands(self):
        self.configure()
        checked = changed_index_validator(self.target)
        with patch("subprocess.run", side_effect=AssertionError("target execution during structural validation")):
            # GitEvidenceView invokes git through its own bounded subprocess API.
            from default_validation_route import validate_default_route
            checked.current_task_id = "fixture-task"
            checked.current_task_class = "standard-task"
            checked.git.head_revision = lambda: self.result
            checked.git.is_ancestor = lambda *_: True
            checked.git.changed_files = lambda *_: []
            validate_default_route(checked, self.route, parse_manifest(self.target / ".ai/alatyr.yaml"))
            self.assertNotIn("DEFAULT_ROUTE_EVIDENCE", self.errors(checked), [x.message for x in checked.findings])

    def test_local_success_is_not_canonical_acceptance(self):
        payload = upgrade_fixtures.accepted_payload()
        self.assertTrue(acceptance_failures(payload, default_route_required=True))
        payload["findings"] = [{"code": "DEFAULT_ROUTE_VERIFIED"}]
        self.assertEqual(acceptance_failures(payload, default_route_required=True), [])
        payload["status"] = "failed"
        self.assertTrue(acceptance_failures(payload, default_route_required=True))

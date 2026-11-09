from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import lifecycle_checkpoints as hooks
import request_brief as contract
import delivery_control as delivery
from inspect_session_context import TARGET_ANCHORS, capture
from tests.active_task_fixture import ActiveTaskFixture
from tests.test_target_validator_installation_state import write_accepted_record, write_state


def brief_fixture(objective="requested outcome", proof_id="proof"):
    return {"schema_version": 1, "record_kind": "alatyr-request-brief", "request_id": "request-1",
        "task_id": "fixture-task", "source_ref": "owner-message:current", "objective": objective,
        "outcomes": [{"id": "same-view", "statement": "Use one presentation with editable fields",
                      "rejection_case": "Shared buttons around different presentations", "proof_obligation_ids": [proof_id]}],
        "constraints": ["Preserve permissions"], "non_goals": ["Do not replace the requested presentation"],
        "requested_order": ["UI before tests"], "authorized_phases": ["inspect", "modify"],
        "write_scope": [{"path": "src", "recursive": True}], "effect_scope": []}


def action_fixture(**changes):
    return {"request_id": "request-1", "task_id": "fixture-task", "kind": "work", "phase": "modify",
            "outcome_ids": ["same-view"], "paths": ["src/example.txt"], "effects": [], **changes}


def delivery_fixture(brief):
    brief.update(schema_version=2, delivery_control={"pilot_outcome_ids": ["same-view"],
        "validation_history": ".ai/.runtime/validation-history.json", "max_expensive_runs": 2,
        "max_validation_seconds": 100})
    return {"schema_version": 1, "request_id": brief["request_id"], "task_id": brief["task_id"], "attempts": []}


def validation_fixture(**changes):
    return {"command_id": "selected-browser", "scope": "focused", "estimated_seconds": 10,
            "diagnosis_proof_id": None, "independent_review_proof_id": None, **changes}


def attempt_fixture(index=1, **changes):
    return {"evidence_ref": f"attempt-{index}.json", "result": "failed", "scope": "focused",
            "duration_seconds": 10, "expected_red_proof_id": None, **changes}


class DeliveryControlTests(unittest.TestCase):
    def setUp(self):
        self.brief = brief_fixture()
        self.history = delivery_fixture(self.brief)
        self.model = {"proof_obligations": [{"id": key, "required": True, "status": "passed",
                    "evidence_refs": ["attempt-1.json", "attempt-2.json", "attempt-3.json"]}
                    for key in ("proof", "diagnosis", "review", "red")]}

    def failures(self, **changes):
        brief = contract.parse_brief(json.dumps(self.brief).encode())
        action = contract.parse_action(action_fixture(phase="inspect", paths=[],
                                      validation=validation_fixture(**changes)))
        history = delivery.parse_history(json.dumps(self.history).encode(), brief)
        return delivery.delivery_failures(brief, action, self.model, history)

    def test_null_controls_are_explicitly_unadopted_not_an_implicit_budget(self):
        self.brief["delivery_control"] = None
        self.assertIsNone(contract.parse_brief(json.dumps(self.brief).encode())["delivery_control"])
        for value in ({}, [], True, 1, "disabled"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                contract.parse_brief(json.dumps({**self.brief, "delivery_control": value}).encode())

    def test_pilot_must_pass_before_expansion_or_broad_validation(self):
        self.model["proof_obligations"][0]["status"] = "open"
        self.assertEqual(self.failures(), [])
        self.assertTrue(any("representative" in x for x in self.failures(scope="broad")))
        self.brief["outcomes"].append({**self.brief["outcomes"][0], "id": "second"})
        action = contract.parse_action(action_fixture(outcome_ids=["second"]))
        self.assertTrue(delivery.delivery_failures(self.brief, action, self.model, self.history))
        self.model["proof_obligations"][0]["status"] = "passed"
        self.assertEqual(delivery.delivery_failures(self.brief, action, self.model, self.history), [])

    def test_cumulative_failure_escalation_and_distinct_failure_linked_proofs(self):
        self.history["attempts"] = [attempt_fixture()]
        self.assertTrue(any("diagnosis" in x for x in self.failures()))
        self.assertEqual(self.failures(diagnosis_proof_id="diagnosis"), [])
        self.assertTrue(self.failures(diagnosis_proof_id="proof"))
        self.history["attempts"].append(attempt_fixture(2, result="interrupted"))
        self.assertTrue(self.failures(diagnosis_proof_id="diagnosis"))
        self.assertTrue(self.failures(diagnosis_proof_id="diagnosis", independent_review_proof_id="diagnosis"))
        self.assertEqual(self.failures(diagnosis_proof_id="diagnosis", independent_review_proof_id="review"), [])
        self.model["proof_obligations"][2]["evidence_refs"] = ["old-failure.json"]
        self.assertTrue(self.failures(diagnosis_proof_id="diagnosis", independent_review_proof_id="review"))
        self.model["proof_obligations"][2]["evidence_refs"].append("attempt-2.json")
        self.history["attempts"].append(attempt_fixture(3))
        self.assertTrue(any("three" in x for x in self.failures(scope="broad", diagnosis_proof_id="diagnosis", independent_review_proof_id="review")))
        self.history["attempts"].append(attempt_fixture(4, result="passed"))
        self.assertTrue(any("three" in x for x in self.failures(scope="broad", diagnosis_proof_id="diagnosis", independent_review_proof_id="review")))
        for proof in self.model["proof_obligations"][1:3]: proof["evidence_refs"].extend(["attempt-3.json", "attempt-4.json"])
        self.assertEqual(self.failures(scope="broad", diagnosis_proof_id="diagnosis", independent_review_proof_id="review"), [])
        self.history["attempts"][-1]["scope"] = "broad"
        self.assertTrue(any("three" in x for x in self.failures(scope="broad", diagnosis_proof_id="diagnosis", independent_review_proof_id="review")))

    def test_budgets_below_at_and_above_including_failed_and_interrupted_runs(self):
        self.history["attempts"] = [attempt_fixture(result="passed", scope="broad", duration_seconds=90)]
        self.assertEqual(self.failures(scope="broad", estimated_seconds=9), [])
        self.assertEqual(self.failures(scope="broad", estimated_seconds=10), [])
        self.assertTrue(any("max_validation_seconds" in x for x in self.failures(estimated_seconds=11)))
        self.brief["delivery_control"]["max_expensive_runs"] = 1
        self.assertTrue(any("max_expensive_runs" in x for x in self.failures(scope="broad")))
        self.assertEqual(self.failures(), [])
        self.history["attempts"][0]["result"] = "interrupted"
        self.assertTrue(any("max_validation_seconds" in x for x in self.failures(estimated_seconds=11)))

    def test_expected_red_requires_a_linked_required_passed_proof(self):
        self.history["attempts"] = [attempt_fixture(result="expected-red")]
        self.assertTrue(any("expected RED" in x for x in self.failures()))
        self.history["attempts"][0]["expected_red_proof_id"] = "red"
        self.assertEqual(self.failures(), [])
        self.model["proof_obligations"][-1]["required"] = False
        self.assertTrue(self.failures())

    def test_completion_cannot_hide_a_failed_or_interrupted_last_attempt(self):
        for result in delivery.RESULTS:
            self.history["attempts"] = [attempt_fixture(result=result, expected_red_proof_id="red" if result == "expected-red" else None)]
            action = action_fixture(kind="complete", phase="inspect", paths=[])
            failures = delivery.delivery_failures(self.brief, action, self.model, self.history)
            self.assertEqual(bool(failures), result != "passed")

    def test_malformed_types_unknown_fields_and_history_boundaries(self):
        for key in self.brief["delivery_control"]:
            for value in (None, {}, [], True, -1, 1.5, "unknown"):
                changed = copy.deepcopy(self.brief); changed["delivery_control"][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    contract.parse_brief(json.dumps(changed).encode())
        for key in validation_fixture():
            for value in ({}, [], True, 1.5):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    delivery.parse_validation(validation_fixture(**{key: value}))
        for key in attempt_fixture():
            for value in ({}, [], True, 1.5):
                changed = copy.deepcopy(self.history); changed["attempts"] = [attempt_fixture(**{key: value})]
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    delivery.parse_history(json.dumps(changed).encode(), self.brief)
        self.history["attempts"] = [attempt_fixture(i, result="passed", duration_seconds=0) for i in range(32)]
        delivery.parse_history(json.dumps(self.history).encode(), self.brief)
        self.assertTrue(any("history is full" in x for x in self.failures()))
        self.history["attempts"].append(attempt_fixture(33))
        with self.assertRaises(ValueError): delivery.parse_history(json.dumps(self.history).encode(), self.brief)

    def test_history_identity_duplicates_and_exact_byte_bound(self):
        raw = json.dumps(self.history).encode()
        with patch.object(delivery, "MAX_HISTORY_BYTES", len(raw)):
            delivery.parse_history(raw, self.brief)
            with self.assertRaises(ValueError): delivery.parse_history(raw+b" ", self.brief)
        for changes in ({"request_id": "other"}, {"task_id": {}}, {"attempts": [attempt_fixture(), attempt_fixture()]}, {"extra": True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                delivery.parse_history(json.dumps({**self.history, **changes}).encode(), self.brief)


class RequestContractTests(unittest.TestCase):
    def setUp(self):
        self.brief = brief_fixture()
        self.model = {"objective": "requested outcome", "proof_obligations": [{"id": "proof", "required": True, "status": "open"}]}

    def parse(self, value=None):
        return contract.parse_brief(json.dumps(self.brief if value is None else value).encode())

    def failures(self, action=None):
        return contract.action_failures(self.parse(), contract.parse_action(action_fixture() if action is None else action),
            self.model, request_id="request-1", task_id="fixture-task")

    def test_valid_request_and_phase_ceiling(self):
        self.assertEqual(self.failures(), [])
        for phase in ("commit", "publish", "live-external"):
            with self.subTest(phase=phase):
                self.assertTrue(any("phase" in item for item in self.failures(action_fixture(phase=phase, effects=["origin/main"]))))

    def test_source_policy_phase_names_match_canonical_registry(self):
        from check_action_authorization import PHASES
        self.assertEqual(set(PHASES), contract.PHASES)

    def test_ordinary_cli_cannot_masquerade_as_a_neutral_native_callback(self):
        prefix = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "lifecycle-checkpoint", "--target", str(ROOT)]
        cases = [["review", "--request-brief", "missing.json"], ["status", "--session-id", "s"],
                 ["checkpoint", "--event", "before-action"],
                 ["bind", "--session-id", "s", "--request-id", "r", "--baseline", "b", "--task-id", "t"]]
        for arguments in cases:
            with self.subTest(action=arguments[0]):
                result = subprocess.run(prefix + arguments + ["--native-output"], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn("unrecognized arguments: --native-output", result.stderr)
        native = subprocess.run(prefix + ["event", "--event", "Stop", "--native-output", "--invalid"], capture_output=True, text=True)
        self.assertEqual(native.returncode, 0)
        self.assertEqual(json.loads(native.stdout), {})

    def test_scope_components_and_all_paths_are_checked(self):
        self.brief["write_scope"] = [{"path": "src/a", "recursive": True}]
        self.assertEqual(self.failures(action_fixture(paths=["src/a/file.py"])), [])
        self.assertTrue(self.failures(action_fixture(paths=["src/ab/file.py"])))
        self.assertTrue(self.failures(action_fixture(paths=["src/a/file.py", "src/elsewhere.py"])))
        self.brief["write_scope"][0]["recursive"] = False
        self.assertTrue(self.failures(action_fixture(paths=["src/a/file.py"])))

    def test_redirect_and_substituted_model_do_not_pass(self):
        for changed in ({"request_id": "previous"}, {"task_id": "unrelated"}, {"outcome_ids": ["invented"]}):
            with self.subTest(changed=changed):
                self.assertTrue(self.failures(action_fixture(**changed)))
        self.model["objective"] = "easier substitute"
        self.assertTrue(any("objective" in item for item in self.failures()))

    def test_completion_needs_every_original_outcome_not_a_ready_list(self):
        complete = action_fixture(kind="complete", phase="inspect", paths=[])
        for status in ("open", "blocked", "failed", "waived"):
            self.model["proof_obligations"][0]["status"] = status
            self.assertTrue(self.failures(complete), status)
        self.model["proof_obligations"][0]["status"] = "passed"
        self.assertEqual(self.failures(complete), [])
        self.brief["outcomes"].append({**self.brief["outcomes"][0], "id": "second", "proof_obligation_ids": ["missing"]})
        self.assertTrue(self.failures(complete))

    def test_original_outcome_oracle_rejects_a_self_confirming_substitute(self):
        original = {"read_body": "content-view", "edit_body": "content-view", "shared_controls": True}
        substitute = {"read_body": "content-view", "edit_body": "different-form", "shared_controls": True}
        complete = action_fixture(kind="complete", phase="inspect", paths=[])
        for observed, expected in ((original, []), (substitute, ["unverified"])):
            # The independent fixture oracle represents the original requirement;
            # implementation-shaped tests check only the common controls.
            self.assertTrue(observed["shared_controls"])
            accepted = observed["read_body"] == observed["edit_body"]
            self.model["proof_obligations"][0]["status"] = "passed" if accepted else "failed"
            failures = self.failures(complete)
            self.assertEqual(bool(failures), bool(expected))
            if expected: self.assertTrue(any(expected[0] in item for item in failures))

    def test_deep_json_and_windows_aliases_fail_with_diagnostics(self):
        with self.assertRaises(ValueError):
            contract.parse_brief(b"[" * 1100 + b"0" + b"]" * 1100)
        for path in ("src/.. /outside.txt", "src/NUL", "src/con.txt", "src/file.txt:secret", "src/file.", "src/COM\u00b9.txt"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                contract.request_path(path)
        guard = {"required": True, "file_tools": [{"tool_name": "Write", "path_field": "file_path"}]}
        with patch("support_write_transaction.safe_output", side_effect=RuntimeError("symlink loop")):
            self.assertTrue(contract.native_file_action_failures(ROOT, guard,
                {"tool_name": "Write", "tool_input": {"file_path": "src/example.txt"}}, action_fixture()))

    def test_missing_and_optional_proofs_cannot_cover_required_outcomes(self):
        self.model["proof_obligations"][0]["required"] = False
        self.assertTrue(self.failures())
        self.model["proof_obligations"] = []
        self.assertTrue(self.failures())

    def test_malformed_fields_are_diagnostics_not_unhashable_crashes(self):
        invalid = (None, True, 1, {}, [])
        for field in ("request_id", "task_id", "source_ref", "objective", "authorized_phases", "write_scope", "outcomes", "constraints", "non_goals", "requested_order", "effect_scope"):
            for value in invalid:
                if value == [] and field in {"constraints", "non_goals", "requested_order", "effect_scope"}:
                    continue
                mutated = copy.deepcopy(self.brief); mutated[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.parse(mutated)
        for field in ("request_id", "task_id", "phase", "kind", "outcome_ids", "paths", "effects"):
            for value in invalid:
                if value == [] and field in {"paths", "effects"}:
                    continue
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    contract.parse_action(action_fixture(**{field: value}))

    def test_unknown_fields_duplicates_placeholders_and_bad_paths_fail(self):
        for field, value in (("extra", True), ("objective", "{UNRESOLVED}"), ("authorized_phases", ["inspect", "inspect"])):
            mutated = copy.deepcopy(self.brief); mutated[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.parse(mutated)
        for path in ("../outside", "/absolute", "C:/absolute", "src//file", "src/./file", "src\\file", "src/*"):
            mutated = copy.deepcopy(self.brief); mutated["write_scope"][0]["path"] = path
            with self.subTest(path=path), self.assertRaises(ValueError): self.parse(mutated)
        raw = json.dumps(self.brief).replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1')
        with self.assertRaises(ValueError): contract.parse_brief(raw.encode())
        self.brief["objective"] = 'Preserve the JSON shape {"id": "value"}'
        self.assertEqual(self.parse()["objective"], self.brief["objective"])

    def test_byte_word_and_count_limits_include_exact_boundary(self):
        raw = json.dumps(self.brief).encode()
        with patch.object(contract, "MAX_BRIEF_BYTES", len(raw)):
            self.assertEqual(contract.parse_brief(raw), self.brief)
            with self.assertRaises(ValueError): contract.parse_brief(raw + b" ")
        from analysis_strategy_contract import structured_word_count
        count = structured_word_count(self.brief)
        with patch.object(contract, "MAX_BRIEF_WORDS", count):
            self.parse()
            mutated = copy.deepcopy(self.brief); mutated["objective"] += " extra"
            with self.assertRaises(ValueError): self.parse(mutated)
        self.brief["constraints"] = [f"constraint-{i}" for i in range(contract.MAX_ROWS)]
        self.parse()
        self.brief["constraints"].append("too-many")
        with self.assertRaises(ValueError): self.parse()

    def test_guard_policy_rejects_malformed_optional_adoption(self):
        good = {"required": True, "file_tools": [{"tool_name": "Write", "path_field": "file_path"}]}
        self.assertEqual(contract.guard_policy(good), good)
        for value in (None, {}, {**good, "required": 1}, {**good, "file_tools": {}},
                      {**good, "file_tools": good["file_tools"] * 2}):
            with self.subTest(value=value), self.assertRaises(ValueError): contract.guard_policy(value)
        unsafe = {"required": True, "file_tools": [{"tool_name": "shell", "path_field": "file_path"}]}
        self.assertTrue(contract.native_file_action_failures(ROOT, unsafe,
            {"tool_name": "shell", "tool_input": {"file_path": "src/example.txt", "command": "arbitrary side effects"}}, action_fixture()))


class RequestLifecycleFixture(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        for name in TARGET_ANCHORS:
            path = self.target / name
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True); path.write_text("{}\n", encoding="utf-8")
        write_state(self.target, "accepted"); write_accepted_record(self.target)
        self.policy = json.loads((ROOT / "templates/target" / hooks.POLICY).read_bytes())
        self.policy.update(enabled=True, provider="procedural")
        self.policy["request_guard"] = {"required": True, "file_tools": [{"tool_name": "Write", "path_field": "file_path"}]}
        self.write_policy()
        self.brief_path = ".ai/.runtime/request-brief.json"
        self.baseline = ".ai/.runtime/request-context.json"
        self.request = self.event("request")
        self.brief = brief_fixture(self.model["objective"], self.model["proof_obligations"][0]["id"])
        self.brief["request_id"] = self.request["request_id"]
        self.write_brief(); self.refresh_baseline()

    def write_policy(self):
        path = self.target / hooks.POLICY; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.policy), encoding="utf-8")

    def write_brief(self):
        (self.target / self.brief_path).write_text(json.dumps(self.brief), encoding="utf-8")

    def refresh_baseline(self):
        paths = [hooks.POLICY, ".ai/assistant/active-tasks.json", self.model_path.relative_to(self.target).as_posix(),
                 self.model["active_projection"]["path"], self.brief_path, "design.md"]
        (self.target / self.baseline).write_text(json.dumps(capture(self.target, paths)[0]), encoding="utf-8")

    def event(self, name, **payload):
        return hooks.handle(self.target, self.policy["provider"], name, {"session_id": "request-fixture", **payload})

    def action(self, **changes):
        return action_fixture(request_id=self.request["request_id"], **changes)

    def bind_request(self, **changes):
        return hooks.handle(self.target, self.policy["provider"], "before-action", {"session_id": "request-fixture"},
            bind={"request_id": self.request["request_id"], "baseline": self.baseline, "task_id": "fixture-task", "request_brief": self.brief_path, **changes})


class RequestLifecycleTests(RequestLifecycleFixture):
    def test_public_cli_checks_the_request_without_adopting_hooks_or_writing(self):
        self.policy["enabled"] = False; self.write_policy()
        before = {p.relative_to(self.target): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.target.rglob("*") if p.is_file() and ".git" not in p.parts}
        command = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "lifecycle-checkpoint", "--target", str(self.target), "review", "--request-brief", self.brief_path]
        for action, expected in ((self.action(), 0), (self.action(phase="publish", effects=["origin/main"]), 1)):
            result = subprocess.run(command, input=json.dumps(action), capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            self.assertFalse(json.loads(result.stdout)["authorization_granted"])
        after = {p.relative_to(self.target): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.target.rglob("*") if p.is_file() and ".git" not in p.parts}
        self.assertEqual(before, after)

    def adopt_focus(self):
        self.brief.update(schema_version=3, delivery_control=None, focus_control="dependency-readiness")
        self.model["execution_dependencies"] = [{"obligation_id": row["id"], "requires": []}
                                                 for row in self.model["proof_obligations"]]
        self.model["proof_obligations"][0]["status"] = "open"
        self.write_model(); self.write_index(); self.write_brief(); self.refresh_baseline()
        return self.action(brief_sha256=hashlib.sha256((self.target/self.brief_path).read_bytes()).hexdigest(),
                           obligation_ids=[self.model["proof_obligations"][0]["id"]])

    def test_focus_public_cli_and_delegate_reject_stale_worker_bindings(self):
        action = self.adopt_focus()
        for entry in (ROOT/"tools/alatyr.py", ROOT/"templates/target/.ai/assistant/tools/alatyr_delegate.py"):
            command = [sys.executable, "-B", str(entry), "lifecycle-checkpoint", "--target", str(self.target)]
            if entry.name == "alatyr_delegate.py": command += ["--framework-source", str(ROOT)]
            command += ["review", "--request-brief", self.brief_path]
            for changed, expected in ((action, 0), ({**action, "brief_sha256": "0"*64}, 1),
                                      ({**action, "brief_sha256": []}, 2),
                                      ({key: value for key, value in action.items() if key != "obligation_ids"}, 1)):
                result = subprocess.run(command, input=json.dumps(changed), capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stdout+result.stderr)
                report = json.loads(result.stdout)
                self.assertFalse(report["authorization_granted"])
                self.assertFalse(report["acceptance_granted"])
                if expected != 2:
                    self.assertEqual(report["focus_control"], "dependency-readiness")

    def test_focus_initial_binding_resume_and_worker_integration_preserve_original_digest(self):
        action = self.adopt_focus()
        self.assertEqual(self.bind_request()["status"], "bound")
        self.assertEqual(self.event("before-action", alatyr_action=action)["status"], "request-consistent")
        self.event("resume")
        self.assertTrue(self.event("before-action", alatyr_action=action)["checkpoint_required"])
        replacement = self.event("request")
        self.request = replacement
        self.brief["request_id"] = replacement["request_id"]
        self.brief["constraints"].append("Keep the clarified request boundary")
        self.write_brief(); self.refresh_baseline(); self.bind_request()
        old_worker = {**action, "request_id": replacement["request_id"]}
        self.assertTrue(self.event("before-action", alatyr_action=old_worker)["checkpoint_required"])
        # New work is constructed after source reconciliation; never retag the worker's old result.
        new_work = self.action(obligation_ids=[self.model["proof_obligations"][0]["id"]],
            brief_sha256=hashlib.sha256((self.target/self.brief_path).read_bytes()).hexdigest())
        self.assertEqual(self.event("before-action", alatyr_action=new_work)["status"], "request-consistent")

    def test_focus_raw_byte_changes_and_control_downgrade_invalidate_bound_actions(self):
        action = self.adopt_focus(); self.bind_request()
        path = self.target/self.brief_path
        original = path.read_bytes()
        path.write_bytes(original+b"\n")
        self.assertTrue(hooks.review_request(self.target, self.brief_path, action)["checkpoint_required"])
        with self.assertRaisesRegex(ValueError, "brief changed"):
            self.event("before-action", alatyr_action=action)
        self.brief["focus_control"] = None; self.write_brief()
        with self.assertRaisesRegex(ValueError, "brief changed"):
            self.event("before-action", alatyr_action=action)

    def test_focus_and_delivery_controls_both_enforce_their_own_constraints(self):
        self.adopt_focus()
        history = delivery_fixture(self.brief)
        self.brief["schema_version"] = 3
        path = self.target/self.brief["delivery_control"]["validation_history"]
        path.write_text(json.dumps(history), encoding="utf-8"); self.write_brief()
        action = self.action(phase="inspect", paths=[], validation=validation_fixture(),
            obligation_ids=[self.model["proof_obligations"][0]["id"]],
            brief_sha256=hashlib.sha256((self.target/self.brief_path).read_bytes()).hexdigest())
        self.assertEqual(hooks.review_request(self.target, self.brief_path, action)["status"], "request-consistent")
        history["attempts"] = [attempt_fixture()]
        path.write_text(json.dumps(history), encoding="utf-8")
        self.assertIn("diagnosis", hooks.review_request(self.target, self.brief_path, action)["reason"])
        history["attempts"] = []; path.write_text(json.dumps(history), encoding="utf-8")
        self.assertIn("brief digest", hooks.review_request(self.target, self.brief_path,
            {**action, "brief_sha256": "0"*64})["reason"])

    def test_frozen_worker_artifacts_preserve_binding_until_primary_review(self):
        from prepare_delegation_context import prepare as prepare_context
        from prepare_delegation_result import prepare as prepare_result
        from source_worker_contract import load_source_worker_policy, make_builtin_packet
        action = self.adopt_focus()
        action.update(phase="inspect", paths=[])
        policy = load_source_worker_policy(ROOT/"tools/source_worker_policy.json", root=ROOT)
        packet = make_builtin_packet(policy, "framework-rules")
        packet.update(bounded_context=["framework/action-authorization.md"], conditional_context=[])
        original = json.dumps(action).encode()
        preflight, context = prepare_context(packet, policy, root=ROOT, prompt=original,
            bootstrap={"fixture-host": b"Inspect only the supplied context"}, expansions=[], other_contexts=[])
        event = {"schema_version": 1, "event_kind": "worker-result-received", "backend_kind": "native-worker",
                 "worker_id": "fixture-worker", "packet_id": "fixture-packet", "base_revision": self.result}
        contents = {"context": context, "raw": original, "summary": b"Review the original request"}
        result = prepare_result(packet, event, contents, policy, preflight)
        self.assertEqual(result["status"], "requires-review")
        returned = json.loads(contents["raw"])
        self.assertEqual(hooks.review_request(self.target, self.brief_path, returned)["status"], "request-consistent")
        self.brief["constraints"].append("New clarification under the same task identity")
        self.write_brief()
        self.assertIn("brief digest", hooks.review_request(self.target, self.brief_path, returned)["reason"])
        self.assertEqual(contents["raw"], original)

    def test_delivery_control_through_public_cli_and_installed_delegate(self):
        history = delivery_fixture(self.brief)
        history["attempts"] = [attempt_fixture()]
        (self.target/self.brief["delivery_control"]["validation_history"]).write_text(json.dumps(history), encoding="utf-8")
        self.write_brief()
        action = self.action(phase="inspect", paths=[], validation=validation_fixture())
        for prefix in ([sys.executable, "-B", str(ROOT/"tools/alatyr.py")],
                       [sys.executable, "-B", str(ROOT/"templates/target/.ai/assistant/tools/alatyr_delegate.py")]):
            args = prefix + ["lifecycle-checkpoint", "--target", str(self.target)]
            if "alatyr_delegate.py" in prefix[-1]: args += ["--framework-source", str(ROOT)]
            result = subprocess.run(args+["review", "--request-brief", self.brief_path], input=json.dumps(action), capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stdout+result.stderr)
            self.assertIn("diagnosis", json.loads(result.stdout)["reason"])
        history["attempts"] = []
        (self.target/self.brief["delivery_control"]["validation_history"]).write_text(json.dumps(history), encoding="utf-8")
        self.assertEqual(hooks.review_request(self.target, self.brief_path, action)["status"], "request-consistent")

    def test_public_delivery_budget_boundaries_missing_history_and_null_control(self):
        history = delivery_fixture(self.brief)
        history["attempts"] = [attempt_fixture(result="passed", duration_seconds=90)]
        path = self.target/self.brief["delivery_control"]["validation_history"]
        path.write_text(json.dumps(history), encoding="utf-8"); self.write_brief()
        command = [sys.executable, "-B", str(ROOT/"tools/alatyr.py"), "lifecycle-checkpoint", "--target", str(self.target),
                   "review", "--request-brief", self.brief_path]
        for seconds, expected in ((9, 0), (10, 0), (11, 1)):
            action = self.action(phase="inspect", paths=[], validation=validation_fixture(estimated_seconds=seconds))
            result = subprocess.run(command, input=json.dumps(action), capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stdout+result.stderr)
            self.assertFalse(json.loads(result.stdout)["authorization_granted"])
        path.unlink()
        result = subprocess.run(command, input=json.dumps(action), capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout+result.stderr)
        self.assertIn("validation history", json.loads(result.stdout)["reason"])
        self.brief["delivery_control"] = None; self.write_brief()
        self.assertTrue(hooks.review_request(self.target, self.brief_path, action)["checkpoint_required"])
        self.assertEqual(hooks.review_request(self.target, self.brief_path, self.action())["status"], "request-consistent")

    def test_delivery_history_must_be_retained_and_changes_invalidate_binding(self):
        history = delivery_fixture(self.brief)
        path = self.target/self.brief["delivery_control"]["validation_history"]
        path.write_text(json.dumps(history), encoding="utf-8"); self.write_brief(); self.refresh_baseline()
        with self.assertRaisesRegex(ValueError, "exact validation history"): self.bind_request()
        baseline = capture(self.target, [hooks.POLICY, ".ai/assistant/active-tasks.json", self.model_path.relative_to(self.target).as_posix(),
            self.model["active_projection"]["path"], self.brief_path, "design.md", path.relative_to(self.target).as_posix()])[0]
        (self.target/self.baseline).write_text(json.dumps(baseline), encoding="utf-8")
        self.bind_request()
        original = copy.deepcopy(self.brief)
        self.brief["delivery_control"] = None; self.write_brief()
        with self.assertRaisesRegex(ValueError, "brief changed"):
            self.event("before-action", alatyr_action=self.action())
        self.brief = original; self.write_brief()
        history["attempts"].append(attempt_fixture())
        path.write_text(json.dumps(history), encoding="utf-8")
        self.assertTrue(self.event("before-action", alatyr_action=self.action())["checkpoint_required"])

    def test_installed_delegate_uses_the_same_review_parser_and_result(self):
        command = [sys.executable, "-B", str(ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"),
                   "lifecycle-checkpoint", "--target", str(self.target), "--framework-source", str(ROOT),
                   "review", "--request-brief", self.brief_path]
        for action, expected in ((self.action(), 0), (self.action(task_id="old-task"), 1)):
            result = subprocess.run(command, input=json.dumps(action), capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            self.assertFalse(json.loads(result.stdout)["authorization_granted"])

    def test_required_brief_cannot_be_omitted_or_skipped_by_an_unbound_session(self):
        with self.assertRaisesRegex(ValueError, "explicit request brief"):
            self.bind_request(request_brief=None)
        self.assertTrue(self.event("before-action")["checkpoint_required"])
        self.assertEqual(self.bind_request()["status"], "bound")
        self.policy["request_guard"]["required"] = False; self.write_policy(); self.refresh_baseline()
        with self.assertRaisesRegex(ValueError, "cannot drop"):
            self.bind_request(request_brief=None)

    def test_binding_requires_exact_brief_in_selected_context(self):
        baseline = json.loads((self.target / self.baseline).read_bytes())
        baseline["inputs"] = [row for row in baseline["inputs"] if row["path"] != self.brief_path]
        # Re-capture without the brief to keep the baseline internally canonical.
        paths = [row["path"] for row in baseline["inputs"]]
        (self.target / self.baseline).write_text(json.dumps(capture(self.target, paths)[0]), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "exact request brief"):
            self.bind_request()

    def test_request_replacement_resume_and_interrupt_do_not_resume_old_work(self):
        self.bind_request()
        replacement = self.event("request")
        self.assertNotEqual(replacement["request_id"], self.request["request_id"])
        self.assertTrue(self.event("before-action", alatyr_action=self.action())["checkpoint_required"])
        self.request = replacement
        with self.assertRaisesRegex(ValueError, "identity"):
            self.bind_request()
        self.brief["request_id"] = replacement["request_id"]; self.write_brief(); self.refresh_baseline(); self.bind_request()
        self.event("resume")
        self.assertTrue(self.event("before-action", alatyr_action=self.action())["checkpoint_required"])
        self.event("interrupt")
        self.assertEqual(self.event("before-action")["status"], "interrupted")

    def test_unknown_missing_and_changed_action_or_brief_never_pass(self):
        self.bind_request()
        with self.assertRaises(ValueError): self.event("before-action")
        self.assertTrue(self.event("before-action", alatyr_action=self.action(outcome_ids=["unrelated"]))["checkpoint_required"])
        (self.target / self.brief_path).write_bytes((self.target / self.brief_path).read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "brief changed"):
            self.event("before-action", alatyr_action=self.action())

    def test_partial_answer_and_completion_are_not_conflated(self):
        self.model["proof_obligations"][0]["status"] = "open"; self.write_model(); self.write_index(); self.refresh_baseline()
        self.bind_request()
        answer = self.action(kind="answer", phase="inspect", paths=[])
        partial = self.event("completion", alatyr_action=answer)
        self.assertEqual(partial["status"], "handoff-review")
        self.assertEqual(partial["request_progress"]["remaining_outcome_ids"], ["same-view"])
        self.assertFalse(partial["request_progress"]["completion_established"])
        with self.assertRaisesRegex(ValueError, "required proof obligations"):
            self.event("completion", alatyr_action={**answer, "kind": "complete"})
        self.assertFalse(self.event("completion", alatyr_action=answer)["acceptance_granted"])

    def test_supporting_delivery_cannot_hide_nine_remaining_areas_at_stop(self):
        # One completed preparation scope is not the whole approved request.
        for index in range(9):
            proof = copy.deepcopy(self.model["proof_obligations"][0])
            proof.update(id=f"area-{index}", status="blocked" if index == 0 else "open", evidence_refs=[])
            self.model["proof_obligations"].append(proof)
            self.brief["outcomes"].append({"id": f"area-{index}", "statement": "Deliver the requested area",
                "rejection_case": "Preparation alone", "proof_obligation_ids": [proof["id"]]})
        self.model["execution_dependencies"] = [{"obligation_id": row["id"], "requires": []}
                                                 for row in self.model["proof_obligations"]]
        self.write_model(); self.write_index(); self.write_brief(); self.refresh_baseline()
        self.bind_request()
        answer = self.action(kind="answer", phase="inspect", paths=[])
        for _ in range(2):
            value = self.event("completion", alatyr_action=answer)
            self.assertEqual(value["status"], "unfinished", value)
            self.assertEqual(len(value["request_progress"]["remaining_outcome_ids"]), 9)
            self.assertEqual(len(value["request_progress"]["ready_outcome_ids"]), 8)
            self.assertFalse(value["emit_native_block"])
            self.assertFalse(value["authorization_granted"])
            self.assertFalse(value["acceptance_granted"])
        self.event("interrupt")
        self.assertEqual(self.event("completion", alatyr_action=answer)["status"], "interrupted")

    def test_native_mutator_path_cannot_be_overridden_by_declared_action(self):
        for provider in sorted(hooks.NATIVE_EVENTS):
            with self.subTest(provider=provider):
                self.policy["provider"] = provider; self.write_policy(); self.refresh_baseline(); self.bind_request()
                valid = self.event("before-action", alatyr_action=self.action(), tool_name="Write", tool_input={"file_path": "src/example.txt"})
                self.assertEqual(valid["status"], "request-consistent", valid)
                wrong = self.event("before-action", alatyr_action=self.action(), tool_name="Write", tool_input={"file_path": "outside.txt"})
                self.assertTrue(wrong["checkpoint_required"])
                unknown = self.event("before-action", alatyr_action=self.action(), tool_name="shell", tool_input={"command": "anything"})
                self.assertTrue(unknown["checkpoint_required"])
                self.assertFalse(wrong["emit_native_block"])

    def test_verified_checkpoint_can_deny_without_enabling_observe_interception(self):
        from datetime import datetime, timezone
        self.policy.update(provider="codex", mode="checkpoint")
        self.policy["native_evidence"] = {"state": "observed", "client_version": "synthetic-fixture",
            "source": "wire fixture, not actual host evidence", "verified_at": datetime.fromtimestamp(time.time()-10, timezone.utc).isoformat(),
            "expires_at": datetime.fromtimestamp(time.time()+600, timezone.utc).isoformat()}
        self.write_policy(); self.refresh_baseline(); self.bind_request()
        result = self.event("before-action", alatyr_action=self.action(), tool_name="shell", tool_input={})
        self.assertTrue(result["emit_native_block"])
        from run_lifecycle_checkpoint import native_output
        self.assertEqual(native_output("codex", "PreToolUse", result)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertFalse(result["native_interception_verified"])

    def test_disabled_route_does_not_load_briefs_or_models(self):
        self.policy["enabled"] = False; self.write_policy()
        with patch.object(hooks, "review_request", side_effect=AssertionError("guard read on disabled route")), \
                patch.object(hooks, "selected_task", side_effect=AssertionError("task read on disabled route")):
            self.assertEqual(self.event("before-action")["status"], "disabled")

    def test_standalone_review_rechecks_selected_model_after_its_last_brief_read(self):
        real = hooks.read_output
        reads = 0
        def changed(target, path, **kwargs):
            nonlocal reads
            raw = real(target, path, **kwargs)
            if path == self.target / self.brief_path:
                reads += 1
                if reads == 2:
                    self.model["objective"] = "unrelated replacement"
                    self.model_path.write_text(json.dumps(self.model), encoding="utf-8")
            return raw
        with patch.object(hooks, "read_output", side_effect=changed), self.assertRaisesRegex(ValueError, "selected request inputs changed"):
            hooks.review_request(self.target, self.brief_path, self.action())

    def test_completion_cannot_drop_newly_selected_proof_inputs_from_baseline(self):
        self.bind_request()
        extra = self.target / "completion-proof.txt"; extra.write_bytes(b"proof\n")
        real = hooks.selected_task
        def selected(*args, **kwargs):
            view = real(*args, **kwargs)
            if kwargs.get("require_completion"):
                view["checkpoint_inputs"]["completion-proof.txt"] = hashlib.sha256(extra.read_bytes()).hexdigest()
            return view
        with patch.object(hooks, "selected_task", side_effect=selected):
            result = self.event("completion", alatyr_action=self.action(kind="complete", phase="inspect", paths=[]))
        self.assertEqual(result["status"], "request-review-required", result)
        self.assertIn("retained context", result["reason"])

    def test_procedural_delivery_under_native_policy_needs_no_native_tool_fields(self):
        self.policy["provider"] = "codex"; self.write_policy(); self.refresh_baseline(); self.bind_request()
        command = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "lifecycle-checkpoint", "--target", str(self.target),
                   "--provider", "codex", "checkpoint", "--event", "before-action"]
        result = subprocess.run(command, input=json.dumps({"session_id": "request-fixture", "alatyr_action": self.action()}),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["status"], "request-consistent")
        self.assertFalse(output["emit_native_block"])

    def test_closed_task_cannot_be_reopened_by_standalone_review(self):
        self.close()
        result = hooks.review_request(self.target, self.brief_path, self.action())
        self.assertTrue(result["checkpoint_required"], result)
        self.assertIn("closed task", result["reason"])

    def test_symlink_escape_and_missing_adopted_brief_fail_without_writes(self):
        self.bind_request()
        (self.target / self.brief_path).unlink()
        with self.assertRaisesRegex(ValueError, "missing request brief"):
            self.event("before-action", alatyr_action=self.action())
        self.write_brief()
        link = self.target / "src/escape"
        try:
            link.symlink_to(self.target.parent, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are unavailable on this host")
        with self.assertRaises(ValueError):
            hooks.review_request(self.target, self.brief_path, self.action(paths=["src/escape/other.txt"]))

    def test_interruption_during_guard_review_wins_at_delivery(self):
        self.bind_request()
        real = hooks.review_request
        def interrupted(*args, **kwargs):
            self.event("interrupt")
            return real(*args, **kwargs)
        with patch.object(hooks, "review_request", side_effect=interrupted):
            result = self.event("before-action", alatyr_action=self.action())
        self.assertEqual(result["status"], "interrupted", result)
        self.assertFalse(result["authorization_granted"])


if __name__ == "__main__":
    unittest.main()

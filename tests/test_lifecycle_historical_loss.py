"""Integration boundaries between optional hooks and reviewed missing history."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

import tests.test_historical_task_loss as historical
from tests.active_task_fixture import ActiveTaskFixture
from tests.test_target_validator_installation_state import write_accepted_record, write_state

import lifecycle_checkpoints as hooks
from inspect_session_context import TARGET_ANCHORS, capture


class LifecycleHistoricalLossTests(unittest.TestCase):
    def prepare(self, *, missing=True):
        fixture = (historical.HistoricalTaskLossTests(
            "test_reviewed_missing_history_is_a_warning_not_completion")
            if missing else ActiveTaskFixture())
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        self.fixture, self.target = fixture, fixture.target
        for name in TARGET_ANCHORS:
            path = self.target / name
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}\n", encoding="utf-8")
        write_state(self.target, "accepted")
        write_accepted_record(self.target)
        self.policy = json.loads((hooks.ROOT / "templates/target" / hooks.POLICY).read_bytes())
        self.policy.update(enabled=True, provider="codex")
        self.write_policy()

    def write_policy(self):
        path = self.target / hooks.POLICY
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.policy), encoding="utf-8")

    def event(self, event):
        return hooks.handle(self.target, "codex", event, {"session_id": "integration-fixture"})

    def bind(self):
        request = self.event("request")
        baseline = ".ai/.runtime/lifecycle-baseline.json"
        path = self.target / baseline
        path.parent.mkdir(parents=True, exist_ok=True)
        selected = ["design.md", hooks.POLICY, ".ai/assistant/active-tasks.json"]
        if self.fixture.model_path.is_file():
            selected += [self.fixture.model_path.relative_to(self.target).as_posix(),
                         self.fixture.model["active_projection"]["path"]]
        path.write_text(json.dumps(capture(self.target, selected)[0]), encoding="utf-8")
        return hooks.handle(self.target, "codex", "before-action",
            {"session_id": "integration-fixture"}, bind={"request_id": request["request_id"],
            "baseline": baseline, "task_id": "fixture-task"})

    def test_disabled_hooks_ignore_missing_history_without_runtime_writes(self):
        self.prepare()
        defaults = json.loads((hooks.ROOT / "templates/target" / hooks.POLICY).read_bytes())
        self.assertFalse(defaults["enabled"])
        self.assertEqual(defaults["native_evidence"]["state"], "unverified")
        self.policy["enabled"] = False
        self.write_policy()
        with patch.object(hooks, "selected_task", side_effect=AssertionError("unexpected lookup")):
            result = self.event("before-action")
        self.assertEqual(result["status"], "disabled")
        self.assertFalse(result["authorization_granted"])
        self.assertFalse((self.target / hooks.RUNTIME).exists())

    def test_historical_loss_is_not_a_lifecycle_selected_task(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "selected task is unavailable"):
            hooks.selected_task(self.target, "fixture-task")
        self.assertIsNone(self.fixture.task["completion_evidence"])

    def test_reviewed_loss_cannot_be_bound_or_rewrite_original_registration(self):
        self.prepare()
        index = self.target / ".ai/assistant/active-tasks.json"
        before = index.read_bytes()
        with self.assertRaisesRegex(ValueError, "selected task is unavailable"):
            self.bind()
        self.assertEqual(index.read_bytes(), before)
        status = hooks.session_status(self.target, "integration-fixture")
        self.assertEqual(status["status"], "unbound")
        self.assertFalse(status["authorization_granted"])
        self.assertFalse(status["acceptance_granted"])

    def test_invalid_loss_witness_cannot_fall_back_to_execution(self):
        self.prepare()
        self.fixture.task["evidence_loss_disposition"]["sha256"] = "0" * 64
        self.fixture.save(".ai/assistant/active-tasks.json", {
            "schema_version": 2, "index_kind": "target-active-task-index",
            "tasks": [self.fixture.task]})
        with self.assertRaisesRegex(ValueError, "selected task is unavailable"):
            self.bind()

    def test_rediscovered_model_does_not_automatically_resume_loss(self):
        self.prepare()
        self.fixture.model_path.write_bytes(self.fixture.model_bytes)
        with self.assertRaisesRegex(ValueError, "selected task is unavailable"):
            self.bind()
        self.assertEqual(self.fixture.task["state"], "historical-evidence-missing")

    def test_unbound_completion_never_accepts_or_resumes_missing_history(self):
        self.prepare()
        self.event("request")
        result = self.event("completion")
        self.assertEqual(result["status"], "inactive")
        self.assertFalse(result["emit_native_block"])
        self.assertFalse(result["authorization_granted"])
        self.assertFalse(result["acceptance_granted"])

    def bind_then_classify_loss(self):
        self.prepare()
        fixture = self.fixture
        lost = copy.deepcopy(fixture.task)
        fixture.task = copy.deepcopy(fixture.original)
        fixture.model_path.write_bytes(fixture.model_bytes)
        fixture.write_index()
        self.assertEqual(self.bind()["status"], "bound")
        fixture.model_path.unlink()
        fixture.task = lost
        fixture.rewrite()

    def test_preexisting_binding_is_rejected_after_task_becomes_historical(self):
        self.bind_then_classify_loss()
        # Library I/O errors are deliberately handled by the public delivery CLI.
        with self.assertRaises(FileNotFoundError):
            self.event("before-action")
        completed = subprocess.run([
            sys.executable, str(hooks.ROOT / "tools/run_lifecycle_checkpoint.py"),
            "--target", str(self.target), "--provider", "codex", "event",
            "--event", "PreToolUse"], input=json.dumps({"session_id": "integration-fixture"}),
            text=True, capture_output=True, check=False)
        self.assertEqual(completed.returncode, 2, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "unavailable")
        self.assertTrue(result["checkpoint_required"])
        self.assertFalse(result["authorization_granted"])
        self.assertFalse(result["acceptance_granted"])

    def test_completion_cannot_reuse_a_binding_for_newly_missing_history(self):
        self.bind_then_classify_loss()
        with self.assertRaisesRegex(ValueError, "selected task is unavailable"):
            self.event("completion")

    def test_existing_active_task_binding_and_unfinished_delivery_still_work(self):
        self.prepare(missing=False)
        fixture = self.fixture
        fixture.model["execution_dependencies"] = [
            {"obligation_id": row["id"], "requires": []}
            for row in fixture.model["proof_obligations"]]
        fixture.model["proof_obligations"][0]["status"] = "open"
        fixture.write_model()
        fixture.write_index()
        self.assertEqual(self.bind()["status"], "bound")
        self.assertEqual(self.event("before-action")["status"], "current-context")
        result = self.event("completion")
        self.assertEqual(result["status"], "unfinished")
        self.assertFalse(result["authorization_granted"])
        self.assertFalse(result["acceptance_granted"])


if __name__ == "__main__":
    unittest.main()

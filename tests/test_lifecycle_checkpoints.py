from __future__ import annotations

import copy
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
from inspect_session_context import TARGET_ANCHORS, capture, check_retained_context
from run_lifecycle_checkpoint import build_parser, native_output, normalize
from tests.active_task_fixture import ActiveTaskFixture
from tests.test_target_validator_installation_state import write_accepted_record, write_state, validator


class LifecycleTests(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        for name in TARGET_ANCHORS:
            path = self.target / name
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}\n", encoding="utf-8")
        write_state(self.target, "accepted")
        write_accepted_record(self.target)
        self.policy = json.loads((ROOT / "templates/target" / hooks.POLICY).read_bytes())
        self.policy.update(enabled=True, provider="codex")
        self.write_policy()
        self.model["execution_dependencies"] = [{"obligation_id": row["id"], "requires": []} for row in self.model["proof_obligations"]]
        self.model["proof_obligations"][0]["status"] = "open"
        self.write_model(); self.write_index()
        self.baseline = ".ai/.runtime/continuity/hook-baseline.json"
        self.refresh_baseline()

    def refresh_baseline(self):
        path = self.target / self.baseline
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(capture(self.target, ["design.md", hooks.POLICY, ".ai/assistant/active-tasks.json", self.model_path.relative_to(self.target).as_posix(), self.model["active_projection"]["path"]])[0]), encoding="utf-8")

    def write_policy(self):
        path = self.target / hooks.POLICY
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.policy), encoding="utf-8")

    def event(self, event, **extra):
        return hooks.handle(self.target, self.policy["provider"], event, {"session_id": "fixture-session", **extra})

    def bind_session(self, request=None):
        request = request or self.event("request")
        return hooks.handle(self.target, self.policy["provider"], "before-action", {"session_id": "fixture-session"},
            bind={"request_id": request["request_id"], "baseline": self.baseline, "task_id": "fixture-task"})

    def observed(self):
        from datetime import datetime, timezone
        self.policy.update(mode="checkpoint", max_reminders=1)
        self.policy["native_evidence"] = {"state": "observed", "client_version": "fixture-only",
            "source": "test fixture, not native smoke evidence",
            "verified_at": datetime.fromtimestamp(time.time()-10, timezone.utc).isoformat(),
            "expires_at": datetime.fromtimestamp(time.time()+600, timezone.utc).isoformat()}
        self.write_policy()
        self.refresh_baseline()

    def test_disabled_path_does_not_inspect_tasks_or_write_state(self):
        self.policy["enabled"] = False; self.write_policy()
        with patch.object(hooks, "selected_task", side_effect=AssertionError("unexpected task scan")), \
                patch.object(hooks, "check_retained_context", side_effect=AssertionError("unexpected context scan")):
            result = self.event("before-action")
        self.assertEqual(result["status"], "disabled")
        self.assertFalse((self.target / hooks.RUNTIME).exists())

    def test_real_bind_and_selected_readiness_do_not_grant_authority_or_acceptance(self):
        self.assertEqual(self.bind_session()["status"], "bound")
        self.assertEqual(self.event("before-action")["status"], "current-context")
        result = self.event("completion")
        self.assertEqual(result["status"], "unfinished", result)
        self.assertFalse(result["emit_native_block"])
        self.assertFalse(result["authorization_granted"])
        self.assertFalse(result["acceptance_granted"])

    def test_request_resume_compaction_and_change_require_new_review(self):
        for event in ("request", "resume", "compact", "after-change"):
            with self.subTest(event=event):
                self.bind_session(); self.event(event)
                result = self.event("before-action")
                self.assertEqual(result["checkpoint_required"], event != "request", result)
                self.assertFalse(result["authorization_granted"])

    def test_old_request_binding_cannot_survive_new_request(self):
        old = self.event("request"); self.event("request")
        with self.assertRaisesRegex(ValueError, "current.*request"):
            self.bind_session(old)

    def test_interrupt_revokes_binding_and_cannot_restart_or_rebind_old_request(self):
        old = self.event("request"); self.bind_session(old)
        self.assertEqual(self.event("interrupt")["status"], "interrupted")
        result = self.event("completion")
        self.assertFalse(result["emit_native_block"])
        self.assertEqual(result["status"], "interrupted")
        self.assertEqual(self.bind_session(old)["status"], "interrupted")
        self.assertEqual(self.bind_session()["status"], "bound")

    def test_interrupt_during_slow_evaluation_wins_without_session_lock(self):
        self.observed(); self.bind_session()
        real = hooks.selected_task
        def interrupted(*args):
            self.event("interrupt")
            return real(*args)
        with patch.object(hooks, "selected_task", side_effect=interrupted):
            result = self.event("completion")
        self.assertEqual(result["status"], "interrupted")
        self.assertFalse(result["emit_native_block"])
        self.assertEqual(self.event("before-action")["status"], "interrupted")

    def test_freshness_shared_with_cli_and_unrelated_files_not_selected(self):
        self.bind_session()
        (self.target / "unrelated-history.md").write_bytes(b"irrelevant")
        self.assertEqual(self.event("before-action")["status"], "current-context")
        (self.target / "design.md").write_bytes(b"changed owner")
        report = check_retained_context(self.target, self.target / self.baseline)
        result = self.event("before-action")
        self.assertEqual(report["status"], "rehydration-required")
        self.assertTrue(result["checkpoint_required"])

    def test_reminder_limit_and_synthetic_prompt_never_renew_authorization(self):
        self.observed(); self.bind_session()
        first = self.event("completion")
        self.assertTrue(first["emit_native_block"])
        self.assertFalse(self.event("completion")["emit_native_block"])
        synthetic = self.event("request", prompt=first["reason"])
        self.assertFalse(synthetic["authorization_granted"])
        self.assertFalse(self.event("completion")["emit_native_block"])
        self.assertEqual(self.event("before-action")["status"], "inactive")
        self.bind_session(synthetic)
        self.assertFalse(self.event("completion")["emit_native_block"])
        self.event("resume"); self.bind_session()
        self.assertFalse(self.event("completion")["emit_native_block"])

    def test_stop_hook_active_suppresses_recursive_reminder(self):
        self.observed(); self.bind_session()
        self.assertFalse(self.event("completion", stop_hook_active=True)["emit_native_block"])

    def test_unselected_small_work_does_not_require_models_or_context_packets(self):
        self.observed(); self.event("request")
        with patch.object(hooks, "selected_task", side_effect=AssertionError("unselected task read")), \
                patch.object(hooks, "check_retained_context", side_effect=AssertionError("unselected context read")):
            for event in ("before-action", "completion"):
                result = self.event(event)
                self.assertEqual(result["status"], "inactive")
                self.assertFalse(result["emit_native_block"])
                self.assertFalse(result["authorization_granted"])

    def test_resume_cannot_acknowledge_interruption_or_reopen_an_ended_scope(self):
        for event, expected in (("interrupt", "interrupted"), ("end", "ended")):
            self.bind_session(); self.event(event)
            resumed = self.event("resume")
            self.assertEqual(resumed["status"], expected)
            self.assertEqual(self.event("before-action")["status"], expected)
            self.assertFalse(self.event("completion")["emit_native_block"])
            self.assertEqual(self.bind_session()["status"], "bound")

    def test_interruption_before_a_state_record_is_not_forgotten(self):
        self.event("interrupt")
        self.assertEqual(self.event("before-action")["status"], "interrupted")
        self.assertEqual(self.event("resume")["status"], "interrupted")
        self.assertEqual(self.bind_session()["status"], "bound")

    def test_selected_model_projection_and_task_index_changes_invalidate_context(self):
        for relative in (self.model_path.relative_to(self.target).as_posix(),
                         self.model["active_projection"]["path"], ".ai/assistant/active-tasks.json"):
            with self.subTest(path=relative):
                self.bind_session()
                path = self.target / relative; original = path.read_bytes()
                path.write_bytes(original + b"\n")
                self.assertTrue(self.event("before-action")["checkpoint_required"])
                path.write_bytes(original)

    def test_completion_does_not_promote_a_task_changed_after_context_check(self):
        self.observed(); self.bind_session()
        original = hooks.selected_task
        def changed(*args):
            self.model["proof_obligations"][0]["statement"] = "new selected obligation"
            self.write_model(); self.write_index()
            return original(*args)
        with patch.object(hooks, "selected_task", side_effect=changed):
            result = self.event("completion")
        self.assertEqual(result["status"], "review-required")
        self.assertFalse(result["emit_native_block"])

    def test_completion_rechecks_non_task_owners_after_task_evaluation(self):
        self.observed(); self.bind_session()
        original = hooks.selected_task
        def changed(*args):
            result = original(*args)
            (self.target / "design.md").write_text("changed canonical owner", encoding="utf-8")
            return result
        with patch.object(hooks, "selected_task", side_effect=changed):
            result = self.event("completion")
        self.assertEqual(result["status"], "review-required")
        self.assertFalse(result["emit_native_block"])

    def test_one_context_comparison_follows_task_evaluation_and_state_write(self):
        self.observed(); self.bind_session()
        order = []
        selected, written, checked = hooks.selected_task, hooks.replace_output, hooks.check_retained_context
        def select(*args):
            order.append("task"); return selected(*args)
        def write(*args):
            order.append("write"); return written(*args)
        def check(*args):
            order.append("context"); return checked(*args)
        with patch.object(hooks, "selected_task", side_effect=select), \
                patch.object(hooks, "replace_output", side_effect=write), \
                patch.object(hooks, "check_retained_context", side_effect=check):
            result = self.event("completion")
        self.assertTrue(result["emit_native_block"], result)
        self.assertEqual(order, ["task", "write", "context"])

    def test_late_interruption_denies_pre_action_without_continuing_completion(self):
        self.observed(); self.bind_session()
        original = hooks.check_retained_context
        def interrupt(*args):
            result = original(*args)
            self.event("interrupt")
            return result
        with patch.object(hooks, "check_retained_context", side_effect=interrupt):
            result = self.event("before-action")
        self.assertEqual(result["status"], "interrupted")
        self.assertTrue(result["emit_native_block"])
        self.assertFalse(self.event("completion")["emit_native_block"])

    def test_binding_requires_the_actual_selected_task_projection_in_baseline(self):
        path = self.target / self.baseline
        path.write_text(json.dumps(capture(self.target, ["design.md"])[0]), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "selected model and projection"):
            self.bind_session()

    def test_read_only_status_and_policy_changes_do_not_refresh_bindings(self):
        self.bind_session()
        paths = list((self.target / hooks.RUNTIME).glob("*.json"))
        before = {path: path.read_bytes() for path in paths}
        self.assertEqual(hooks.session_status(self.target, "fixture-session")["status"], "bound")
        self.assertEqual(before, {path: path.read_bytes() for path in paths})
        self.policy["binding_ttl_seconds"] += 1; self.write_policy()
        self.assertTrue(self.event("before-action")["checkpoint_required"])

    def test_binding_requires_reviewed_policy_and_does_not_acknowledge_policy_edits(self):
        self.policy["binding_ttl_seconds"] += 1; self.write_policy()
        with self.assertRaisesRegex(ValueError, "lifecycle policy"):
            self.bind_session()
        self.refresh_baseline()
        self.assertEqual(self.bind_session()["status"], "bound")

    def test_all_native_evidence_fields_are_type_safe_and_expiry_is_enforced(self):
        self.observed()
        for field in self.policy["native_evidence"]:
            for bad in (None, {}, [], True, 1, "unknown"):
                value = copy.deepcopy(self.policy); value["native_evidence"][field] = bad
                self.assertTrue(hooks.policy_failures(value), (field, bad))
        self.policy["native_evidence"]["expires_at"] = "2000-01-01T00:00:00+00:00"
        self.assertTrue(hooks.policy_failures(self.policy))
        self.policy["native_evidence"]["verified_at"] = "0001-01-01T00:00:00+14:00"
        self.assertTrue(hooks.policy_failures(self.policy))

    def test_budget_boundaries_and_unverified_checkpoint_mode_cannot_emit_native_block(self):
        for field, low, high in (("binding_ttl_seconds", 1, 3600), ("max_reminders", 0, hooks.MAX_REMINDERS)):
            for number in (low-1, low, high, high+1):
                value = copy.deepcopy(self.policy); value[field] = number
                self.assertEqual(bool(hooks.policy_failures(value)), not low <= number <= high)
        self.policy.update(mode="checkpoint", max_reminders=3); self.write_policy()
        self.refresh_baseline()
        self.bind_session()
        self.assertFalse(self.event("completion")["emit_native_block"])

    def test_expiry_rejects_early_without_context_scan_and_at_boundary(self):
        request = self.event("request")
        with patch.object(hooks.time, "time", return_value=1000):
            self.bind_session(request)
        for when in (1899.99, 1900, 1900.01):
            with patch.object(hooks.time, "time", return_value=when):
                result = self.event("before-action")
            self.assertEqual(result["checkpoint_required"], when >= 1900)
        with patch.object(hooks.time, "time", return_value=1901), \
                patch.object(hooks, "check_retained_context", side_effect=AssertionError("expired input read")), \
                patch.object(hooks, "object_at", side_effect=AssertionError("expired baseline read")):
            self.assertTrue(self.event("before-action")["checkpoint_required"])

    def test_expiry_during_evaluation_is_not_accepted(self):
        request = self.event("request")
        with patch.object(hooks.time, "time", return_value=1000):
            self.bind_session(request)
        clock = [1899]
        original = hooks.check_retained_context
        def crosses_expiry(*args):
            value = original(*args); clock[0] = 1900; return value
        with patch.object(hooks.time, "time", side_effect=lambda: clock[0]), \
                patch.object(hooks, "check_retained_context", side_effect=crosses_expiry):
            self.assertTrue(self.event("before-action")["checkpoint_required"])

    def test_slow_bind_starts_its_lifetime_after_validation(self):
        self.policy["binding_ttl_seconds"] = 1; self.write_policy()
        self.refresh_baseline()
        requested = self.event("request")
        clock = [1000]; original = hooks.selected_task
        def slow(*args):
            result = original(*args); clock[0] = 1002; return result
        with patch.object(hooks.time, "time", side_effect=lambda: clock[0]), \
                patch.object(hooks, "selected_task", side_effect=slow):
            self.assertEqual(self.bind_session(requested)["status"], "bound")
        with patch.object(hooks.time, "time", return_value=1002.5):
            self.assertEqual(self.event("before-action")["status"], "current-context")

    def test_native_evidence_expiry_during_evaluation_never_emits_a_block(self):
        self.observed(); self.bind_session()
        evidence = self.policy["native_evidence"]
        end = hooks.timestamp(evidence["expires_at"])
        original = hooks.selected_task; clock = [end-1]
        def expires(*args):
            result = original(*args); clock[0] = end; return result
        with patch.object(hooks.time, "time", side_effect=lambda: clock[0]), \
                patch.object(hooks, "selected_task", side_effect=expires):
            with self.assertRaisesRegex(ValueError, "native evidence expired"):
                self.event("completion")

    def test_native_evidence_expiry_during_final_baseline_read_is_rejected(self):
        self.observed(); self.bind_session()
        end = hooks.timestamp(self.policy["native_evidence"]["expires_at"])
        clock = [end-1]; reads = []; original = hooks.object_at
        def expires(*args, **kwargs):
            result = original(*args, **kwargs)
            reads.append(args[1])
            if len(reads) == 2:
                clock[0] = end
            return result
        with patch.object(hooks.time, "time", side_effect=lambda: clock[0]), \
                patch.object(hooks, "object_at", side_effect=expires):
            with self.assertRaisesRegex(ValueError, "native evidence expired"):
                self.event("completion")
        self.assertEqual(len(reads), 2)

    def test_expiry_crossed_while_waiting_for_lock_does_not_read_selected_context(self):
        import contextlib
        request = self.event("request")
        with patch.object(hooks.time, "time", return_value=1000):
            self.bind_session(request)
        clock = [1899]
        @contextlib.contextmanager
        def waited(*args, **kwargs):
            clock[0] = 1900
            yield
        with patch.object(hooks.time, "time", side_effect=lambda: clock[0]), \
                patch.object(hooks, "file_lock", side_effect=waited), \
                patch.object(hooks, "check_retained_context", side_effect=AssertionError("expired selected context read")):
            self.assertTrue(self.event("before-action")["checkpoint_required"])

    def test_ignore_policy_must_cover_locks_and_revocation_markers_too(self):
        ignore = self.target / ".ai/.gitignore"
        ignore.write_text(".runtime/lifecycle-hooks/*.json\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "all lifecycle state"):
            self.event("request")
        self.assertFalse((self.target / hooks.RUNTIME).exists())

    def test_recorded_binding_cannot_extend_the_configured_lifetime(self):
        self.bind_session()
        path = next((self.target / hooks.RUNTIME).glob("*.json"))
        state = json.loads(path.read_bytes())
        state["binding"]["expires_at"] = time.time() + 100000
        path.write_text(json.dumps(state), encoding="utf-8")
        with patch.object(hooks, "object_at", side_effect=AssertionError("unbounded lease content read")):
            self.assertTrue(self.event("before-action")["checkpoint_required"])
        self.assertEqual(hooks.session_status(self.target, "fixture-session")["status"], "review-required")

    def test_malformed_policy_fields_return_findings_in_registered_validation(self):
        for field in self.policy:
            for bad in (None, {}, [], True, 1, "unknown"):
                value = copy.deepcopy(self.policy); value[field] = bad
                failures = hooks.policy_failures(value)
                allowed_change = field in {"binding_ttl_seconds", "max_reminders"} and type(bad) is int and bad == 1
                if not allowed_change and (bad != self.policy[field] or type(bad) != type(self.policy[field])):
                    self.assertTrue(failures, (field, bad))
        self.policy["provider"] = {}; self.write_policy()
        checked = validator(self.target)
        checked.check_assistant_instruction_capabilities(None)
        self.assertIn("LIFECYCLE_HOOK_POLICY", [item.code for item in checked.findings])

    def test_policy_parser_parity_for_byte_limits_and_duplicate_fields(self):
        path = self.target / hooks.POLICY
        encoded = json.dumps(self.policy).encode()
        for size in (hooks.MAX_INPUT_BYTES-1, hooks.MAX_INPUT_BYTES, hooks.MAX_INPUT_BYTES+1):
            raw = encoded.ljust(size)
            path.write_bytes(raw)
            checked = validator(self.target); checked.check_lifecycle_hook_policy()
            errors = [row for row in checked.findings if row.level == "error"]
            self.assertEqual(bool(errors), size > hooks.MAX_INPUT_BYTES)
            if errors:
                with self.assertRaises(ValueError): hooks.load_policy(self.target)
            else:
                self.assertEqual(hooks.load_policy(self.target)[1], self.policy)
        path.write_bytes(encoded.replace(b'{', b'{"enabled":false,', 1))
        checked = validator(self.target); checked.check_lifecycle_hook_policy()
        self.assertIn("LIFECYCLE_HOOK_POLICY", [row.code for row in checked.findings])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            hooks.load_policy(self.target)

    def test_policy_file_safety_is_shared_with_registered_validation(self):
        import os
        path = self.target / hooks.POLICY
        other = self.target / "linked-policy.json"
        os.link(path, other)
        with self.assertRaises(ValueError):
            hooks.load_policy(self.target)
        checked = validator(self.target); checked.check_lifecycle_hook_policy()
        self.assertIn("LIFECYCLE_HOOK_POLICY", [row.code for row in checked.findings])

    def test_public_cli_and_installed_delegate_forward_events_without_executing_work(self):
        command = [sys.executable, "-B", str(ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"),
            "lifecycle-checkpoint", "--target", str(self.target), "--framework-source", str(ROOT),
            "--provider", "codex", "event", "--event", "UserPromptSubmit", "--native-output"]
        result = subprocess.run(command, input=json.dumps({"session_id": "cli-session", "prompt": "private input never retained"}),
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout), {})
        self.assertEqual(json.loads(result.stderr)["status"], "unbound")
        for path in (self.target / hooks.RUNTIME).glob("*.json"):
            self.assertNotIn("private input", path.read_text())
        result = subprocess.run(command, input='{"session_id":{}}', text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stderr)["status"], "unavailable")
        missing = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "lifecycle-checkpoint",
                   "--target", str(self.target / "absent"), "--provider", "codex", "event", "--event", "Stop", "--native-output"]
        result = subprocess.run(missing, input="{}", capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stderr)["status"], "unavailable")

    def test_native_completion_errors_never_request_retries_but_pre_action_errors_remain_distinct(self):
        for provider, event, expected in (("codex", "Stop", 0), ("claude", "Stop", 0),
                                        ("gemini", "AfterAgent", 0), ("cursor", "stop", 0),
                                        ("copilot", "agentStop", 0), ("codex", "PreToolUse", 0)):
            command = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "lifecycle-checkpoint",
                "--target", str(self.target), "--provider", provider, "event", "--event", event, "--native-output"]
            result = subprocess.run(command, input='{"session_id":{}}', capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, (provider, result.stderr))
            self.assertEqual(json.loads(result.stdout), {})
            self.assertEqual(json.loads(result.stderr)["status"], "unavailable")
        broken = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "lifecycle-checkpoint",
                  "--provider", "codex", "event", "--event", "Stop", "--native-output"]
        result = subprocess.run(broken, input="{}", capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), {})
        self.assertEqual(json.loads(result.stderr)["status"], "unavailable")
        self.observed()
        denied = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "lifecycle-checkpoint",
                  "--target", str(self.target), "--provider", "codex", "event", "--event", "PreToolUse", "--native-output"]
        result = subprocess.run(denied, input='{"session_id":{}}', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_extreme_runtime_expiry_values_fail_without_arithmetic_or_type_crashes(self):
        self.bind_session()
        path = next((self.target / hooks.RUNTIME).glob("*.json"))
        original = json.loads(path.read_bytes())
        command = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "lifecycle-checkpoint",
                   "--target", str(self.target), "--provider", "codex", "event", "--event", "PreToolUse"]
        for bad in (None, {}, [], True, "unknown", float("nan"), float("inf"), 10**1000):
            state = copy.deepcopy(original); state["binding"]["expires_at"] = bad
            path.write_text(json.dumps(state), encoding="utf-8")
            result = subprocess.run(command, input='{"session_id":"fixture-session"}', capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "unavailable")
            self.assertNotIn("Traceback", result.stderr)

    def test_public_bind_completion_and_interrupt_use_the_same_registered_path(self):
        self.observed()
        prefix = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "lifecycle-checkpoint",
            "--target", str(self.target), "--provider", "codex"]
        requested = self.event("request")
        bound = subprocess.run([*prefix, "bind", "--session-id", "fixture-session", "--request-id", requested["request_id"],
            "--baseline", self.baseline, "--task-id", "fixture-task"], capture_output=True, text=True)
        self.assertEqual(bound.returncode, 0, bound.stdout + bound.stderr)
        self.assertFalse(json.loads(bound.stdout)["authorization_granted"])
        stop = [*prefix, "event", "--event", "Stop", "--native-output"]
        result = subprocess.run(stop, input='{"session_id":"fixture-session"}', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["decision"], "block")
        interrupt = subprocess.run([*prefix, "checkpoint", "--event", "interrupt"],
            input='{"session_id":"fixture-session"}', capture_output=True, text=True)
        self.assertEqual(interrupt.returncode, 0, interrupt.stderr)
        result = subprocess.run(stop, input='{"session_id":"fixture-session"}', capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout), {})
        self.assertEqual(json.loads(result.stderr)["status"], "interrupted")

    def test_public_input_size_duplicate_keys_and_non_objects_fail_diagnostically(self):
        command = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "lifecycle-checkpoint",
            "--target", str(self.target), "--provider", "codex", "event", "--event", "UserPromptSubmit"]
        valid = '{"session_id":"bounded"}'
        for size in (hooks.MAX_INPUT_BYTES-1, hooks.MAX_INPUT_BYTES, hooks.MAX_INPUT_BYTES+1):
            result = subprocess.run(command, input=valid.ljust(size), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0 if size <= hooks.MAX_INPUT_BYTES else 2)
        for raw in ('[]', 'null', '{"session_id":"s","session_id":"other"}'):
            result = subprocess.run(command, input=raw, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["status"], "unavailable")


class LifecycleWireTests(unittest.TestCase):
    def test_all_declared_native_events_have_explicit_mapping(self):
        for provider, events in hooks.NATIVE_EVENTS.items():
            for native_event, event in events.items():
                payload = {"session_id": "s", "sessionId": "s", "conversation_id": "s", "status": "completed"}
                self.assertEqual(normalize(provider, native_event, payload)[0], event)

    def test_malformed_session_and_enum_inputs_do_not_crash(self):
        for provider, events in hooks.NATIVE_EVENTS.items():
            for native_event in events:
                for bad in (None, [], {}, True, 3):
                    with self.assertRaises(ValueError):
                        normalize(provider, native_event, {"session_id": bad, "sessionId": bad, "conversation_id": bad})
        for bad in (None, [], {}, 1, "false"):
            with self.assertRaises(ValueError):
                normalize("codex", "Stop", {"session_id": "s", "stop_hook_active": bad})
        for bad in (None, [], {}, True, 1, "unknown"):
            with self.assertRaises(ValueError):
                normalize("cursor", "stop", {"conversation_id": "s", "status": bad})

    def test_exact_cli_parsing_rejects_abbreviations_duplicates_and_missing_values(self):
        for args in (["--target", ".", "--tar", ".", "event", "--event", "request"],
                     ["--target", ".", "event", "--event", "request", "--event", "request"],
                     ["--target", ".", "event", "--event", "-h"]):
            with self.assertRaises(SystemExit):
                build_parser().parse_args(args)

    def test_native_wire_decisions_match_provider_specific_control_fields(self):
        result = hooks.decision("unfinished", "review", block=True); result["emit_native_block"] = True
        for provider, native in (("codex", "Stop"), ("claude", "Stop"), ("copilot", "agentStop")):
            self.assertEqual(native_output(provider, native, result)["decision"], "block")
        self.assertEqual(native_output("gemini", "AfterAgent", result)["decision"], "deny")
        self.assertIn("followup_message", native_output("cursor", "stop", result))
        self.assertEqual(native_output("cursor", "preToolUse", result)["permission"], "deny")
        result["emit_native_block"] = False
        self.assertEqual(native_output("codex", "Stop", result), {})


if __name__ == "__main__":
    unittest.main()

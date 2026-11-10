from __future__ import annotations

import contextlib
import copy
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tests")]
from active_task_fixture import ActiveTaskFixture
from finalization_preflight import inspect_finalization, preflight_report
from finalize_target_support import Step, execute_write_steps


class FinalizationPreflightTests(ActiveTaskFixture):
    def inspect(self, **kwargs):
        kwargs.setdefault("diff_ref", self.base)
        return inspect_finalization(self.target, task_id=self.task["task_id"], task_class=self.task["task_class"], **kwargs)

    def tree(self):
        return {p.relative_to(self.target).as_posix(): p.read_bytes() for p in self.target.rglob("*") if p.is_file()}

    def test_open_task_blocked_before_writes_and_never_acceptance(self):
        before = self.tree()
        report = preflight_report(self.inspect(require_task_acceptance=True))
        self.assertEqual(report["state"], "blocked")
        self.assertIn("TASK_ACCEPTANCE_CLOSURE", {f["code"] for f in report["findings"]})
        self.assertFalse(report["acceptance_eligible"])
        self.assertEqual(before, self.tree())

    def test_migration_staging_preserves_active_task_without_final_acceptance(self):
        report = preflight_report(self.inspect(migration_staging=True))
        self.assertEqual(report["state"], "ready-for-finalization", report)
        self.assertFalse(report["acceptance_eligible"])

    def test_current_closed_task_passes_canonical_selected_checks(self):
        self.close()
        with patch("target_adapter_validation.active_tasks._validate_current_result", side_effect=AssertionError("heavy result proof belongs to final acceptance")), \
                patch("target_adapter_validation.active_tasks._validate_selected_architecture_review", side_effect=AssertionError("heavy review belongs to final acceptance")):
            report = preflight_report(self.inspect(require_task_acceptance=True))
        self.assertEqual(report["state"], "ready-for-finalization", report["findings"])
        self.assertFalse(report["acceptance_eligible"])

    def test_malformed_closure_and_publication_use_canonical_schema(self):
        self.close()
        for mutation in ("preservation", "publication"):
            saved = copy.deepcopy(self.closure)
            if mutation == "preservation":
                del self.closure["engineering_evidence"]["preservation"]
            else:
                self.closure["delivery"]["publication"] = "published"
                self.closure["publication_evidence"] = []
            self.write_closure()
            report = preflight_report(self.inspect(require_task_acceptance=True))
            self.assertEqual(report["state"], "blocked", mutation)
            self.closure = saved

    def test_unrelated_history_does_not_load_a_missing_model(self):
        self.close()
        other = copy.deepcopy(self.task)
        other.update(task_id="other", operation_id="other", state="active", completion_evidence=None)
        other["problem_model"] = {"path": ".ai/.runtime/missing.json", "sha256": "a" * 64}
        self.write_index([self.task, other])
        result = preflight_report(self.inspect(require_task_acceptance=True))
        self.assertEqual(result["state"], "ready-for-finalization", result)
        self.assertNotIn(".ai/.runtime/missing.json", result["input_sha256"])

    def test_stale_selected_digest_blocks_without_projection_writes(self):
        self.close()
        (self.target / self.task["completion_evidence"]["path"]).write_text("{}", encoding="utf-8")
        result = preflight_report(self.inspect(require_task_acceptance=True))
        self.assertEqual(result["state"], "blocked")
        self.assertIn("ACTIVE_TASK_DIGEST", {f["code"] for f in result["findings"]})

    def test_changed_input_between_preflight_and_writer_blocks_before_builder(self):
        self.close()
        checked = self.inspect(require_task_acceptance=True)
        (self.target / self.task["completion_evidence"]["path"]).write_bytes(b"{}")
        with patch("finalize_target_support.step_outputs") as outputs:
            code, step, conflicts = execute_write_steps(self.target, [], preflight=checked)
        self.assertNotEqual(code, 0)
        self.assertEqual(step, "authoring-preflight-changed")
        outputs.assert_not_called()

    def test_peer_output_changed_during_successful_validation_is_preserved(self):
        output = self.target / ".ai/assistant/entry-packet.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"original")
        def run(*args, **kwargs):
            output.write_bytes(b"peer")
            return subprocess.CompletedProcess([], 0)
        steps = [Step("entry-packet", "unused", ()), Step("canonical-validation", "unused", ())]
        with patch("finalize_target_support.step_outputs", return_value={output: b"owned"}), contextlib.redirect_stderr(io.StringIO()):
            code, step, conflicts = execute_write_steps(self.target, steps, runner=run)
        self.assertNotEqual(code, 0)
        self.assertEqual(output.read_bytes(), b"peer")
        self.assertIn(".ai/assistant/entry-packet.json", conflicts)

    def test_full_validator_failure_rolls_back_owned_outputs(self):
        output = self.target / ".ai/assistant/entry-packet.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"original")
        steps = [Step("entry-packet", "unused", ()), Step("canonical-validation", "unused", ())]
        with patch("finalize_target_support.step_outputs", return_value={output: b"owned"}):
            code, step, conflicts = execute_write_steps(self.target, steps,
                runner=lambda *a, **kw: subprocess.CompletedProcess([], 7))
        self.assertEqual(code, 7)
        self.assertEqual(output.read_bytes(), b"original")
        self.assertEqual(conflicts, [])

    def test_public_cli_and_installed_delegate_block_open_task_before_writes(self):
        before = self.tree()
        for script in ("tools/alatyr.py", "templates/target/.ai/assistant/tools/alatyr_delegate.py"):
            args = [sys.executable, "-B", str(ROOT / script), "finalize-support", "--target", str(self.target), "--preflight",
                    "--task-id", self.task["task_id"], "--task-class", self.task["task_class"], "--require-task-acceptance"]
            if "templates/" in script:
                args.extend(["--framework-source", str(ROOT)])
            result = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(json.loads(result.stdout)["state"], "blocked")
            self.assertEqual(before, self.tree())

    def test_cli_mode_conflict_and_required_argument_pairing(self):
        for args in (["--write", "--preflight"], ["--preflight", "--require-task-acceptance"],
                     ["--preflight", "--require-current-change"]):
            result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "finalize-support", "--target", str(self.target), *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)

    def test_public_cli_positive_and_malformed_model_remain_read_only(self):
        self.close()
        command = [sys.executable, "-B", str(ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"),
                   "finalize-support", "--target", str(self.target), "--framework-source", str(ROOT), "--preflight",
                   "--task-id", self.task["task_id"], "--task-class", self.task["task_class"],
                   "--diff-ref", self.base, "--require-task-acceptance"]
        before = self.tree()
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertFalse(json.loads(result.stdout)["acceptance_eligible"])
        self.assertEqual(before, self.tree())
        self.model["task_binding"]["task_ids"] = None
        self.write_model()
        self.write_closure()
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("ANALYSIS_PROBLEM_MODEL_INVALID", result.stdout)


if __name__ == "__main__":
    unittest.main()

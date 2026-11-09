from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import delivery_control as delivery
import delivery_progress as progress
import delivery_receipts as receipts
import lifecycle_checkpoints as hooks
import request_brief
from target_adapter_validation.context import TargetRepositoryView
from tests import test_request_brief as request_fixtures

action_fixture = request_fixtures.action_fixture
delivery_fixture = request_fixtures.delivery_fixture
validation_fixture = request_fixtures.validation_fixture


NOW = 1794220800.0


def stamp(offset=0):
    return datetime.fromtimestamp(NOW + offset, timezone.utc).isoformat()


def store(target, path, value):
    raw = value if isinstance(value, bytes) else json.dumps(value).encode()
    destination = target / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    return {"path": path, "sha256": hashlib.sha256(raw).hexdigest()}


def adopt(target, brief, proof):
    history = delivery_fixture(brief)
    brief["delivery_control"]["execution_review"] = {
        "max_task_seconds": 100, "max_no_progress_seconds": 60, "max_observation_age_seconds": 30}
    history.update(schema_version=2, previous=None, progress={
        "started_at": stamp(-100), "last_progress_at": stamp(-60), "observed_at": stamp(),
        "phase": "implementation", "evidence": store(target, "evidence/progress.txt", b"A discriminating observation"),
        "obligation_ids": [proof]})
    return history


def add_attempt(target, history, *, result="passed", offset=0, index=1):
    history["previous"] = store(target, f"history/previous-{index}.json", history)
    output = store(target, f"evidence/run-{index}.txt", b"Actual result retained")
    receipt = {"schema_version": 1, "record_kind": "alatyr-delivery-run-receipt",
               "request_id": history["request_id"], "task_id": history["task_id"], "command_id": "bounded-check",
               "started_at": stamp(-20 + offset), "finished_at": stamp(-10 + offset), "result": result,
               "exit_code": 0 if result == "passed" else 1 if result == "failed" else None,
               "input_sha256": {"src/changed.py": "a" * 64}, "result_artifact": output}
    row = {"evidence_ref": output["path"], "result": result, "scope": "focused", "duration_seconds": 10,
           "expected_red_proof_id": None, "command_id": receipt["command_id"],
           "receipt": store(target, f"evidence/receipt-{index}.json", receipt)}
    history["attempts"].append(row)
    return receipt, row


class DeliveryProgressTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.target = Path(self.temporary.name)
        from tests.test_request_brief import brief_fixture
        self.brief = brief_fixture()
        self.history = adopt(self.target, self.brief, "proof")
        self.model = {"proof_obligations": [{"id": "proof", "required": True, "status": "passed"}]}
        self.action = action_fixture()

    def review(self, now=NOW, action=None):
        brief = request_brief.parse_brief(json.dumps(self.brief).encode())
        history = delivery.parse_history(json.dumps(self.history).encode(), brief)
        with_context = TargetRepositoryView(self.target)
        return progress.execution_review(with_context, self.target, brief, self.action if action is None else action,
                                         self.model, history, {}, history_parser=delivery.parse_history, now=now)

    def test_task_and_no_progress_below_at_above_boundaries(self):
        self.history["progress"]["observed_at"] = stamp(-1)
        self.history["progress"]["last_progress_at"] = stamp(-10)
        for seconds, fails in ((-1, False), (0, False), (.001, True)):
            with self.subTest(seconds=seconds):
                report, failures = self.review(NOW + seconds)
                self.assertEqual(bool(failures), fails)
                self.assertFalse(report["authorization_granted"])
                self.assertFalse(report["acceptance_granted"])
        self.brief["delivery_control"]["execution_review"]["max_task_seconds"] = 1000
        self.history["progress"]["last_progress_at"] = stamp(-60)
        for seconds, fails in ((-1, False), (0, False), (.001, True)):
            failures = self.review(NOW + seconds)[1]
            self.assertEqual(bool(failures), fails)
            if fails: self.assertIn("time since declared progress", ";".join(failures))

    def test_stale_observation_future_values_and_read_only_recovery(self):
        self.brief["delivery_control"]["execution_review"].update(max_task_seconds=1000, max_no_progress_seconds=1000)
        self.assertEqual(self.review(NOW + 30)[1], [])
        self.assertIn("observation age", ";".join(self.review(NOW + 30.001)[1]))
        self.history["progress"]["observed_at"] = stamp(1)
        self.assertIn("future", ";".join(self.review()[1]))
        report, failures = self.review(action=action_fixture(kind="answer", phase="inspect", paths=[]))
        self.assertEqual(failures, [])
        self.assertEqual(report["state"], "reassessment-required")

    def test_budget_exhaustion_blocks_validation_publish_and_completion_not_diagnosis(self):
        for action in (action_fixture(phase="publish", paths=[], effects=["origin/main"]),
                       action_fixture(kind="complete", phase="inspect", paths=[]),
                       action_fixture(phase="inspect", paths=[], validation=validation_fixture())):
            self.assertTrue(self.review(NOW + 1, action)[1])
        self.assertEqual(self.review(NOW + 1, action_fixture(phase="inspect", paths=[]))[1], [])

    def test_receipt_duration_identity_result_and_artifact_must_match(self):
        receipt, row = add_attempt(self.target, self.history)
        self.assertEqual(self.review()[1], [])
        for key, value in (("command_id", "other"), ("duration_seconds", 9), ("result", "failed"),
                           ("evidence_ref", "evidence/other.txt")):
            original = row[key]; row[key] = value
            with self.subTest(key=key): self.assertTrue(self.review()[1])
            row[key] = original
        for key, value in (("request_id", "other"), ("task_id", "other"), ("finished_at", stamp(-9.5))):
            changed = {**receipt, key: value}
            row["receipt"] = store(self.target, "evidence/receipt-1.json", changed)
            with self.subTest(key=key): self.assertTrue(self.review()[1])
        row["receipt"] = store(self.target, "evidence/receipt-1.json", receipt)
        (self.target / receipt["result_artifact"]["path"]).write_bytes(b"Modified result")
        self.assertIn("digest differs", ";".join(self.review()[1]))

    def test_previous_snapshot_preserves_attempts_clock_and_progress_binding(self):
        add_attempt(self.target, self.history)
        self.history["previous"] = store(self.target, "history/recorded.json", self.history)
        original = copy.deepcopy(self.history)
        for mutation in (lambda h: h["attempts"].clear(),
                         lambda h: h["progress"].update(started_at=stamp(-99)),
                         lambda h: h["progress"].update(last_progress_at=stamp(-59))):
            self.history = copy.deepcopy(original); mutation(self.history)
            self.assertTrue(self.review()[1])
        self.history = original
        self.history["progress"].update(last_progress_at=stamp(-59),
            evidence=store(self.target, "evidence/new-progress.txt", b"New observation, not timestamp renewal"))
        self.assertEqual(self.review()[1], [])

    def test_historical_receipt_inputs_are_not_revalidated_or_promoted_to_current_proof(self):
        add_attempt(self.target, self.history)
        store(self.target, "src/changed.py", b"Repaired after historical failure")
        self.assertEqual(self.review()[1], [])
        view = TargetRepositoryView(self.target)
        with patch.object(view, "read_bytes_result", wraps=view.read_bytes_result) as reads:
            progress.execution_review(view, self.target, self.brief, self.action, self.model, self.history, {},
                                      history_parser=delivery.parse_history, now=NOW)
        self.assertNotIn(self.target / "src/changed.py", [call.args[0] for call in reads.call_args_list])

    def test_receipt_enum_count_and_timestamp_malformed_matrix(self):
        valid, _ = add_attempt(self.target, self.history)
        for key in valid:
            for bad in ({}, [], None, True, 1.5, "unknown"):
                if key == "exit_code" and bad is None:
                    continue
                with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                    receipts.parse_receipt(json.dumps({**valid, key: bad}).encode())
        for key in self.history["progress"]:
            for bad in ({}, [], None, True, 1.5, "unknown"):
                changed = copy.deepcopy(self.history); changed["progress"][key] = bad
                with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                    delivery.parse_history(json.dumps(changed).encode(), self.brief)

    def test_duplicate_receipt_digest_and_missing_artifacts_fail(self):
        _, row = add_attempt(self.target, self.history)
        self.history["attempts"].append({**row, "evidence_ref": "evidence/another.txt"})
        self.assertIn("reuse a receipt", ";".join(self.review()[1]))
        self.history["attempts"].pop()
        (self.target / row["receipt"]["path"]).unlink()
        self.assertIn("missing or unreadable", ";".join(self.review()[1]))

    def test_progress_control_types_and_portable_ceiling_boundaries(self):
        control = self.brief["delivery_control"]["execution_review"]
        for key, maximum in (("max_task_seconds", 604800), ("max_no_progress_seconds", 86400),
                             ("max_observation_age_seconds", 3600)):
            for number in (1, maximum):
                progress.parse_review_control({**control, key: number})
            for bad in (0, maximum + 1, {}, [], None, True, 1.5, "unknown"):
                with self.subTest(key=key, value=bad), self.assertRaises(ValueError):
                    progress.parse_review_control({**control, key: bad})

    def test_result_artifact_byte_boundaries_include_aggregate_runs(self):
        import analysis_evidence
        receipt, row = add_attempt(self.target, self.history)
        size = len((self.target / receipt["result_artifact"]["path"]).read_bytes())
        for maximum in (size - 1, size, size + 1):
            with patch.object(analysis_evidence, "MAX_ARTIFACT_BYTES", maximum):
                if maximum < size:
                    self.assertTrue(self.review()[1])
                else:
                    self.assertEqual(self.review()[1], [])
        add_attempt(self.target, self.history, offset=-1, index=2)
        view = TargetRepositoryView(self.target)
        progress.execution_review(view, self.target, self.brief, self.action, self.model, self.history, {},
                                  history_parser=delivery.parse_history, now=NOW)
        total = view.retained_byte_count()
        self.assertGreater(total, 2*size)  # Metadata shares the same ceiling as result payloads.
        for maximum in (total - 1, total, total + 1):
            with patch.object(analysis_evidence, "MAX_EVIDENCE_BYTES", maximum):
                if maximum < total:
                    self.assertTrue(self.review()[1])
                else:
                    self.assertEqual(self.review()[1], [])

    def test_progress_aliases_do_not_renew_the_timer(self):
        self.history["previous"] = store(self.target, "history/earlier.json", self.history)
        self.history["progress"]["evidence"] = store(self.target, "evidence/copy.txt", b"A discriminating observation")
        self.history["progress"]["last_progress_at"] = stamp(-59)
        self.assertIn("new bound progress evidence", ";".join(self.review()[1]))

    def test_existing_legacy_attempts_remain_exact_and_new_unreceipted_rows_fail(self):
        legacy = {"schema_version": 1, "request_id": self.brief["request_id"], "task_id": self.brief["task_id"],
                  "attempts": [request_fixtures.attempt_fixture(result="passed")]}
        self.history["previous"] = store(self.target, "history/legacy.json", legacy)
        self.history["attempts"] = copy.deepcopy(legacy["attempts"])
        report, failures = self.review()
        self.assertEqual(failures, [])
        self.assertEqual(report["legacy_attempts"], 1)
        self.history["attempts"].append(request_fixtures.attempt_fixture(2, result="passed"))
        self.assertIn("new attempts require receipts", ";".join(self.review()[1]))

    def test_aggregate_cap_counts_previously_selected_inputs_without_duplicate_read_cost(self):
        view = TargetRepositoryView(self.target)
        selected = self.target / "selected-model.json"
        selected.write_bytes(b"123456")
        other = self.target / "other.json"
        other.write_bytes(b"abc")
        self.assertEqual(view.read_bytes_result(selected).value, b"123456")
        for limit in (8, 9, 10):
            fresh = TargetRepositoryView(self.target)
            fresh.read_bytes_result(selected)
            result = fresh.read_bytes_result(other, max_bytes=100, aggregate_max_bytes=limit)
            self.assertEqual(result.value is not None, limit >= 9)
            self.assertEqual(fresh.read_bytes_result(selected, aggregate_max_bytes=limit).value, b"123456")
        for invalid in (-1, True, 1.5, "unknown"):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                view.read_bytes_result(other, aggregate_max_bytes=invalid)

    def test_alias_buffers_and_growth_rechecks_stay_inside_the_allocation_budget(self):
        selected = self.target / "selected.txt"
        selected.write_bytes(b"1234")
        alias = self.target / "alias.txt"
        try:
            alias.symlink_to(selected)
        except OSError as exc:
            self.skipTest("symlinks unavailable: " + str(exc))
        view = TargetRepositoryView(self.target)
        self.assertEqual(view.read_bytes_result(selected, aggregate_max_bytes=4).value, b"1234")
        self.assertIsNone(view.read_bytes_result(alias, aggregate_max_bytes=4).value)
        self.assertEqual(view.retained_byte_count(), 4)
        selected.write_bytes(b"Changed and much larger than the accepted allocation")
        with patch.object(Path, "read_bytes", side_effect=AssertionError("unbounded finalize read")):
            self.assertTrue(view.finalize())

    def test_same_size_mutation_is_detected_by_bounded_stream_recheck(self):
        selected = self.target / "selected.txt"
        selected.write_bytes(b"1234")
        view = TargetRepositoryView(self.target)
        view.read_bytes_result(selected, aggregate_max_bytes=4)
        selected.write_bytes(b"4321")
        with patch.object(Path, "read_bytes", side_effect=AssertionError("unbounded finalize read")):
            self.assertTrue(view.finalize()[0].content_changed)

    def test_already_over_budget_view_still_uses_bounded_finalization(self):
        selected = self.target / "selected.txt"
        selected.write_bytes(b"1234")
        view = TargetRepositoryView(self.target)
        view.read_bytes_result(selected)
        self.assertIsNone(view.read_bytes_result(selected, aggregate_max_bytes=3).value)
        selected.write_bytes(b"Grown after the aggregate rejection")
        with patch.object(Path, "read_bytes", side_effect=AssertionError("unbounded finalize read")):
            self.assertTrue(view.finalize())

    def test_expected_red_and_interrupted_receipts_keep_the_existing_failure_gates(self):
        _, row = add_attempt(self.target, self.history, result="failed")
        row.update(result="expected-red", expected_red_proof_id="proof")
        self.model["proof_obligations"][0]["evidence_refs"] = [row["evidence_ref"]]
        self.assertEqual(self.review()[1], [])
        self.assertEqual(delivery.delivery_failures(self.brief, self.action, self.model, self.history), [])
        validation = action_fixture(phase="inspect", paths=[], validation=validation_fixture())
        row.update(result="interrupted", expected_red_proof_id=None)
        self.assertTrue(self.review()[1])  # A failed receipt cannot be relabelled as interrupted.
        self.assertTrue(delivery.delivery_failures(self.brief, validation, self.model, self.history))

    def test_receipt_window_rounding_and_valid_results(self):
        receipt, row = add_attempt(self.target, self.history)
        for elapsed in (0, .001, 1, 1.001, 86400):
            candidate = {**receipt, "started_at": stamp(-elapsed), "finished_at": stamp()}
            receipts.parse_receipt(json.dumps(candidate).encode())
        for elapsed in (-.001, 86400.001):
            with self.assertRaises(ValueError):
                receipts.parse_receipt(json.dumps({**receipt, "started_at": stamp(-elapsed), "finished_at": stamp()}).encode())
        for result, code in (("passed", 0), ("failed", 1), ("failed", 255), ("interrupted", None)):
            receipts.parse_receipt(json.dumps({**receipt, "result": result, "exit_code": code}).encode())
        for result, code in (("passed", 1), ("failed", 0), ("failed", 256), ("interrupted", 0)):
            with self.assertRaises(ValueError): receipts.parse_receipt(json.dumps({**receipt, "result": result, "exit_code": code}).encode())
        receipt.update(started_at=stamp(-.001), finished_at=stamp())
        row["duration_seconds"] = 1
        row["receipt"] = store(self.target, "evidence/receipt-1.json", receipt)
        self.assertEqual(self.review()[1], [])
        row["duration_seconds"] = 0
        self.assertIn("rounded-up", ";".join(self.review()[1]))

    def test_predecessor_identity_order_and_temporal_regression_fail_closed(self):
        add_attempt(self.target, self.history)
        add_attempt(self.target, self.history, index=2)
        prior = copy.deepcopy(self.history)
        self.history["previous"] = store(self.target, "history/prior.json", prior)
        baseline = copy.deepcopy(self.history)
        mutations = [lambda h: h["attempts"].reverse(),
                     lambda h: h["attempts"][0].update(duration_seconds=9),
                     lambda h: h["progress"].update(observed_at=stamp(-1)),
                     lambda h: h["progress"].update(last_progress_at=stamp(-61))]
        for mutation in mutations:
            self.history = copy.deepcopy(baseline); mutation(self.history)
            self.assertTrue(self.review()[1])
        self.history = baseline
        for key in ("request_id", "task_id"):
            changed = {**prior, key: "other"}
            self.history["previous"] = store(self.target, "history/prior.json", changed)
            self.assertTrue(self.review()[1])
        self.history["previous"] = None
        with self.assertRaisesRegex(ValueError, "preceding snapshot"): self.review()

    def test_legacy_and_null_controls_do_not_adopt_observations(self):
        self.history["schema_version"] = 1
        self.history.pop("progress"); self.history.pop("previous")
        with self.assertRaisesRegex(ValueError, "requires validation history schema 2"):
            delivery.parse_history(json.dumps(self.history).encode(), self.brief)
        self.brief["delivery_control"]["execution_review"] = None
        self.assertEqual(delivery.parse_history(json.dumps(self.history).encode(), self.brief), self.history)


class PublicDeliveryProgressTests(request_fixtures.RequestLifecycleFixture):
    def retain_delivery(self):
        from inspect_session_context import capture
        history_path = self.brief["delivery_control"]["validation_history"]
        history = json.loads((self.target/history_path).read_bytes())
        paths = [hooks.POLICY, ".ai/assistant/active-tasks.json", self.model_path.relative_to(self.target).as_posix(),
                 self.model["active_projection"]["path"], self.brief_path, "design.md", history_path,
                 history["progress"]["evidence"]["path"]]
        if history["previous"]: paths.append(history["previous"]["path"])
        for row in history["attempts"]:
            if "receipt" in row:
                paths.append(row["receipt"]["path"])
                paths.append(json.loads((self.target/row["receipt"]["path"]).read_bytes())["result_artifact"]["path"])
        # Selection is only a fixture superset; the real bind validates every byte and prior anchor.
        paths = sorted(set(paths))
        (self.target/self.baseline).write_text(json.dumps(capture(self.target, paths)[0]), encoding="utf-8")
        return self.bind_request()

    def setup_delivery(self):
        with patch(__name__ + ".NOW", time.time() - 1):
            history = adopt(self.target, self.brief, self.model["proof_obligations"][0]["id"])
        self.brief["delivery_control"]["execution_review"].update(max_task_seconds=1000, max_no_progress_seconds=1000,
                                                               max_observation_age_seconds=3600)
        self.write_brief()
        self.history_path = self.target/self.brief["delivery_control"]["validation_history"]
        self.history_path.write_text(json.dumps(history), encoding="utf-8")
        return history

    def test_bound_history_cannot_reset_or_select_a_fake_predecessor_and_valid_append_can_rebind(self):
        history = self.setup_delivery()
        self.assertEqual(self.retain_delivery()["status"], "bound")
        with patch(__name__ + ".NOW", time.time() - 1): add_attempt(self.target, history)
        self.history_path.write_text(json.dumps(history), encoding="utf-8")
        self.assertEqual(self.retain_delivery()["status"], "bound")
        self.assertEqual(self.event("before-action", alatyr_action=self.action())["status"], "request-consistent")
        recorded = copy.deepcopy(history)
        with patch(__name__ + ".NOW", time.time() - 1): reset = adopt(self.target, self.brief, self.model["proof_obligations"][0]["id"])
        self.history_path.write_text(json.dumps(reset), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "last bound snapshot"): self.retain_delivery()
        reset["previous"] = store(self.target, "history/fake-empty.json", reset)
        self.history_path.write_text(json.dumps(reset), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "last bound snapshot"): self.retain_delivery()
        with patch(__name__ + ".NOW", time.time() - 1): add_attempt(self.target, recorded, index=2)
        self.history_path.write_text(json.dumps(recorded), encoding="utf-8")
        self.assertEqual(self.retain_delivery()["status"], "bound")

    def test_bound_tampered_receipt_preserves_recovery_without_waiving_required_context(self):
        history = self.setup_delivery()
        with patch(__name__ + ".NOW", time.time() - 1): receipt, row = add_attempt(self.target, history)
        self.history_path.write_text(json.dumps(history), encoding="utf-8")
        self.retain_delivery()
        (self.target/row["receipt"]["path"]).write_bytes(b'{"malformed":true}')
        readonly = self.action(kind="answer", phase="inspect", paths=[])
        answer = hooks.review_request(self.target, self.brief_path, readonly)
        self.assertFalse(answer["checkpoint_required"], answer)
        self.assertEqual(answer["delivery_review"]["state"], "reassessment-required")
        bound = self.event("before-action", alatyr_action=readonly)
        self.assertFalse(bound["checkpoint_required"], bound)
        self.assertEqual(bound["delivery_review"]["state"], "reassessment-required")
        self.assertTrue(self.event("before-action", alatyr_action=self.action())["checkpoint_required"])
        original = (self.target/"design.md").read_bytes()
        (self.target/"design.md").write_bytes(b"Changed unrelated canonical context")
        self.assertTrue(self.event("before-action", alatyr_action=readonly)["checkpoint_required"])
        (self.target/"design.md").write_bytes(original)

    def test_resume_preserves_attempts_without_retagging_original_receipts(self):
        history = self.setup_delivery()
        with patch(__name__ + ".NOW", time.time() - 1): receipt, row = add_attempt(self.target, history)
        self.history_path.write_text(json.dumps(history), encoding="utf-8")
        self.retain_delivery()
        original_receipt = (self.target/row["receipt"]["path"]).read_bytes()
        resumed = self.event("resume")
        self.request = resumed
        self.brief["request_id"] = resumed["request_id"]
        history["previous"] = store(self.target, "history/before-resume.json", history)
        history["request_id"] = resumed["request_id"]
        self.history_path.write_text(json.dumps(history), encoding="utf-8")
        self.write_brief()
        self.assertEqual(self.retain_delivery()["status"], "bound")
        self.assertEqual(self.event("before-action", alatyr_action=self.action())["status"], "request-consistent")
        self.assertEqual((self.target/row["receipt"]["path"]).read_bytes(), original_receipt)

    def test_recovery_uses_only_prior_bound_artifact_paths_and_handles_multiple_missing_receipts(self):
        history = self.setup_delivery()
        with patch(__name__ + ".NOW", time.time() - 1):
            _, first = add_attempt(self.target, history)
            _, second = add_attempt(self.target, history, index=2)
        self.history_path.write_text(json.dumps(history), encoding="utf-8")
        self.retain_delivery()
        (self.target/first["receipt"]["path"]).unlink()
        (self.target/second["receipt"]["path"]).unlink()
        readonly = self.action(kind="answer", phase="inspect", paths=[])
        self.assertFalse(self.event("before-action", alatyr_action=readonly)["checkpoint_required"])
        # An invalid replacement cannot turn an unrelated retained file into a delivery omission.
        history["previous"] = None
        history["attempts"] = []
        history["progress"]["evidence"] = store(self.target, "design.md", b"Unrelated changed owner")
        self.history_path.write_text(json.dumps(history), encoding="utf-8")
        self.assertTrue(self.event("before-action", alatyr_action=readonly)["checkpoint_required"])

    def test_unadopted_path_performs_no_progress_or_receipt_review(self):
        with patch("delivery_progress.execution_review", side_effect=AssertionError("unselected extra reads")):
            self.assertEqual(hooks.review_request(self.target, self.brief_path, self.action())["status"], "request-consistent")
            history = delivery_fixture(self.brief)
            path = self.target / self.brief["delivery_control"]["validation_history"]
            path.write_text(json.dumps(history), encoding="utf-8")
            for present in (False, True):
                if present: self.brief["delivery_control"]["execution_review"] = None
                self.write_brief()
                self.assertEqual(hooks.review_request(self.target, self.brief_path, self.action())["status"], "request-consistent")
            self.policy["enabled"] = False; self.write_policy()
            path.unlink()
            self.assertEqual(self.event("before-action")["status"], "disabled")

    def test_every_delivery_artifact_must_be_retained_before_binding(self):
        from inspect_session_context import capture
        history = self.setup_delivery()
        with patch(__name__ + ".NOW", time.time() - 1): add_attempt(self.target, history)
        self.history_path.write_text(json.dumps(history), encoding="utf-8")
        report = hooks.review_request(self.target, self.brief_path, self.action(kind="answer", phase="inspect", paths=[]))
        fixed = [hooks.POLICY, ".ai/assistant/active-tasks.json", self.model_path.relative_to(self.target).as_posix(),
                 self.model["active_projection"]["path"], self.brief_path, "design.md"]
        for omitted in report["delivery_inputs"]:
            paths = fixed + [path for path in report["delivery_inputs"] if path != omitted]
            (self.target/self.baseline).write_text(json.dumps(capture(self.target, paths)[0]), encoding="utf-8")
            with self.subTest(omitted=omitted), self.assertRaisesRegex(ValueError, "exact validation history"):
                self.bind_request()
        self.assertEqual(self.retain_delivery()["status"], "bound")

    def test_new_receipts_cannot_override_focus_or_publication_authorization(self):
        with patch(__name__ + ".NOW", time.time() - 1):
            history = adopt(self.target, self.brief, self.model["proof_obligations"][0]["id"])
        self.brief.update(schema_version=3, focus_control="dependency-readiness")
        self.brief["delivery_control"]["execution_review"].update(max_task_seconds=1000, max_no_progress_seconds=1000,
                                                               max_observation_age_seconds=3600)
        self.model["execution_dependencies"] = [{"obligation_id": row["id"], "requires": []}
                                                 for row in self.model["proof_obligations"]]
        self.model["proof_obligations"][0]["status"] = "open"
        self.write_model(); self.write_index(); self.write_brief()
        (self.target / self.brief["delivery_control"]["validation_history"]).write_text(json.dumps(history), encoding="utf-8")
        sha = hashlib.sha256((self.target/self.brief_path).read_bytes()).hexdigest()
        action = self.action(brief_sha256=sha, obligation_ids=[self.model["proof_obligations"][0]["id"]])
        self.retain_delivery()
        self.assertFalse(self.event("before-action", alatyr_action=action)["checkpoint_required"])
        stale = hooks.review_request(self.target, self.brief_path, {**action, "brief_sha256": "0"*64})
        self.assertIn("brief digest", stale["reason"])
        publish = hooks.review_request(self.target, self.brief_path,
            {**action, "phase": "publish", "paths": [], "effects": ["origin/main"]})
        self.assertIn("ceiling", publish["reason"])

    def test_valid_receipts_pass_both_public_paths_and_mutations_fail(self):
        with patch(__name__ + ".NOW", time.time() - 1):
            history = adopt(self.target, self.brief, self.model["proof_obligations"][0]["id"])
            self.brief["delivery_control"]["execution_review"].update(max_task_seconds=1000, max_no_progress_seconds=1000,
                                                                   max_observation_age_seconds=3600)
            receipt, row = add_attempt(self.target, history)
        path = self.target / self.brief["delivery_control"]["validation_history"]
        path.write_text(json.dumps(history), encoding="utf-8")
        self.write_brief()
        for entry in (ROOT / "tools/alatyr.py", ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"):
            command = [sys.executable, "-B", str(entry), "lifecycle-checkpoint", "--target", str(self.target)]
            if entry.name == "alatyr_delegate.py": command += ["--framework-source", str(ROOT)]
            command += ["review", "--request-brief", self.brief_path]
            def run():
                return subprocess.run(command, input=json.dumps(self.action(kind="answer", phase="inspect", paths=[])), capture_output=True, text=True)
            valid = run()
            self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
            report = json.loads(valid.stdout)
            self.assertEqual(report["delivery_review"]["state"], "within-declared-bounds")
            self.assertIn(row["receipt"]["path"], report["delivery_inputs"])
            self.assertIn(receipt["result_artifact"]["path"], report["delivery_inputs"])
            self.assertFalse(report["acceptance_granted"])
            result_path = self.target / receipt["result_artifact"]["path"]
            original = result_path.read_bytes()
            result_path.write_bytes(b"Altered execution result")
            invalid = run()
            self.assertEqual(invalid.returncode, 0, invalid.stdout + invalid.stderr)
            invalid_report = json.loads(invalid.stdout)
            self.assertEqual(invalid_report["delivery_review"]["state"], "reassessment-required")
            self.assertIn("digest differs", ";".join(invalid_report["delivery_review"]["reasons"]))
            blocked = subprocess.run(command, input=json.dumps(self.action()), capture_output=True, text=True)
            self.assertEqual(blocked.returncode, 1, blocked.stdout + blocked.stderr)
            result_path.write_bytes(original)

    def test_public_cli_and_installed_delegate_preserve_recovery_and_do_not_write(self):
        history = adopt(self.target, self.brief, self.model["proof_obligations"][0]["id"])
        history["progress"].update(started_at=stamp(-1000), observed_at=stamp(-1000), last_progress_at=stamp(-1000))
        receipt_path = self.target / self.brief["delivery_control"]["validation_history"]
        receipt_path.write_text(json.dumps(history), encoding="utf-8")
        self.write_brief()
        action = self.action()
        before = {p.relative_to(self.target): p.read_bytes() for p in self.target.rglob("*") if p.is_file() and ".git" not in p.parts}
        for entry in (ROOT / "tools/alatyr.py", ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"):
            command = [sys.executable, "-B", str(entry), "lifecycle-checkpoint", "--target", str(self.target)]
            if entry.name == "alatyr_delegate.py": command += ["--framework-source", str(ROOT)]
            command += ["review", "--request-brief", self.brief_path]
            for candidate, code in ((action, 1), (self.action(kind="answer", phase="inspect", paths=[]), 0)):
                run = subprocess.run(command, input=json.dumps(candidate), capture_output=True, text=True)
                self.assertEqual(run.returncode, code, run.stdout + run.stderr)
                result = json.loads(run.stdout)
                self.assertEqual(result["delivery_review"]["state"], "reassessment-required")
                self.assertFalse(result["acceptance_granted"])
        after = {p.relative_to(self.target): p.read_bytes() for p in self.target.rglob("*") if p.is_file() and ".git" not in p.parts}
        self.assertEqual(before, after)

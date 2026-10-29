from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import inspect_session_context as session
from context_input_snapshot import ContextInputSnapshot
from tests.test_target_validator_installation_state import write_accepted_record, write_state


class SessionContextTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.target = Path(self.directory.name).resolve() / "target"
        self.target.mkdir()
        for name in session.TARGET_ANCHORS:
            path = self.target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"{}\n")
        write_state(self.target, "accepted")
        write_accepted_record(self.target)
        self.owner = self.target / ".ai/framework/selected-rule.md"
        self.owner.write_bytes(b"accepted rule\n")

    def command(self, *args):
        return subprocess.run([sys.executable, "-B", str(ROOT / "tools/alatyr.py"),
                               "session-context", "--target", str(self.target), *args],
                              capture_output=True, text=True, cwd=ROOT)

    def main_command(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["session-context", "--target", str(self.target), *args]), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = session.main()
        return SimpleNamespace(returncode=result, stdout=stdout.getvalue(), stderr=stderr.getvalue())

    def baseline(self, *paths):
        record, state, _ = session.capture(self.target, list(paths))
        self.assertEqual(state, "accepted")
        return record

    def save_baseline(self, record):
        path = self.target.parent / "baseline.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    def test_public_cli_candidate_then_current_and_same_version_owner_drift(self):
        output = self.target.parent / "first.json"
        initial = self.command("capture", "--context", ".ai/framework/selected-rule.md", "--output", str(output))
        self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
        payload = json.loads(initial.stdout)
        self.assertEqual(payload["status"], "baseline-candidate")
        self.assertFalse(payload["context_matches"])
        current = self.command("check", "--baseline", str(output))
        self.assertEqual(current.returncode, 0, current.stdout + current.stderr)
        self.assertEqual(json.loads(current.stdout)["status"], "current")
        retained = output.read_bytes()
        self.owner.write_bytes(b"revised rule with the same framework version\n")
        changed = self.command("check", "--baseline", str(output))
        self.assertEqual(changed.returncode, 1, changed.stdout)
        payload = json.loads(changed.stdout)
        self.assertEqual(payload["status"], "rehydration-required")
        self.assertEqual(payload["changed_paths"], [".ai/framework/selected-rule.md"])
        self.assertFalse(payload["authorization_granted"])
        self.assertFalse(payload["acceptance_granted"])
        self.assertEqual(output.read_bytes(), retained)

    def test_unselected_files_and_generation_metadata_do_not_change_identity(self):
        before = self.baseline(".ai/framework/selected-rule.md")
        (self.target / ".ai/support-state.json").write_text('{"source_revision":"other"}')
        (self.target / ".ai/framework/unselected.md").write_bytes(b"not loaded")
        (self.target / "product.txt").write_bytes(b"unrelated code")
        after = self.baseline(".ai/framework/selected-rule.md")
        self.assertEqual(before, after)

    def test_every_anchor_change_changes_identity(self):
        before = self.baseline()
        for name in sorted(session.TARGET_ANCHORS - {".ai/alatyr.yaml", session.STATE_PATH}):
            with self.subTest(path=name):
                path = self.target / name
                original = path.read_bytes()
                path.write_bytes(original + b"changed")
                after = self.baseline()
                self.assertNotEqual(before["fingerprint"], after["fingerprint"])
                path.write_bytes(original)

    def test_optional_entrypoint_absence_creation_and_removal_are_detected(self):
        absent = self.baseline()
        self.assertFalse((self.target / "AI_ASSISTANTS.md").exists())
        (self.target / "AI_ASSISTANTS.md").write_bytes(b"additional bootstrap route")
        present = self.baseline()
        self.assertNotEqual(absent["fingerprint"], present["fingerprint"])
        result = self.command("check", "--baseline", str(self.save_baseline(absent)))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["changed_paths"], ["AI_ASSISTANTS.md"])
        (self.target / "AI_ASSISTANTS.md").unlink()
        result = self.command("check", "--baseline", str(self.save_baseline(present)))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["changed_paths"], ["AI_ASSISTANTS.md"])

    def test_nonaccepted_state_blocks_even_matching_fingerprint(self):
        for state in ("scaffolded", "staged", "degraded"):
            with self.subTest(state=state):
                write_state(self.target, state)
                record = json.loads((self.target / session.STATE_PATH).read_bytes())
                next_state = "staged" if state == "staged" else "degraded"
                if state == "scaffolded":
                    record["transitions"] = record["transitions"][:1]
                else:
                    transition = copy.deepcopy(record["transitions"][-1])
                    transition.update(sequence=len(record["transitions"]) + 1,
                                      previous_state="accepted", next_state=next_state,
                                      reason="controlled-update" if state == "staged" else "blocking-drift")
                    record["transitions"].append(transition)
                record["current_state"] = state
                (self.target / session.STATE_PATH).write_text(json.dumps(record))
                captured, _, _ = session.capture(self.target, [])
                result = self.command("check", "--expected", captured["fingerprint"])
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertEqual(json.loads(result.stdout)["status"],
                                 "installation-degraded" if state == "degraded" else "update-in-progress")
                self.assertIn("authorized installer/updater", json.loads(result.stdout)["recovery"])
                write_accepted_record(self.target)

    def test_malformed_lifecycle_values_return_diagnostics_through_cli(self):
        original = json.loads((self.target / session.STATE_PATH).read_bytes())
        for field in ("current_state", "previous_state", "next_state", "validation"):
            for value in ({}, [], None, True, 7):
                with self.subTest(field=field, value=value):
                    record = copy.deepcopy(original)
                    if field == "current_state":
                        record[field] = value
                    elif field == "validation":
                        record["transitions"][-1][field]["status"] = value
                    else:
                        record["transitions"][-1][field] = value
                    (self.target / session.STATE_PATH).write_text(json.dumps(record))
                    result = self.main_command("capture")
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertEqual(json.loads(result.stdout)["status"], "unavailable")
                    self.assertNotIn("Traceback", result.stderr)

    def test_tampered_and_malformed_baselines_reject_without_crashing(self):
        original = self.baseline()
        for field in original:
            for value in ({}, [], None, True, 9, "unknown"):
                with self.subTest(field=field, value=value):
                    record = copy.deepcopy(original)
                    record[field] = value
                    with self.assertRaises(ValueError):
                        session.validate_baseline(record)
        original["inputs"][0]["sha256"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            session.validate_baseline(original)

    def test_wrong_root_and_source_contour_cannot_reuse_baseline(self):
        record = self.baseline()
        record["target_identity"] = "sha256:" + "0" * 64
        record["fingerprint"] = session.fingerprint(record)
        result = self.command("check", "--baseline", str(self.save_baseline(record)))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertFalse(json.loads(result.stdout)["same_target_and_contour"])
        source, state, _ = session.capture(ROOT, [], source_contour=True)
        self.assertEqual(state, "source-contour")
        self.assertEqual(session.validate_baseline(source), source)
        self.assertNotEqual(source["contour"], record["contour"])

    def test_custom_installation_state_route_is_preserved(self):
        custom = ".ai/assistant/custom-installation.json"
        (self.target / session.STATE_PATH).rename(self.target / custom)
        manifest = self.target / ".ai/alatyr.yaml"
        manifest.write_text(manifest.read_text().replace(session.STATE_PATH, custom))
        record = self.baseline()
        self.assertEqual(record["installation_state_path"], custom)
        result = self.command("check", "--baseline", str(self.save_baseline(record)))
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_missing_escaping_symlink_and_duplicate_paths_fail(self):
        for path in ("../outside", "/outside", "C:outside", "x\\y", "./file", "file//leaf", "missing.md", "bad\0path"):
            with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                session.capture(self.target, [path])
        with self.assertRaisesRegex(ValueError, "repeated"):
            session.capture(self.target, ["AGENTS.md", "AGENTS.md"])
        link = self.target / "link.md"
        outside = self.target.parent / "outside.md"
        outside.write_bytes(b"not selected")
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("host does not support symlinks")
        with self.assertRaises(ValueError):
            session.capture(self.target, ["link.md"])

    def test_mutation_during_capture_cannot_produce_a_baseline(self):
        original = ContextInputSnapshot.verify

        def changed(snapshot):
            self.owner.write_bytes(b"concurrent change")
            original(snapshot)

        with patch.object(ContextInputSnapshot, "verify", changed), self.assertRaisesRegex(ValueError, "changed"):
            session.capture(self.target, [".ai/framework/selected-rule.md"])

    def test_bounds_and_no_recursive_or_git_work_on_unchanged_path(self):
        for delta in (-1, 0, 1):
            count = len(session.TARGET_ANCHORS) + delta
            with self.subTest(limit=count), patch.object(session, "MAX_INPUTS", count):
                if delta < 0:
                    with self.assertRaises(ValueError): session.capture(self.target, [])
                else:
                    session.capture(self.target, [])
        for delta in (-1, 0, 1):
            size = 20 + delta
            self.owner.write_bytes(b"x" * size)
            with self.subTest(bytes=size), patch.object(session, "MAX_FILE_BYTES", 20):
                # Exercise file boundary using source anchors replaced with this file.
                with patch.object(session, "SOURCE_ANCHORS", frozenset({".ai/framework/selected-rule.md"})):
                    if delta > 0:
                        with self.assertRaises(ValueError): session.capture(self.target, [], source_contour=True)
                    else:
                        session.capture(self.target, [], source_contour=True)
        with patch.object(Path, "rglob", side_effect=AssertionError("recursive scan")), \
                patch.object(subprocess, "run", side_effect=AssertionError("subprocess")):
            first = self.baseline()
            second = self.baseline()
            self.assertEqual(first, second)

    def test_total_input_bytes_below_at_above_limit(self):
        _, _, measured = session.capture(self.target, [])
        for delta in (-1, 0, 1):
            with self.subTest(delta=delta), patch.object(session, "MAX_TOTAL_BYTES", measured["input_bytes"] + delta):
                if delta < 0:
                    with self.assertRaises(ValueError): session.capture(self.target, [])
                else:
                    session.capture(self.target, [])

    def test_cli_options_are_exact_and_single_bindings_are_not_silently_replaced(self):
        cases = [
            ["--target", str(self.target), "check", "--exp", "sha256:" + "0" * 64],
            ["--target", str(self.target), "check", "--expected", "-h"],
            ["--target", str(self.target), "capture", "--output", "first", "--output=second"],
            ["--target", str(self.target), "check", "--expected", "sha256:" + "0" * 64,
             "--baseline", "file"],
        ]
        for arguments in cases:
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                session.build_parser().parse_args(arguments)
            self.assertEqual(raised.exception.code, 2)

    def test_output_cannot_overwrite_inputs_or_baseline(self):
        baseline = self.save_baseline(self.baseline())
        for output in (self.target / "AGENTS.md", baseline):
            with self.subTest(output=output):
                before = output.read_bytes()
                result = self.command("check", "--baseline", str(baseline), "--output", str(output))
                self.assertEqual(result.returncode, 2)
                self.assertEqual(output.read_bytes(), before)

    def test_output_hardlinks_cannot_destroy_retained_evidence(self):
        baseline = self.save_baseline(self.baseline())
        for protected in (baseline, self.target / "AGENTS.md"):
            with self.subTest(protected=protected):
                alias = self.target.parent / "alias.json"
                try:
                    os.link(protected, alias)
                except OSError:
                    self.skipTest("host cannot create hardlinks")
                before = protected.read_bytes()
                result = self.command("check", "--baseline", str(baseline), "--output", str(alias))
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertEqual(protected.read_bytes(), before)
                alias.unlink()

    def test_capture_cannot_replace_an_existing_baseline(self):
        baseline = self.save_baseline(self.baseline())
        before = baseline.read_bytes()
        self.owner.write_bytes(b"new rule")
        result = self.command("capture", "--context", ".ai/framework/selected-rule.md", "--output", str(baseline))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(baseline.read_bytes(), before)

    def test_capture_report_byte_boundary_round_trips(self):
        output = self.target.parent / "capture.json"
        initial = self.command("capture", "--output", str(output))
        self.assertEqual(initial.returncode, 0, initial.stdout)
        size = len(output.read_bytes())
        self.assertNotIn("baseline", json.loads(initial.stdout))
        output.unlink()
        for delta in (-1, 0, 1):
            with self.subTest(limit=size + delta), patch.object(session, "MAX_BASELINE_BYTES", size + delta):
                arguments = ["session-context", "--target", str(self.target), "capture", "--output", str(output)]
                with patch.object(sys, "argv", arguments), contextlib.redirect_stdout(io.StringIO()):
                    result = session.main()
                if delta < 0:
                    self.assertEqual(result, 2)
                    self.assertFalse(output.exists())
                else:
                    self.assertEqual(result, 0)
                    arguments = ["session-context", "--target", str(self.target), "check", "--baseline", str(output)]
                    with patch.object(sys, "argv", arguments), contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(session.main(), 0)
                    output.unlink()

    @unittest.skipUnless(hasattr(os, "mkfifo"), "host has no FIFO support")
    def test_fifo_baseline_and_selected_input_do_not_block(self):
        fifo = self.target / "fifo"
        os.mkfifo(fifo)
        for arguments in (("check", "--baseline", str(fifo)), ("capture", "--context", "fifo")):
            for writer_open in (False, True):
                with self.subTest(arguments=arguments, writer_open=writer_open):
                    descriptor = os.open(fifo, os.O_RDWR | os.O_NONBLOCK) if writer_open else None
                    try:
                        result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/alatyr.py"),
                                                 "session-context", "--target", str(self.target), *arguments],
                                                capture_output=True, text=True, timeout=5)
                        self.assertEqual(result.returncode, 2, result.stdout)
                        self.assertEqual(json.loads(result.stdout)["status"], "unavailable")
                    finally:
                        if descriptor is not None:
                            os.close(descriptor)

    def test_invalid_yaml_and_changed_retained_baseline_are_unavailable(self):
        manifest = self.target / ".ai/alatyr.yaml"
        original = manifest.read_bytes()
        manifest.write_bytes(b"installation: [unclosed")
        result = self.command("capture")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        manifest.write_bytes(original)
        baseline = self.save_baseline(self.baseline())
        capture = session.capture

        def replace_baseline(*args, **kwargs):
            current = capture(*args, **kwargs)
            baseline.write_bytes(b"{}")
            return current

        with patch.object(sys, "argv", ["session-context", "--target", str(self.target), "check", "--baseline", str(baseline)]), \
                patch.object(session, "capture", replace_baseline), contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(session.main(), 2)
        self.assertIn("baseline changed", stdout.getvalue())

    def test_registered_continuity_check_rejects_missing_checkpoint_contract(self):
        from target_adapter_validation.harness_scenarios.common import validator
        from target_adapter_validation.session_continuity import validate_session_continuity
        policy_path = self.target / ".ai/assistant/policies/session-continuity.json"
        policy = json.loads((ROOT / "templates/target/.ai/assistant/policies/session-continuity.json").read_bytes())
        for field in policy["installed_context"]:
            with self.subTest(field=field):
                changed = copy.deepcopy(policy)
                changed["installed_context"].pop(field)
                policy_path.write_text(json.dumps(changed))
                checked = validator(self.target)
                validate_session_continuity(checked)
                self.assertTrue(any(f.code == "SESSION_CONTEXT_POLICY" for f in checked.findings))

    def test_installed_delegate_invokes_actual_canonical_helper(self):
        delegate = ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"
        initial = subprocess.run([sys.executable, "-B", str(delegate), "session-context",
                                  "--target", str(self.target), "--framework-source", str(ROOT),
                                  "capture", "--context", ".ai/framework/selected-rule.md"],
                                 capture_output=True, text=True)
        self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
        expected = json.loads(initial.stdout)["fingerprint"]
        current = subprocess.run([sys.executable, "-B", str(delegate), "session-context",
                                  "--target", str(self.target), "--framework-source", str(ROOT),
                                  "check", "--expected", expected, "--context", ".ai/framework/selected-rule.md"],
                                 capture_output=True, text=True)
        self.assertEqual(current.returncode, 0, current.stdout + current.stderr)
        self.assertEqual(json.loads(current.stdout)["status"], "current")


if __name__ == "__main__":
    unittest.main()

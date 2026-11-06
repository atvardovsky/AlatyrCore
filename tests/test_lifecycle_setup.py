from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from lifecycle_checkpoints import EVENTS, NATIVE_EVENTS
from lifecycle_policy import POLICY, load_policy, policy_failures
from lifecycle_setup import setup_plan
from run_lifecycle_checkpoint import build_parser


class LifecycleSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.target = Path(self.temp.name).resolve()

    def existing(self, **changes):
        _, value = load_policy(ROOT / "templates/target")
        value = copy.deepcopy(value)
        value.update(changes)
        path = self.target / POLICY
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(value, indent=4).encode()
        path.write_bytes(raw)
        return value, raw

    def native(self, provider="codex", **kwargs):
        return setup_plan(self.target, provider, "new", native_setup_approved=True,
            client_version="fixture-client-1.0", config_path=".client/hooks.json", **kwargs)

    def test_new_default_is_enabled_nonblocking_and_does_not_write(self):
        result = setup_plan(self.target, "procedural", "new")
        policy = result["policy_candidate"]
        self.assertEqual(policy, load_policy(ROOT / "templates/target")[1])
        self.assertTrue(policy["enabled"])
        self.assertEqual((policy["provider"], policy["mode"], policy["max_reminders"]), ("procedural", "observe", 0))
        self.assertEqual(policy["native_evidence"]["state"], "unverified")
        self.assertFalse(policy["request_guard"]["required"])
        self.assertEqual(result["callbacks"], [])
        self.assertEqual(result["setup_disposition"], "procedural-fallback")
        self.assertEqual(list(self.target.iterdir()), [])
        for flag in ("authorization_granted", "acceptance_granted", "configuration_write_performed"):
            self.assertFalse(result[flag])
        self.assertEqual(result["native_hook_status"], "not-established")

    def test_native_routes_need_explicit_setup_approval_not_provider_selection(self):
        for provider in NATIVE_EVENTS:
            with self.subTest(provider=provider):
                result = setup_plan(self.target, provider, "new")
                self.assertEqual(result["policy_candidate"]["provider"], "procedural")
                self.assertEqual(result["callbacks"], [])
                self.assertEqual(result["setup_disposition"], "procedural-fallback")

    def test_all_proposed_event_arguments_use_the_canonical_parser_and_mapping(self):
        for provider, events in NATIVE_EVENTS.items():
            with self.subTest(provider=provider):
                result = self.native(provider, interpreter="python3")
                policy = result["policy_candidate"]
                self.assertEqual(policy["provider"], provider)
                self.assertEqual(policy["mode"], "observe")
                self.assertEqual(policy["max_reminders"], 0)
                self.assertEqual(policy_failures(policy), [])
                self.assertEqual({x["event"] for x in result["callbacks"]}, set(events))
                for row in result["callbacks"]:
                    argv = row["argv"]
                    self.assertEqual(argv[:3], ["python3", ".ai/assistant/tools/alatyr_delegate.py", "lifecycle-checkpoint"])
                    parsed = build_parser().parse_args(argv[3:])
                    self.assertEqual((parsed.provider, parsed.action, parsed.event, parsed.native_output), (provider, "event", row["event"], True))
                    self.assertEqual(row["checkpoint"], events[row["event"]])
                    self.assertEqual(row["selection"], "verified-mutating-tools-only" if row["checkpoint"] in {"before-action", "after-change"} else "session-event")
                self.assertEqual(set(result["procedural_events"]), EVENTS - set(events.values()))
                self.assertEqual(result["native_hook_status"], "not-established")
        self.assertIn("interrupt", self.native("claude")["procedural_events"])
        self.assertEqual(list(self.target.iterdir()), [])

    def test_missing_or_unresolved_native_setup_bindings_are_rejected(self):
        complete = {"native_setup_approved": True, "client_version": "client-1", "config_path": ".client/hooks.json"}
        for changes in ({"client_version": None}, {"config_path": None}, {"client_version": "unknown"}, {"client_version": "{CLIENT}"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                setup_plan(self.target, "codex", "new", **(complete | changes))
        with self.assertRaises(ValueError):
            setup_plan(self.target, "procedural", "new", **complete)

    def test_updates_preserve_explicit_disable_and_custom_settings_byte_for_byte(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                value, raw = self.existing(enabled=enabled, provider="claude", max_reminders=3)
                for kind in ("new", "update"):
                    result = setup_plan(self.target, "codex", kind, native_setup_approved=True,
                        client_version="new-client", config_path=".client/new.json")
                    self.assertEqual(result["policy_action"], "preserve")
                    self.assertEqual(result["policy_candidate"], value)
                    self.assertEqual(result["existing_policy_sha256"], hashlib.sha256(raw).hexdigest())
                    self.assertEqual(result["callbacks"], [])
                    self.assertEqual((self.target / POLICY).read_bytes(), raw)

    def test_update_with_absent_policy_never_adopts_fresh_defaults(self):
        result = setup_plan(self.target, "codex", "update", native_setup_approved=True,
            client_version="new-client", config_path=".client/hooks.json")
        self.assertEqual(result["setup_disposition"], "adoption-decision-required")
        self.assertEqual(result["policy_action"], "none")
        self.assertIsNone(result["policy_candidate"])
        self.assertEqual(result["callbacks"], [])
        self.assertEqual(list(self.target.iterdir()), [])

    def test_existing_native_definitions_are_not_modified(self):
        path = self.target / ".client/hooks.json"
        path.parent.mkdir()
        raw = b'{"unrelated-hook":"keep-exactly"}'
        path.write_bytes(raw)
        result = self.native()
        self.assertEqual(result["setup_disposition"], "native-setup-proposed")
        self.assertEqual(path.read_bytes(), raw)

    def test_invalid_existing_policy_is_not_repaired_or_replaced(self):
        self.existing()
        path = self.target / POLICY
        for raw in (b"not-json", b"{}", b'{"schema_version":true}', b'{"enabled":false,"enabled":true}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                path.write_bytes(raw)
                setup_plan(self.target, "procedural", "update")
            self.assertEqual(path.read_bytes(), raw)

    def test_existing_expired_evidence_does_not_turn_into_new_consent(self):
        value, _ = self.existing(provider="codex")
        value["native_evidence"] = {"state": "observed", "client_version": "client-1", "source": "review-1",
            "verified_at": "2000-01-01T00:00:00Z", "expires_at": "2000-01-02T00:00:00Z"}
        raw = json.dumps(value).encode()
        (self.target / POLICY).write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "expired"):
            setup_plan(self.target, "procedural", "update")
        self.assertEqual((self.target / POLICY).read_bytes(), raw)

    def test_invalid_routes_interpreters_and_config_paths_fail_without_writes(self):
        for provider in ("opencode", "codex-cloud", "copilot-extension", "unknown", {}, None):
            with self.subTest(provider=provider), self.assertRaises(ValueError):
                setup_plan(self.target, provider, "new")
        for path in ("../global.json", "/outside/hooks.json", ".git/config", ".git", "C:/global.json", "CON", "client/*"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                setup_plan(self.target, "codex", "new", native_setup_approved=True, client_version="client-1", config_path=path)
        for interpreter in ("sh -c", "python --eval", "", []):
            with self.subTest(interpreter=interpreter), self.assertRaises(ValueError):
                self.native(interpreter=interpreter)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_config_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            link = self.target / "client"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest("symlink creation unavailable: " + str(exc))
            with self.assertRaises((ValueError, OSError)):
                setup_plan(self.target, "codex", "new", native_setup_approved=True,
                    client_version="client-1", config_path="client/hooks.json")

    def test_source_default_drift_fails_instead_of_weakening_the_plan(self):
        real = load_policy
        def changed(target):
            raw, value = real(target)
            if target == ROOT / "templates/target":
                value["enabled"] = False
            return raw, value
        with patch("lifecycle_setup.load_policy", side_effect=changed), self.assertRaisesRegex(ValueError, "source hook default"):
            setup_plan(self.target, "procedural", "new")

    def test_actual_source_cli_and_installed_delegate_match_without_stdin_or_writes(self):
        common = ["--target", str(self.target), "--provider", "codex", "setup-plan", "--installation-kind", "new",
                  "--native-setup-approved", "--client-version", "fixture-client-1", "--config-path", ".client/hooks.json"]
        commands = [[sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "lifecycle-checkpoint", *common],
                    [sys.executable, "-B", str(ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"),
                     "lifecycle-checkpoint", "--framework-source", str(ROOT), *common]]
        observed = []
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True, input="", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            observed.append(json.loads(result.stdout))
        self.assertEqual(observed[0], observed[1])
        self.assertEqual(list(self.target.iterdir()), [])

    def test_setup_parser_errors_cannot_become_neutral_native_success(self):
        prefix = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "lifecycle-checkpoint", "--target", str(self.target), "setup-plan"]
        for arguments in ([], ["--installation-kind", "new", "--native-output"], ["--installation-kind", "new", "--config-path"],
                          ["--installation-kind", "new", "--installation-kind", "update"]):
            with self.subTest(arguments=arguments):
                result = subprocess.run(prefix + arguments, capture_output=True, text=True, input="", timeout=30)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

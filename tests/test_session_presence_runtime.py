from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from session_presence_contract import DEFAULT_PRESENCE, MAX_BYTES, POLICY_PATH
from session_presence_store import git_identity, load_registry, operate, registry_lock


class PresenceRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.target = self.root / "target with spaces"
        self.target.mkdir()
        self.git("init")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-m", "fixture")
        self.set_policy(True)

    def git(self, *arguments):
        return subprocess.run(["git", "-C", str(self.target), *arguments], check=True, capture_output=True, text=True)

    def set_policy(self, enabled):
        path = self.target / POLICY_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"presence": {**DEFAULT_PRESENCE, "enabled": enabled}}), encoding="utf-8")

    def register(self, target=None, **kwargs):
        return operate(target or self.target, "register", write=True, task="Review API", scope=["api"], **kwargs)

    def cli(self, *args, target=None, delegate=False):
        command = [sys.executable, str(ROOT / "tools/alatyr.py"), "session-presence", "--target", str(target or self.target), *args]
        if delegate:
            command = [sys.executable, str(ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"), "session-presence", "--target", str(target or self.target), "--framework-source", str(ROOT), *args]
        return subprocess.run(command, capture_output=True, text=True)

    def test_status_and_disabled_operations_have_no_side_effects(self):
        _, hub, _ = git_identity(self.target)
        result = operate(self.target, "status")
        self.assertEqual(result["sessions"], [])
        self.assertFalse(hub.exists())
        self.set_policy(False)
        with patch("session_presence_store.git_identity", side_effect=AssertionError("disabled performs Git discovery")):
            self.assertFalse(operate(self.target, "status")["enabled"])
            with self.assertRaisesRegex(ValueError, "disabled"):
                self.register()
        self.assertFalse(hub.exists())
        (self.target / POLICY_PATH).unlink()
        self.assertFalse(operate(self.target, "status")["enabled"])

    def test_uid_lifecycle_cas_foreign_worktree_and_unrelated_conservation(self):
        one = self.register()
        two = self.register(parent_uid=one["session_uid"])
        before = {x["session_uid"]: x for x in operate(self.target, "status")["sessions"]}
        changed = operate(self.target, "update", write=True, session_uid=one["session_uid"], expected_version=1, task="Review tests", scope=["tests"])
        self.assertEqual(changed["version"], 2)
        with self.assertRaisesRegex(ValueError, "version changed"):
            operate(self.target, "leave", write=True, session_uid=one["session_uid"], expected_version=1)
        operate(self.target, "leave", write=True, session_uid=one["session_uid"], expected_version=2)
        after = operate(self.target, "status")["sessions"]
        self.assertEqual(after, [before[two["session_uid"]]])
        operate(self.target, "leave", write=True, session_uid=two["session_uid"], expected_version=1)
        self.assertEqual(operate(self.target, "status")["sessions"], [])
        self.assertNotEqual(one["session_uid"], two["session_uid"])

    def test_actual_worktrees_share_hub_and_clones_do_not(self):
        other = self.root / "linked worktree"
        self.git("worktree", "add", "--detach", str(other), "HEAD")
        path = other / POLICY_PATH
        path.parent.mkdir(parents=True)
        path.write_bytes((self.target / POLICY_PATH).read_bytes())
        one = self.register()
        two = self.register(other)
        self.assertEqual(one["registry"], two["registry"])
        self.assertEqual(len(operate(other, "status")["sessions"]), 2)
        with self.assertRaisesRegex(ValueError, "different worktree"):
            operate(other, "leave", write=True, session_uid=one["session_uid"], expected_version=1)
        clone = self.root / "clone"
        subprocess.run(["git", "clone", str(self.target), str(clone)], capture_output=True, check=True)
        clone_policy = clone / POLICY_PATH
        clone_policy.parent.mkdir(parents=True)
        clone_policy.write_bytes(path.read_bytes())
        self.assertNotEqual(git_identity(clone)[1], git_identity(self.target)[1])
        self.assertEqual(operate(clone, "status")["sessions"], [])
        with patch.dict(os.environ, {"GIT_DIR": str(clone / ".git"), "GIT_WORK_TREE": str(clone)}):
            self.assertEqual(git_identity(self.target)[0], self.target.resolve())

    def test_parallel_cli_registration_and_completion_preserve_every_participant(self):
        other = self.root / "parallel worktree"
        self.git("worktree", "add", "--detach", str(other), "HEAD")
        policy = other / POLICY_PATH
        policy.parent.mkdir(parents=True)
        policy.write_bytes((self.target / POLICY_PATH).read_bytes())
        targets = [self.target if i % 2 else other for i in range(8)]
        commands = [[sys.executable, str(ROOT / "tools/alatyr.py"), "session-presence", "--target", str(targets[i]), "register", "--write", "--task", str(i), "--scope", "api"] for i in range(8)]
        children = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for command in commands]
        entries = []
        for child in children:
            output, error = child.communicate(timeout=30)
            self.assertEqual(child.returncode, 0, error)
            entries.append(json.loads(output))
        self.assertEqual(len(operate(self.target, "status")["sessions"]), 8)
        children = [subprocess.Popen([sys.executable, str(ROOT / "tools/alatyr.py"), "session-presence", "--target", str(targets[i]), "leave", "--write", "--session-uid", entry["session_uid"], "--expected-version", "1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i, entry in enumerate(entries)]
        for child in children:
            _, error = child.communicate(timeout=30)
            self.assertEqual(child.returncode, 0, error)
        self.assertEqual(operate(self.target, "status")["sessions"], [])

    def test_competing_same_uid_updates_accept_only_one_version(self):
        one = self.register()
        base = [sys.executable, str(ROOT / "tools/alatyr.py"), "session-presence", "--target", str(self.target), "update", "--write", "--session-uid", one["session_uid"], "--expected-version", "1", "--scope", "api"]
        children = [subprocess.Popen([*base, "--task", name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for name in ("First", "Second")]
        results = []
        for child in children:
            child.communicate(timeout=30)
            results.append(child.returncode)
        self.assertEqual(sorted(results), [0, 1])
        entry = operate(self.target, "status")["sessions"][0]
        self.assertEqual(entry["version"], 2)
        self.assertIn(entry["task"], ("First", "Second"))

    def test_capacity_rejection_preserves_records_and_allows_update_leave(self):
        import uuid
        from session_presence_contract import MAX_SESSIONS, encoded_registry
        self.register()
        _, hub, repository_id = git_identity(self.target)
        path = hub / "sessions.json"
        value = load_registry(hub, repository_id)
        sample = next(iter(value["sessions"].values()))
        for _ in range(MAX_SESSIONS - 2):
            identity = str(uuid.uuid4())
            value["sessions"][identity] = {**sample, "session_uid": identity}
        path.write_bytes(encoded_registry(value, repository_id))
        last = self.register()
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "capacity"):
            self.register()
        self.assertEqual(path.read_bytes(), before)
        operate(self.target, "update", write=True, session_uid=last["session_uid"], expected_version=1, task="Still active", scope=["api"])
        operate(self.target, "leave", write=True, session_uid=last["session_uid"], expected_version=2)
        self.assertTrue(self.register()["session_uid"])

    def test_crashed_lock_holder_does_not_block_next_writer(self):
        _, hub, _ = git_identity(self.target)
        script = "import sys,time; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from session_presence_store import registry_lock;\nwith registry_lock(Path(sys.argv[2])):\n print('locked',flush=True); time.sleep(30)"
        child = subprocess.Popen([sys.executable, "-c", script, str(ROOT / "tools"), str(hub)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: child.poll() is None and child.kill())
        self.assertEqual(child.stdout.readline().strip(), "locked")
        with self.assertRaisesRegex(ValueError, "timed out"):
            with registry_lock(hub, timeout=0.05):
                self.fail("lock unexpectedly acquired")
        child.kill()
        child.communicate(timeout=10)
        self.assertTrue(self.register()["session_uid"])

    def test_windows_lock_byte_is_initialized_only_after_acquisition(self):
        from types import SimpleNamespace
        _, hub, _ = git_identity(self.target)
        calls = []

        def locking(descriptor, operation, count):
            if operation == 1:
                self.assertEqual(os.fstat(descriptor).st_size, 0)
            calls.append(operation)

        windows = SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=locking)
        with patch("session_presence_store.os.name", "nt"), patch.dict(sys.modules, {"msvcrt": windows}):
            with registry_lock(hub):
                self.assertEqual((hub / "registry.lock").read_bytes(), b"\0")
                self.assertEqual(calls, [1])
        self.assertEqual(calls, [1, 2])

    def test_update_preserves_omitted_activity(self):
        one = self.register(activity="editing")
        operate(self.target, "update", write=True, session_uid=one["session_uid"], expected_version=1, task="Implement tests", scope=["tests"])
        self.assertEqual(operate(self.target, "status")["sessions"][0]["activity"], "editing")

    def test_windows_transient_reader_handle_conflict_retries_atomic_replace(self):
        from session_presence_store import save_registry
        self.register()
        _, hub, repository_id = git_identity(self.target)
        value = load_registry(hub, repository_id)
        original_replace = os.replace
        attempts = []

        def replacement(source, destination):
            attempts.append(1)
            if len(attempts) < 3:
                raise PermissionError("reader still holds handle")
            original_replace(source, destination)

        with registry_lock(hub), patch("session_presence_store.os.name", "nt"), patch("session_presence_store.os.replace", side_effect=replacement):
            save_registry(hub, value, repository_id)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(load_registry(hub, repository_id), value)

    def test_malformed_registry_preserved_and_atomic_write_failure_cleaned(self):
        self.register()
        _, hub, _ = git_identity(self.target)
        path = hub / "sessions.json"
        original = path.read_bytes()
        for raw in (b'[]', b'{"schema_version":1,"schema_version":1}', b'\xff', b' ' * (MAX_BYTES + 1)):
            path.write_bytes(raw)
            result = self.cli("register", "--write", "--task", "Review", "--scope", "api")
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(path.read_bytes(), raw)
        path.write_bytes(original)
        with patch("session_presence_store.os.replace", side_effect=OSError("replacement failed")):
            with self.assertRaises(OSError):
                self.register()
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(list(hub.glob(".sessions-*")))

    def test_stale_and_future_records_are_reported_not_pruned(self):
        self.register()
        _, hub, _ = git_identity(self.target)
        path = hub / "sessions.json"
        value = json.loads(path.read_bytes())
        entry = next(iter(value["sessions"].values()))
        for updated, expected in (("2020-01-01T00:00:00Z", "stale"), ("2099-01-01T00:00:00Z", "clock-uncertain")):
            entry["started_at"] = "2020-01-01T00:00:00Z"
            entry["updated_at"] = updated
            path.write_text(json.dumps(value), encoding="utf-8")
            before = path.read_bytes()
            self.assertEqual(operate(self.target, "status")["sessions"][0]["freshness"], expected)
            self.assertEqual(path.read_bytes(), before)

    def test_unsafe_files_and_invalid_policy_never_repair_runtime(self):
        self.register()
        _, hub, _ = git_identity(self.target)
        registry = hub / "sessions.json"
        original = registry.read_bytes()
        external = self.root / "external.json"
        external.write_bytes(original)
        registry.unlink()
        try:
            registry.symlink_to(external)
        except OSError:
            self.skipTest("host does not permit test symlinks")
        with self.assertRaises(ValueError):
            self.register()
        self.assertEqual(external.read_bytes(), original)
        registry.unlink()
        os.link(external, registry)
        with self.assertRaises(ValueError):
            operate(self.target, "status")
        registry.unlink()
        registry.write_bytes(original)
        policy_path = self.target / POLICY_PATH
        for raw in (b'[]', b'{"presence":null}', b'{"presence":{"enabled":true}}'):
            policy_path.write_bytes(raw)
            result = self.cli("register", "--write", "--task", "Review", "--scope", "api")
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(registry.read_bytes(), original)

    def test_existing_status_does_not_modify_files_or_create_lock(self):
        self.register()
        _, hub, _ = git_identity(self.target)
        (hub / "registry.lock").unlink()
        before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in hub.iterdir()}
        self.assertEqual(len(operate(self.target, "status")["sessions"]), 1)
        after = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in hub.iterdir()}
        self.assertEqual(before, after)

    def test_enabled_non_git_target_fails_without_runtime_creation(self):
        other = self.root / "non-git"
        policy_path = other / POLICY_PATH
        policy_path.parent.mkdir(parents=True)
        policy_path.write_bytes((self.target / POLICY_PATH).read_bytes())
        with self.assertRaisesRegex(ValueError, "Git worktree"):
            operate(other, "status")
        self.assertFalse((other / "alatyr-session-presence").exists())

    def test_target_registered_continuity_validation_reports_presence_errors(self):
        from target_adapter_validation.harness_scenarios.common import validator
        from target_adapter_validation.session_continuity import validate_session_continuity
        policy_path = self.target / POLICY_PATH
        policy_path.write_text('{"presence": {"enabled": "yes"}}', encoding="utf-8")
        selected = validator(self.target)
        validate_session_continuity(selected)
        codes = {finding.code for finding in selected.findings if finding.level == "error"}
        self.assertIn("SESSION_PRESENCE_POLICY", codes)
        self.assertIn("SESSION_PRESENCE_FLOW", codes)
        policy_path.write_text('{"presence": {"schema_version": 1, "enabled": false, "enabled": true, "flow": ".ai/assistant/flows/session-presence.flow.md", "stale_after_seconds": 3600}}', encoding="utf-8")
        selected = validator(self.target)
        validate_session_continuity(selected)
        self.assertIn("SESSION_PRESENCE_POLICY", {finding.code for finding in selected.findings})

    def test_cli_delegate_and_source_share_canonical_parser_and_results(self):
        self.assertEqual(json.loads(self.cli("status", delegate=True).stdout)["sessions"], [])
        for delegate in (False, True):
            result = self.cli("register", "--write", "--task", "Review", "--scope", "api", delegate=delegate)
            self.assertEqual(result.returncode, 0, result.stderr)
            item = json.loads(result.stdout)
            bad = self.cli("update", "--write", "--session-uid", item["session_uid"], "--expected-version", "-h", "--task", "Review", "--scope", "api", delegate=delegate)
            self.assertEqual(bad.returncode, 2, bad.stderr)
            bad = self.cli("register", "--write", "--task", "Review", "--scope", "api", "--acti", "editing", delegate=delegate)
            self.assertEqual(bad.returncode, 2)
        self.assertEqual(len(operate(self.target, "status")["sessions"]), 2)
        self.assertEqual(self.git("status", "--porcelain").stdout.strip(), "?? .ai/")


if __name__ == "__main__":
    unittest.main()

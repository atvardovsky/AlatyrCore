from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from tests import test_session_presence_runtime as fixtures

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from session_presence_contract import (
    DEFAULT_PRESENCE, POLICY_PATH, SOURCE_POLICY_PATH, merge_presence_policy,
    presence_policy, scope_reference,
)
from session_presence_store import git_identity, load_registry, operate
from session_presence_summary import MAX_SUMMARY_SESSIONS, scope_overlap


class PresenceCoordinationTests(unittest.TestCase):
    setUp = fixtures.PresenceRuntimeTests.setUp
    git = fixtures.PresenceRuntimeTests.git
    set_policy = fixtures.PresenceRuntimeTests.set_policy
    cli = fixtures.PresenceRuntimeTests.cli

    def join(self, scope=None, **kwargs):
        return operate(self.target, "register", write=True, task="Review API",
                       scope=scope or ["path:src/api/"], **kwargs)

    def test_zero_one_two_one_zero_and_fork_lineage(self):
        self.assertEqual(operate(self.target, "status")["coordination"]["state"], "no-reported")
        one = self.join()
        self.assertEqual(one["coordination"]["state"], "single-reported")
        self.assertEqual(one["sessions"], [])
        self.assertFalse(one["own_session"]["refresh_due"])
        two = self.join(parent_uid=one["session_uid"])
        self.assertEqual(two["coordination"]["state"], "multiple-reported")
        self.assertEqual(two["sessions"][0]["session_uid"], one["session_uid"])
        self.assertEqual(two["coordination"]["reported_overlaps"], 1)
        state = operate(self.target, "status", session_uid=one["session_uid"])
        self.assertEqual(state["sessions"][0]["session_uid"], two["session_uid"])
        self.assertNotEqual(one["session_uid"], two["session_uid"])
        result = operate(self.target, "leave", write=True, session_uid=two["session_uid"], expected_version=1)
        self.assertEqual(result["coordination"]["state"], "single-reported")
        self.assertIsNone(result["own_session"])
        result = operate(self.target, "leave", write=True, session_uid=one["session_uid"], expected_version=1)
        self.assertEqual(result["coordination"]["state"], "no-reported")

    def test_registration_uses_one_snapshot_and_retains_legacy_repository_binding(self):
        import hashlib
        import os
        import subprocess
        with patch("session_presence_store.load_registry", wraps=load_registry) as loads, patch("session_presence_store.subprocess.run", wraps=subprocess.run) as calls:
            result = self.join()
        self.assertEqual(loads.call_count, 1)
        self.assertEqual(calls.call_count, 2)
        _, hub, repository_id = git_identity(self.target)
        self.assertEqual(repository_id, hashlib.sha256(os.fsencode(str(hub.parent))).hexdigest())
        self.assertEqual(load_registry(hub, repository_id)["repository_id"], repository_id)
        self.assertEqual(result["version"], 1)

    def test_compact_limit_below_at_above_and_full_detail_parity(self):
        own = self.join(["path:src/api/"])
        for count in range(1, MAX_SUMMARY_SESSIONS + 2):
            peer = self.join(["path:other/"])
            state = operate(self.target, "status", session_uid=own["session_uid"])
            self.assertEqual(len(state["sessions"]), min(count, MAX_SUMMARY_SESSIONS))
            self.assertEqual(state["omitted_sessions"], max(0, count - MAX_SUMMARY_SESSIONS))
        overlapping = self.join(["path:src/api/handler.py"])
        state = operate(self.target, "status", session_uid=own["session_uid"])
        self.assertEqual(state["coordination"]["reported_overlaps"], 1)
        self.assertEqual(state["sessions"][0]["session_uid"], overlapping["session_uid"])
        full = operate(self.target, "status", session_uid=own["session_uid"], full=True)
        self.assertEqual(full["coordination"], state["coordination"])
        self.assertEqual(full["omitted_sessions"], 0)
        detail = operate(self.target, "detail", session_uid=peer["session_uid"])
        self.assertEqual(detail["sessions"][0]["scope"], ["path:other/"])
        self.assertEqual(detail["coordination"]["state"], "multiple-reported")
        self.assertEqual(detail["coordination"]["same_worktree_recent"], full["coordination"]["same_worktree_recent"])
        self.assertEqual(len(detail["sessions"]), 1)
        _, hub, _ = git_identity(self.target)
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in hub.iterdir()}
        for args in (("status", "--full"), ("detail", "--session-uid", peer["session_uid"])):
            result = self.cli(*args, delegate=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in hub.iterdir()})

    def test_scope_matching_and_malformed_typed_references(self):
        cases = [
            (["path:."], ["path:src/api/x.py"], True, "reported-overlap"),
            (["path:src/api"], ["path:src/api/x.py"], True, "reported-overlap"),
            (["path:src/api"], ["path:src/api2"], True, "no-direct-overlap"),
            (["area:billing"], ["area:billing"], True, "reported-overlap"),
            (["area:billing"], ["path:src/api"], True, "unknown"),
            (["api"], ["path:src/api"], True, "unknown"),
            (["path:src/api"], ["path:src/api"], False, "no-direct-overlap"),
            (["resource:git-state"], ["resource:git-state"], False, "reported-overlap"),
        ]
        for left, right, shared, expected in cases:
            with self.subTest(left=left, right=right, shared=shared):
                self.assertEqual(scope_overlap(left, right, shared_worktree=shared), expected)
                self.assertEqual(scope_overlap(right, left, shared_worktree=shared), expected)
        for invalid in ("path:/etc", "path:../src", "path:a//b", "path:./src", "path:C:/src", "path:a\\b", "area:", "resource:build/", "path:src//"):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                scope_reference(invalid)
        self.assertEqual(scope_reference("path:src/"), ("path", "src"))
        self.assertEqual(scope_reference("path:src/My File.py"), ("path", "src/My File.py"))

    def test_scaffold_routes_bind_preserved_policy_instead_of_template_defaults(self):
        from types import SimpleNamespace
        from scaffold_target_structure import (
            build_projection_context, run_scaffold, projected_continuity_policy, projected_template_content,
        )
        args = SimpleNamespace(target=self.root / "scaffold", write=True,
                               overwrite_existing=False, profile="kernel",
                               framework_pack="matched", enable_module=[], assistant_surface=[])
        args.target.mkdir()
        run = run_scaffold(args)
        self.assertFalse(run.blocked)
        selected = {Path(path) for path in run.composition.selected_target_paths}
        selected.update(Path(".ai/framework") / path for path in run.composition.framework_paths)
        context = build_projection_context(selected, set(run.composition.staged_capabilities))
        policy_path = args.target / POLICY_PATH
        installed = json.loads(policy_path.read_text())
        self.assertTrue(installed["presence"]["enabled"])
        for enabled in (False, True):
            installed["presence"]["enabled"] = enabled
            installed["presence"]["own_entry_housekeeping"] = False
            policy_path.write_text(json.dumps(installed))
            projected_policy = projected_continuity_policy(args.target)
            for rel in (".ai/assistant/bootstrap-index.json", ".ai/assistant/entry-packet.json"):
                result = json.loads(projected_template_content(Path(rel), "kernel", run.composition.framework_pack, selected, context, args.target))
                self.assertEqual(result["session_presence"]["enabled"], enabled)
            self.assertFalse(json.loads(projected_policy)["presence"]["own_entry_housekeeping"])

    def test_freshness_and_refresh_boundaries_without_registry_changes(self):
        one = self.join()
        _, hub, _ = git_identity(self.target)
        before = (hub / "sessions.json").read_bytes()
        start = datetime.strptime(one["own_session"].get("started_at", one["observed_at"]), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        for seconds, state, refresh in ((-1, "uncertain", True), (1799, "single-reported", False), (1800, "single-reported", True), (3599, "single-reported", True), (3600, "uncertain", True)):
            with patch("session_presence_store.datetime") as clock:
                clock.now.return_value = start + timedelta(seconds=seconds)
                result = operate(self.target, "status", session_uid=one["session_uid"])
            self.assertEqual(result["coordination"]["state"], state)
            self.assertEqual(result["own_session"]["refresh_due"], refresh)
            self.assertEqual((hub / "sessions.json").read_bytes(), before)

    def test_legacy_typed_looking_records_remain_readable_and_removable(self):
        from session_presence_contract import encoded_registry
        own = self.join()
        peer = self.join()
        _, hub, repository_id = git_identity(self.target)
        value = load_registry(hub, repository_id)
        value["sessions"][peer["session_uid"]]["scope"] = ["path:src/**"]
        (hub / "sessions.json").write_bytes(encoded_registry(value, repository_id))
        before = (hub / "sessions.json").read_bytes()
        result = operate(self.target, "status", session_uid=own["session_uid"])
        self.assertEqual(result["sessions"][0]["overlap"], "unknown")
        self.assertEqual((hub / "sessions.json").read_bytes(), before)
        with self.assertRaises(ValueError):
            self.join(["path:src/**"])
        self.assertEqual((hub / "sessions.json").read_bytes(), before)
        result = self.cli("leave", "--write", "--session-uid", peer["session_uid"], "--expected-version", "1", delegate=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_source_route_explicit_policy_and_worktree_root(self):
        self.set_policy(False)
        self.assertFalse(operate(self.target, "status")["enabled"])
        with self.assertRaisesRegex(ValueError, "source presence policy is missing"):
            operate(self.target, "status", source_contour=True)
        source_policy = self.target / SOURCE_POLICY_PATH
        source_policy.parent.mkdir()
        source_policy.write_bytes((ROOT / SOURCE_POLICY_PATH).read_bytes())
        one = operate(self.target, "register", source_contour=True, write=True, task="Source work", scope=["path:tools/"])
        self.assertEqual(one["coordination"]["state"], "single-reported")
        self.assertFalse(operate(self.target, "status")["enabled"])
        source_cli = self.cli("--source-contour", "status", "--session-uid", one["session_uid"])
        self.assertEqual(source_cli.returncode, 0, source_cli.stderr)
        self.assertEqual(json.loads(source_cli.stdout)["own_session"]["session_uid"], one["session_uid"])
        _, hub, _ = git_identity(self.target)
        before = (hub / "sessions.json").read_bytes()
        disabled = json.loads(source_policy.read_text())
        disabled["presence"]["enabled"] = False
        disabled["presence"]["own_entry_housekeeping"] = False
        source_policy.write_text(json.dumps(disabled))
        self.assertFalse(operate(self.target, "status", source_contour=True)["enabled"])
        self.assertEqual((hub / "sessions.json").read_bytes(), before)
        subdir = self.target / "nested"
        policy = subdir / POLICY_PATH
        policy.parent.mkdir(parents=True)
        policy.write_bytes((ROOT / "templates/target" / POLICY_PATH).read_bytes())
        with self.assertRaisesRegex(ValueError, "worktree root"):
            operate(subdir, "register", write=True, task="Shadow", scope=["path:src/"])

    def test_worktrees_only_share_resource_overlap_not_file_overlap(self):
        other = self.root / "other"
        self.git("worktree", "add", "--detach", str(other), "HEAD")
        policy = other / POLICY_PATH
        policy.parent.mkdir(parents=True)
        policy.write_bytes((self.target / POLICY_PATH).read_bytes())
        self.join(["path:src/", "resource:git-state"])
        second = operate(other, "register", write=True, task="Other worktree", scope=["path:src/", "resource:git-state"])
        self.assertEqual(second["coordination"]["state"], "single-reported")
        self.assertEqual(second["coordination"]["other_worktrees"], 1)
        self.assertEqual(second["sessions"][0]["overlap"], "reported-overlap")
        with self.assertRaisesRegex(ValueError, "different worktree"):
            operate(self.target, "status", session_uid=second["session_uid"])

    def test_migration_preserves_opt_out_housekeeping_legacy_and_runtime(self):
        from scaffold_target_structure import projected_continuity_policy
        template = json.loads((ROOT / "templates/target" / POLICY_PATH).read_text())
        self.assertTrue(merge_presence_policy(template, None)["presence"]["enabled"])
        for old in ({}, {"presence": DEFAULT_PRESENCE}, {"presence": {**template["presence"], "enabled": False}}, {"presence": {**template["presence"], "own_entry_housekeeping": False}}):
            with self.subTest(old=old):
                self.assertEqual(merge_presence_policy(template, old)["presence"], presence_policy(old))
        self.join()
        _, hub, _ = git_identity(self.target)
        before = (hub / "sessions.json").read_bytes()
        for old in ({}, {"presence": DEFAULT_PRESENCE}, {"presence": {**template["presence"], "own_entry_housekeeping": False}}):
            (self.target / POLICY_PATH).write_text(json.dumps(old))
            projected = json.loads(projected_continuity_policy(self.target))
            self.assertEqual(projected["presence"], presence_policy(old))
            self.assertEqual((hub / "sessions.json").read_bytes(), before)
        for invalid in (None, {}, [], "yes", 1, True):
            bad = {"presence": {**template["presence"], "schema_version": invalid}}
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                merge_presence_policy(template, bad)
        for invalid in (None, [], {}, "true", 1):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                presence_policy({"presence": {**template["presence"], "own_entry_housekeeping": invalid}})


if __name__ == "__main__":
    unittest.main()

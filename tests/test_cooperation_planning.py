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
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tests")]
import plan_minimum_work as planner
from cooperation_preflight import preflight
from resource_access import presence_resource_scopes
from session_presence_store import git_identity, operate
from test_plan_minimum_work import NOW, SESSION_ID, capability_record
import test_session_presence_runtime as presence_fixtures
import test_prepare_delegation_result as result_fixtures
from source_worker_contract import load_source_worker_policy, make_builtin_packet
from prepare_delegation_result import prepare
from worker_handoff import compact_handoff, handoff, observed_metrics
from test_test_execution_contract import policy as testing_policy


class WavePlanningTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_source_worker_policy(ROOT / "tools/source_worker_policy.json", root=ROOT)
        self.packets = [make_builtin_packet(self.policy, key) for key in self.policy["workstreams"]]

    def assessment(self, count, parallelism, selected=None):
        decomposition = planner._decomposition("source-tooling", "large-or-resumable", task_worker_packets=self.packets[:count])
        return planner._delegation_assessment(decomposition, runtime_capability="available", decision_override=None,
            skip_reason_id=None, reason=None, selected_workstream_ids=selected,
            runtime_capability_record=capability_record(parallelism), worker_session_id=SESSION_ID, now=NOW)

    def test_candidate_inventory_can_exceed_parallelism_without_expanding_default_selection(self):
        result = self.assessment(4, 2)
        self.assertEqual(len(result["candidate_workstream_ids"]), 4)
        self.assertEqual(len(result["selected_workstream_ids"]), 1)
        self.assertEqual(len(result["dispatch_waves"]), 1)
        self.assertEqual(self.assessment(4, 2, [])["selected_workstream_ids"], result["selected_workstream_ids"])

    def test_waves_preserve_explicit_order_and_runtime_and_policy_limits(self):
        ids = [packet["workstream_id"] for packet in reversed(self.packets)]
        for count in (1, 2, 3, 4):
            for capacity in (1, 2, 4):
                with self.subTest(count=count, capacity=capacity):
                    selected = ids[-count:]
                    result = self.assessment(4, capacity, selected)
                    waves = result["dispatch_waves"]
                    self.assertEqual([item for wave in waves for item in wave], selected)
                    self.assertTrue(all(0 < len(wave) <= min(capacity, 2) for wave in waves))

    def test_root_and_context_limits_still_apply_to_all_candidates(self):
        for field, bound, message in (("max_children_per_parent", 2, "child"), ("max_total_delegates", 2, "total")):
            policy = copy.deepcopy(self.policy)
            policy["tree_policy"][field] = bound
            with patch.object(planner, "_load_source_worker_policy", return_value=policy):
                planner._decomposition("source-tooling", "large-or-resumable", task_worker_packets=self.packets[:bound])
                with self.assertRaisesRegex(ValueError, message):
                    planner._decomposition("source-tooling", "large-or-resumable", task_worker_packets=self.packets[:bound + 1])
        with patch.object(planner, "_packet_context_words", return_value=11000):
            with self.assertRaisesRegex(ValueError, "context"):
                planner._decomposition("source-tooling", "large-or-resumable", task_worker_packets=self.packets[:3])

    def test_invalid_selected_ids_remain_rejected(self):
        identity = self.packets[0]["workstream_id"]
        for selected in ([identity, identity], ["unknown"]):
            with self.assertRaises(ValueError):
                self.assessment(4, 2, selected)


class CooperationRuntimeTests(unittest.TestCase):
    setUp = presence_fixtures.PresenceRuntimeTests.setUp
    git = presence_fixtures.PresenceRuntimeTests.git
    set_policy = presence_fixtures.PresenceRuntimeTests.set_policy
    cli = presence_fixtures.PresenceRuntimeTests.cli

    def test_shared_fixture_canonicalizes_aliased_temporary_paths(self):
        factory = tempfile.TemporaryDirectory
        with factory() as directory:
            root = Path(directory).resolve()
            alias = root / "alias"
            try:
                alias.symlink_to(root, target_is_directory=True)
            except OSError as error:
                self.skipTest("Directory aliases unavailable: " + str(error))
            nested = CooperationRuntimeTests("test_prospective_status_and_preflight_preserve_registry_bytes_and_mtime")
            try:
                with patch.object(presence_fixtures.tempfile, "TemporaryDirectory", side_effect=lambda: factory(dir=alias)):
                    nested.setUp()
                self.assertEqual(nested.target, nested.target.resolve())
                nested.test_prospective_status_and_preflight_preserve_registry_bytes_and_mtime()
            finally:
                nested.doCleanups()
    def test_prospective_status_and_preflight_preserve_registry_bytes_and_mtime(self):
        operate(self.target, "register", write=True, task="Peer task", scope=["path:tools", "resource:git-state"])
        _, hub, _ = git_identity(self.target)
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in hub.iterdir()}
        result = self.cli("status", "--scope", "path:tools/file.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["coordination"]["reported_overlaps"], 1)
        report = preflight(self.target, ["resource:git-state"])
        self.assertEqual(report["decision"], "coordinate-before-work")
        run = subprocess.run([sys.executable, str(ROOT / "tools/alatyr.py"), "cooperation-preflight", "--target", str(self.target), "--scope", "resource:git-state"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["decision"], "coordinate-before-work")
        delegate = [sys.executable, str(ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"),
                    "cooperation-preflight", "--target", str(self.target), "--framework-source", str(ROOT), "--scope", "resource:git-state"]
        delegated = subprocess.run(delegate, capture_output=True, text=True)
        self.assertEqual(delegated.returncode, 0, delegated.stderr)
        self.assertEqual(json.loads(delegated.stdout)["decision"], "coordinate-before-work")
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in hub.iterdir()})

    def test_invalid_scope_rejected_without_creating_presence_state(self):
        _, hub, _ = git_identity(self.target)
        for scope in ([], ["path:../escape"], ["path:tools/*"], ["same", "same"], ["x"] * 9, [None]):
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                operate(self.target, "status", scope=scope)
        self.assertFalse(hub.exists())

    def test_disabled_presence_stays_unknown_not_clear(self):
        self.set_policy(False)
        self.assertEqual(preflight(self.target, ["path:tools"])["decision"], "unknown")

    def test_untyped_prospective_scope_is_unknown_even_without_peers(self):
        self.assertEqual(preflight(self.target, ["legacy-free-form"])["decision"], "unknown")

    def test_stale_unknown_and_omitted_evidence_cannot_clear_work(self):
        for view in ({"same_worktree_uncertain": 1}, {"unknown_scope_peers": 1}):
            with patch("cooperation_preflight.operate", return_value={"enabled": True, "coordination": view}):
                self.assertEqual(preflight(self.target, ["path:tools"])["decision"], "unknown")
        with patch("cooperation_preflight.operate", return_value={"enabled": True, "omitted_sessions": 1}):
            self.assertEqual(preflight(self.target, ["path:tools"])["decision"], "unknown")
        with patch("cooperation_preflight.operate", return_value={"enabled": True, "sessions": [{"freshness": "stale", "overlap": "no-direct-overlap"}]}):
            self.assertEqual(preflight(self.target, ["path:tools"])["decision"], "unknown")

    def test_prospective_scope_boundaries(self):
        for count in (7, 8):
            self.assertEqual(operate(self.target, "status", scope=["area:a" + str(i) for i in range(count)])["sessions"], [])
        with self.assertRaises(ValueError):
            operate(self.target, "status", scope=["area:a" + str(i) for i in range(9)])

    def test_resource_identity_is_shared_across_namespaces_conservatively(self):
        base = {"kind": "database", "id": "test:db", "namespace": "one", "access": "write", "isolation": "verified-isolated"}
        self.assertEqual(presence_resource_scopes([base]), presence_resource_scopes([{**base, "namespace": "two"}]))
        self.assertNotEqual(presence_resource_scopes([base]), presence_resource_scopes([{**base, "id": "other"}]))
        scope = presence_resource_scopes([base])[0]
        operate(self.target, "register", write=True, task="Database test", scope=[scope])
        plan = {"concurrent_eligible": True, "presence_scope_refs": [scope]}
        with patch("cooperation_preflight.resource_plan", return_value=plan):
            self.assertEqual(preflight(self.target, [], command_ids=["unit"])["decision"], "coordinate-before-work")

    def test_real_resource_policy_and_public_cli_are_composed_without_execution(self):
        policy = testing_policy()
        path = self.target / ".ai/project/testing/test-first-policy.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(policy), encoding="utf-8")
        resources = policy["commands"][0]["execution"]["resources"]
        operate(self.target, "register", write=True, task="Shared test output", scope=presence_resource_scopes(resources))
        _, hub, _ = git_identity(self.target)
        before = (hub / "sessions.json").read_bytes()
        args = [sys.executable, str(ROOT / "tools/alatyr.py"), "cooperation-preflight", "--target", str(self.target), "--command", "unit"]
        run = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["decision"], "coordinate-before-work")
        self.assertEqual((hub / "sessions.json").read_bytes(), before)
        invalid = subprocess.run([*args[:-1], "missing"], capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 2, invalid.stderr)
        self.assertNotIn("Traceback", invalid.stderr)


class WorkerHandoffTests(unittest.TestCase):
    setUp = result_fixtures.DelegationDraftTests.setUp
    def test_measured_handoff_does_not_accept_or_copy_raw_content(self):
        result = prepare(self.packet, self.event, self.contents, self.policy)
        draft, serialized = handoff(result, self.packet, self.contents)
        node = draft["node_update_candidate"]
        self.assertEqual(draft["status"], "requires-review")
        self.assertEqual(node["status"], "REVIEW_REQUIRED")
        self.assertEqual(node["satisfied_proof_obligation_ids"], [])
        self.assertEqual(node["result_evidence"]["sha256"], hashlib.sha256(serialized).hexdigest())
        self.assertEqual(node["context_evidence"]["sha256"], result["input_context_packet_sha256"])
        self.assertIn("parent_node_id", draft["required_primary_bindings"])
        self.assertEqual(draft["observed_metrics"], {})
        self.assertNotIn("observed result", json.dumps(draft))
        self.assertLess(len(json.dumps(compact_handoff(draft), indent=2)), len(json.dumps(result, indent=2)))

    def test_metrics_are_optional_typed_and_cannot_change_result_identity(self):
        result = prepare(self.packet, self.event, self.contents, self.policy)
        _, original = handoff(result, self.packet, self.contents)
        for value in (0, 1, 0.25, 1000000000):
            draft, serialized = handoff(result, self.packet, self.contents, {"worker_seconds": value})
            self.assertEqual(serialized, original)
            self.assertEqual(draft["canonical_result_sha256"], result["subtree_sha256"])
        for bad in (True, False, None, [], {}, "1", -1, float("nan"), float("inf"), 10**1000):
            with self.subTest(bad=str(bad)[:30]), self.assertRaises(ValueError):
                observed_metrics({"worker_seconds": bad})
        for bad in ({"unknown": 1}, {}, {"rework_count": 1.5}):
            with self.assertRaises(ValueError):
                observed_metrics(bad)

    def test_tampered_or_accepted_result_cannot_generate_handoff(self):
        result = prepare(self.packet, self.event, self.contents, self.policy)
        for field, value in (("status", "succeeded"), ("subtree_sha256", "0" * 64), ("satisfied_proof_obligation_ids", ["claimed"])):
            with self.subTest(field=field), self.assertRaises(ValueError):
                handoff({**result, field: value}, self.packet, self.contents)
        with self.assertRaises(ValueError):
            handoff(result, self.packet, {**self.contents, "context": b"different"})

    def test_public_summary_cli_writes_matching_handoff_and_rejects_bad_metrics_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name, value in (("packet", self.packet), ("event", self.event), ("metrics", {"worker_seconds": 0.25})):
                (root / (name + ".json")).write_text(json.dumps(value), encoding="utf-8")
            for name, value in self.contents.items():
                (root / (name + ".txt")).write_bytes(value)
            args = [sys.executable, str(ROOT / "tools/alatyr.py"), "prepare-worker-result"]
            for name in ("packet", "event", "context", "raw", "summary", "metrics"):
                args.extend(["--" + name, str(root / (name + (".json" if name in {"packet", "event", "metrics"} else ".txt")))])
            args.extend(["--output-dir", str(root / "output"), "--compact"])
            preview = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertNotIn("result", json.loads(preview.stdout))
            self.assertFalse((root / "output").exists())
            (root / "metrics.json").write_text('{"worker_seconds": true}', encoding="utf-8")
            invalid = subprocess.run([*args, "--write"], capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 2, invalid.stderr)
            self.assertFalse((root / "output").exists())
            (root / "metrics.json").write_text('{"worker_seconds": 0.25}', encoding="utf-8")
            run = subprocess.run([*args, "--write"], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            draft = json.loads((root / "output/handoff.json").read_text())
            self.assertEqual(json.loads(run.stdout)["handoff"], compact_handoff(draft))
            self.assertEqual(draft["node_update_candidate"]["result_evidence"]["sha256"], hashlib.sha256((root / "output/result.json").read_bytes()).hexdigest())

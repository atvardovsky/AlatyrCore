from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from collaboration_observations import handoff_report, capacity_report, intent_digest, decode_observation
from cooperation_preflight import preflight

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
WHEN = "2026-10-30T11:59:00Z"
BAD = (None, {}, [], True, False, 0, -1, 1.5, "unknown")


def handoff_fixture():
    publisher = "11111111-1111-4111-8111-111111111111"
    intent = {"resource_id": "deployment/staging", "publisher_uid": publisher,
              "approval_ref": "approval:task-1-publish", "candidate_revision": "a" * 40,
              "origin_id": "origin:project", "expected_previous_pin": "b" * 40,
              "expected_pin_generation": "generation-2"}
    record = {"schema_version": 1, "intent": intent,
              "acknowledgement": {"publisher_uid": publisher, "intent_sha256": intent_digest(intent),
                  "recorded_at": WHEN, "evidence_ref": "handoff:acknowledgement-1"},
              "availability": {"candidate_revision": "a" * 40, "origin_id": "origin:project", "state": "available",
                  "observed_at": WHEN, "evidence_ref": "origin-observation-1"}}
    current = {"max_age_seconds": 600, "intent": copy.deepcopy(intent),
               "pin": {"revision": "b" * 40, "generation": "generation-2", "observed_at": WHEN, "evidence_ref": "pin-observation-2"}}
    return record, current


def capacity_fixture():
    return {"schema_version": 1, "max_age_seconds": 600,
            "domains": [{"domain_id": "host-1", "headroom_bytes": 1000, "cpu_slots": 2, "observed_at": WHEN, "evidence_ref": "host-headroom"}],
            "builds": [{"instance_id": "build-1", "domain_id": "host-1", "process_tree_peak_bytes": 500,
                        "cpu_slots": 1, "basis": "process-tree-peak-estimate", "observed_at": WHEN, "evidence_ref": "bounded-observation"}]}


class CollaborationObservationTests(unittest.TestCase):
    def test_strict_decoder_rejects_duplicate_nonfinite_and_oversize_inputs(self):
        for raw in (b'{"schema_version":1,"schema_version":2}', b'{"amount":NaN}',
                    b'{"amount":Infinity}', b'[]', b'\xff', b' ' * (256 * 1024 + 1)):
            with self.subTest(raw=raw[:60]), self.assertRaises(ValueError):
                decode_observation(raw)

    def test_valid_handoff_is_only_reported_consistent(self):
        checked = handoff_report(*handoff_fixture(), now=NOW)
        self.assertEqual(checked["state"], "reported-consistent")
        self.assertFalse(checked["authorization_granted"])
        self.assertFalse(checked["activation_order_verified"])

    def test_acknowledgement_cannot_survive_any_intent_change(self):
        for name in handoff_fixture()[0]["intent"]:
            record, current = handoff_fixture()
            replacement = "c" * 40 if name in ("candidate_revision", "expected_previous_pin") else "other-resolved-value"
            record["intent"][name] = current["intent"][name] = replacement
            with self.subTest(name=name):
                self.assertNotEqual(handoff_report(record, current, now=NOW)["state"], "reported-consistent")

    def test_independent_current_bindings_and_pin_generation_cannot_default(self):
        for name in handoff_fixture()[1]["intent"]:
            record, current = handoff_fixture()
            current["intent"].pop(name)
            self.assertTrue(handoff_report(record, current, now=NOW)["findings"])
        record, current = handoff_fixture()
        current["pin"]["generation"] = "generation-3"
        self.assertTrue(handoff_report(record, current, now=NOW)["findings"])

    def test_missing_wrong_unavailable_or_stale_observations_fail(self):
        for name in ("acknowledgement", "availability"):
            record, current = handoff_fixture()
            record.pop(name)
            self.assertTrue(handoff_report(record, current, now=NOW)["findings"])
        for field, value in (("state", "unavailable"), ("origin_id", "different-origin"),
                             ("candidate_revision", "c" * 40), ("observed_at", "2026-10-30T10:00:00Z"),
                             ("observed_at", "2026-10-30T12:00:01Z"), ("observed_at", "2026-10-30T11:59:00")):
            record, current = handoff_fixture()
            record["availability"][field] = value
            self.assertTrue(handoff_report(record, current, now=NOW)["findings"])

    def test_handoff_wrong_types_never_crash_or_clear_obligations(self):
        for group in ("intent", "acknowledgement", "availability"):
            for field in handoff_fixture()[0][group]:
                for value in BAD:
                    record, current = handoff_fixture()
                    record[group][field] = value
                    with self.subTest(group=group, field=field, value=value):
                        self.assertTrue(handoff_report(record, current, now=NOW)["findings"])
        for value in BAD:
            self.assertTrue(handoff_report(value, value, now=NOW)["findings"])

    def test_capacity_below_at_above_boundary_and_multiple_instances(self):
        for demand, state in ((999, "estimated-fit"), (1000, "estimated-fit"), (1001, "unresolved")):
            value = capacity_fixture()
            value["builds"][0]["process_tree_peak_bytes"] = demand
            self.assertEqual(capacity_report(value, now=NOW)["state"], state)
        value = capacity_fixture()
        value["builds"].append(dict(value["builds"][0], instance_id="build-2"))
        self.assertEqual(capacity_report(value, now=NOW)["state"], "estimated-fit")
        value["builds"].append(dict(value["builds"][0], instance_id="build-3"))
        self.assertEqual(capacity_report(value, now=NOW)["state"], "unresolved")

    def test_capacity_domains_never_pool_and_heap_targets_do_not_establish_demand(self):
        value = capacity_fixture()
        value["domains"].append(dict(value["domains"][0], domain_id="host-2", headroom_bytes=10000))
        value["builds"][0]["process_tree_peak_bytes"] = 1001
        self.assertEqual(capacity_report(value, now=NOW)["state"], "unresolved")
        value = capacity_fixture()
        value["builds"][0]["basis"] = "compiler-heap-target"
        self.assertEqual(capacity_report(value, now=NOW)["state"], "unresolved")

    def test_capacity_malformed_fields_and_missing_observations_fail_without_exception(self):
        for group in ("domains", "builds"):
            for field in capacity_fixture()[group][0]:
                for mutation in BAD:
                    value = capacity_fixture()
                    value[group][0][field] = mutation
                    with self.subTest(group=group, field=field, value=mutation):
                        result = capacity_report(value, now=NOW)
                        # Zero observed headroom is valid but cannot fit a positive build.
                        self.assertEqual(result["state"], "unresolved")
        for field in ("domains", "builds", "max_age_seconds", "schema_version"):
            for mutation in BAD:
                value = capacity_fixture()
                value[field] = mutation
                self.assertEqual(capacity_report(value, now=NOW)["state"], "unresolved")

    def test_composition_preserves_presence_conflicts_and_optional_behavior(self):
        presence = {"enabled": True, "omitted_sessions": 0, "sessions": [],
                    "coordination": {"reported_overlaps": 1, "unknown_scope_peers": 0, "same_worktree_uncertain": 0}}
        with patch("cooperation_preflight.operate", return_value=presence):
            checked = preflight(ROOT, ["resource:deployment"], handoff={}, handoff_current={}, capacity={})
            self.assertEqual(checked["decision"], "coordinate-before-work")
            self.assertTrue(checked["handoff"]["findings"])
            self.assertTrue(checked["capacity"]["findings"])
            absent = preflight(ROOT, ["resource:deployment"])
            self.assertIsNone(absent["handoff"])
            self.assertIsNone(absent["capacity"])

    def test_handoff_resource_is_included_in_peer_comparison(self):
        record, current = handoff_fixture()
        presence = {"enabled": True, "omitted_sessions": 0, "sessions": [],
                    "coordination": {"reported_overlaps": 0, "unknown_scope_peers": 0, "same_worktree_uncertain": 0}}
        with patch("cooperation_preflight.operate", return_value=presence) as operation:
            checked = preflight(ROOT, ["resource:git-state"], handoff=record, handoff_current=current)
            self.assertIn("resource:deployment/staging", operation.call_args.kwargs["scope"])
            self.assertIn("resource:deployment/staging", checked["scope"])

    def test_public_cli_invalid_observation_is_actionable_not_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
            (root / "handoff.json").write_text(json.dumps({"schema_version": 1, "intent": []}))
            command = [sys.executable, str(ROOT / "tools/alatyr.py"), "cooperation-preflight", "--target", str(root),
                       "--scope", "resource:deployment", "--handoff", "handoff.json", "--handoff-current", "handoff.json", "--require-clear"]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertTrue(json.loads(result.stdout)["handoff"]["findings"])
            self.assertNotIn("Traceback", result.stderr)

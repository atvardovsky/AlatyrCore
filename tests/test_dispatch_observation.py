"""Dispatch acknowledgement must not be inferred from message delivery."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from dispatch_observation import NO_DISPATCH, dispatch_failures
from delegation_evidence import DelegationEvidenceError, validate_execution_tree, validate_single_read_only_receipt
import tests.test_source_worker_contract as fixtures
from tests.test_delegation_evidence_closure import bind_branch

PROTOCOL = {"operation_roles": {"launch": "start", "resume": "resume", "send": "message"},
            "evidence_ref": "current-runtime-observation"}


def observation(operation, packet, node, attempt=0):
    return {"operation_id": operation, "packet_id": packet, "node_id": node,
            "attempt": attempt, "worker_id": "runtime-worker-" + node,
            "assignment_id": "assignment-" + node, "action": "start", "operation_name": "launch",
            "observed_state": "completed", "observed_at": "2026-11-03T13:00:00Z",
            "event_ref": "tool-response-" + node}


class DispatchObservationTests(unittest.TestCase):
    def check(self, value, state="DONE", required=True):
        return dispatch_failures(value, operation_id="operation", packet_id="packet",
            node_id="worker", attempt=0, state=state, required=required, protocol=PROTOCOL)

    def test_message_queued_unknown_and_wrong_assignment_do_not_prove_execution(self):
        self.assertTrue(self.check(None))
        for key, bad in (("action", "message"), ("observed_state", "queued"),
                         ("operation_name", "send"),
                         ("observed_state", "unknown"), ("packet_id", "old-packet"),
                         ("operation_id", "other-task"), ("attempt", True),
                         ("observed_at", "2026-11-03")):
            value = observation("operation", "packet", "worker"); value[key] = bad
            self.assertTrue(self.check(value), (key, bad))

    def test_immediate_completion_and_resumed_execution_are_valid(self):
        value = observation("operation", "packet", "worker")
        self.assertEqual(self.check(value), [])
        value.update(action="resume", operation_name="resume", observed_state="running")
        self.assertEqual(self.check(value, state="RUNNING"), [])
        self.assertEqual(self.check(NO_DISPATCH, state="READY"), [])
        self.assertEqual(self.check(NO_DISPATCH, required=False), [])
        for bad in (None, {}, [], True, 3, "unknown"):
            self.assertTrue(self.check(bad, required=False))

    def test_all_malformed_json_fields_produce_diagnostics(self):
        valid = observation("operation", "packet", "worker")
        for key in valid:
            for bad in ({}, [], None, True, 3, "unknown"):
                value = copy.deepcopy(valid); value[key] = bad
                self.assertTrue(self.check(value), (key, bad))

    def test_both_evidence_tiers_share_dispatch_rules_and_real_cli_rejects_message(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt, policy, capability = fixtures.SingleReadOnlyDelegationReceiptTests().build_fixture(root)
            policy["dispatch_verification"] = "required"
            capability["subagent_delegation"]["assignment_protocol"] = PROTOCOL
            receipt["capability_sha256"] = fixtures.canonical_value_digest(capability)
            receipt["policy_sha256"] = fixtures.canonical_value_digest(policy)
            with self.assertRaisesRegex(DelegationEvidenceError, "dispatch"):
                validate_single_read_only_receipt(receipt, policy, capability, artifact_root=root)
            packet = receipt["packet"]
            receipt["dispatch"] = observation(receipt["operation_id"], packet["packet_id"], packet["node_id"])
            validate_single_read_only_receipt(receipt, policy, capability, artifact_root=root)
            receipt["dispatch"]["action"] = "message"
            for name, data in (("receipt", receipt), ("policy", policy), ("capability", capability)):
                (root / (name + ".json")).write_text(json.dumps(data))
            result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/validate_delegation_execution_tree.py"),
                "--target-root", str(root), "--receipt", str(root / "receipt.json"), "--policy", str(root / "policy.json"),
                "--capability", str(root / "capability.json")], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("message", result.stderr)
            tree = fixtures.recursive_execution_fixture(root)
            policy = fixtures.policy_fixture()
            policy["dispatch_verification"] = "required"
            for node in tree["nodes"]:
                if node["depth"]:
                    node["dispatch"] = observation(tree["operation_id"], node["packet_id"], node["node_id"], node["attempt"])
            # The tree binds the policy as an immutable record; retain that binding.
            tree["policy_revision"] = fixtures.canonical_value_digest(policy)
            cap_path = root / tree["capability_evidence"]
            capability = json.loads(cap_path.read_text())
            capability["subagent_delegation"] = {"assignment_protocol": PROTOCOL}
            cap_path.write_text(json.dumps(capability))
            import hashlib
            tree["capability_evidence_sha256"] = hashlib.sha256(cap_path.read_bytes()).hexdigest()
            envelope = json.loads((root / tree["nodes"][1]["branch_envelope"]).read_text())
            envelope["capability_evidence_sha256"] = tree["capability_evidence_sha256"]
            bind_branch(root, tree, envelope=envelope)
            validate_execution_tree(tree, policy, artifact_root=root)
            tree["nodes"][1]["dispatch"]["action"] = "message"
            with self.assertRaisesRegex(DelegationEvidenceError, "message"):
                validate_execution_tree(tree, policy, artifact_root=root)


if __name__ == "__main__":
    unittest.main()

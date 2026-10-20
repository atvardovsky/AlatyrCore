"""Public-boundary regressions for delegation scope and evidence closure."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import test_source_worker_contract as fixtures
from test_source_worker_contract import (
    canonical_digest, canonical_value_digest,
    measured_artifact, policy_fixture, recursive_execution_fixture,
)
from delegation_evidence import DelegationEvidenceError, validate_execution_tree, validate_single_read_only_receipt
from jsonschema import Draft7Validator


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bind_result(root, node, value):
    value["subtree_sha256"] = canonical_digest(value, "subtree_sha256")
    node["result_evidence"] = measured_artifact(root, node["result_evidence"]["path"], json.dumps(value, ensure_ascii=False))


def bind_branch(root, tree, child=None, envelope=None):
    parent, node = tree["nodes"][1:]
    if child is None:
        child = json.loads((root / node["result_evidence"]["path"]).read_text())
    bind_result(root, node, child)
    result = json.loads((root / parent["result_evidence"]["path"]).read_text())
    result["child_result_sha256"] = [node["result_evidence"]["sha256"]]
    bind_result(root, parent, result)
    checkpoint = json.loads((root / parent["branch_checkpoint"]).read_text())
    if envelope is not None:
        envelope["envelope_sha256"] = canonical_digest(envelope, "envelope_sha256")
        save(root / parent["branch_envelope"], envelope)
        parent["branch_envelope_sha256"] = envelope["envelope_sha256"]
        checkpoint["branch_envelope_sha256"] = envelope["envelope_sha256"]
        checkpoint["context_packet_sha256"] = envelope["context_packet_sha256"]
    checkpoint["accepted_result_sha256"] = [node["result_evidence"]["sha256"]]
    checkpoint["evidence_manifest_sha256"] = canonical_value_digest({child["result_id"]: child["evidence_manifest"]})
    checkpoint["validation_sha256"] = canonical_value_digest({child["result_id"]: child["validation"]})
    checkpoint["checkpoint_sha256"] = canonical_digest(checkpoint, "checkpoint_sha256")
    save(root / parent["branch_checkpoint"], checkpoint)
    parent["branch_checkpoint_sha256"] = checkpoint["checkpoint_sha256"]


def tree_cli(root, tree):
    save(root / "tree.json", tree)
    save(root / "policy.json", policy_fixture())
    return subprocess.run([sys.executable, str(ROOT / "tools/validate_delegation_execution_tree.py"),
        "--target-root", str(root), "--tree", str(root / "tree.json"), "--policy", str(root / "policy.json")], capture_output=True, text=True)


class DelegationClosureTests(unittest.TestCase):
    def test_receipt_counters_reject_boolean_and_float_numeric_aliases(self):
        for field, values in (("depth", (True, 1.0)), ("attempt", (False, 0.0)), ("child_count", (False, 0.0))):
            for bad in values:
                with self.subTest(field=field, bad=bad), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    receipt, policy, capability = fixtures.SingleReadOnlyDelegationReceiptTests().build_fixture(root)
                    receipt["packet"][field] = bad
                    with self.assertRaisesRegex(DelegationEvidenceError, field):
                        validate_single_read_only_receipt(receipt, policy, capability, artifact_root=root)

    def test_distinct_child_context_and_optional_parent_baseline_pass_public_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = recursive_execution_fixture(root)
            self.assertNotEqual(tree["nodes"][1]["context_evidence"]["sha256"], tree["nodes"][2]["context_evidence"]["sha256"])
            self.assertEqual(tree_cli(root, tree).returncode, 0)
            envelope = json.loads((root / "evidence/envelope.json").read_text())
            envelope["context_packet_sha256"] = tree["nodes"][1]["context_evidence"]["sha256"]
            bind_branch(root, tree, envelope=envelope)
            result = tree_cli(root, tree)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_selector_widening_is_rejected_with_all_hashes_rebound(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = recursive_execution_fixture(root)
            envelope = json.loads((root / "evidence/envelope.json").read_text())
            envelope["allowed_surface_refs"] = ["tools/?.py"]
            tree["nodes"][2]["surface_refs"] = ["tools/*.py"]
            child = json.loads((root / "evidence/child-result.json").read_text())
            child["touched_surfaces"] = ["tools/private.py"]
            bind_branch(root, tree, child, envelope)
            result = tree_cli(root, tree)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("surface", result.stderr)

    def test_every_ancestor_constrains_project_surfaces_not_artifact_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = recursive_execution_fixture(root)
            tree["nodes"][0]["surface_refs"] = ["tools/only.py"]
            with self.assertRaisesRegex(DelegationEvidenceError, "surface"):
                validate_execution_tree(tree, policy_fixture(), artifact_root=root)
            tree["nodes"][0]["surface_refs"] = []
            validate_execution_tree(tree, policy_fixture(), artifact_root=root)

    def test_missing_or_mismatched_delivered_identity_fails_at_each_depth(self):
        for index in (1, 2):
            for bad in (None, "0" * 64, {}, [], True, "unknown"):
                with self.subTest(index=index, bad=bad), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    tree = recursive_execution_fixture(root)
                    node = tree["nodes"][index]
                    value = json.loads((root / node["result_evidence"]["path"]).read_text())
                    value["input_context_packet_sha256"] = bad
                    if index == 2:
                        bind_branch(root, tree, value)
                    else:
                        bind_result(root, node, value)
                    with self.assertRaisesRegex(DelegationEvidenceError, "input.context"):
                        validate_execution_tree(tree, policy_fixture(), artifact_root=root)

    def test_nonblank_convergence_fields_match_schema(self):
        for field in ("combined_validation", "logical_integrity_review", "residual_risk"):
            for bad in (None, "", " \n", {}, [], False, 0):
                with self.subTest(field=field, bad=bad), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    tree = recursive_execution_fixture(root)
                    tree["primary_convergence"][field] = bad
                    with self.assertRaisesRegex(DelegationEvidenceError, field):
                        validate_execution_tree(tree, policy_fixture(), artifact_root=root)

    def test_receipt_strategy_and_independent_worker_primary_validation(self):
        for field, bad in (("strategy", "unknown"), ("worker", []), ("primary", [])):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                receipt, policy, capability = fixtures.SingleReadOnlyDelegationReceiptTests().build_fixture(root)
                if field == "strategy":
                    receipt["analysis_strategy_id"] = bad
                    receipt["problem_model_sha256"] = "0" * 64
                elif field == "worker":
                    receipt["result"]["validation"] = bad
                else:
                    receipt["primary_convergence"]["validation"] = bad
                with self.assertRaisesRegex(DelegationEvidenceError, "strategy|validation"):
                    validate_single_read_only_receipt(receipt, policy, capability, artifact_root=root)

    def test_receipt_public_cli_and_schema_agree_on_admission_cases(self):
        schema = json.loads((ROOT / "schemas/alatyr-single-read-only-delegation-receipt.schema.json").read_text())
        for mutation in ("valid", "unknown-strategy", "worker-validation", "primary-validation", "failed-worker"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                receipt, policy, capability = fixtures.SingleReadOnlyDelegationReceiptTests().build_fixture(root)
                if mutation == "unknown-strategy":
                    receipt["analysis_strategy_id"] = "not-a-strategy"
                    receipt["problem_model_sha256"] = "0" * 64
                elif mutation == "worker-validation":
                    receipt["result"]["validation"] = []
                elif mutation == "primary-validation":
                    receipt["primary_convergence"]["validation"] = []
                elif mutation == "failed-worker":
                    receipt["result"]["status"] = "failed"
                for name, value in (("receipt", receipt), ("policy", policy), ("capability", capability)):
                    save(root / (name + ".json"), value)
                result = subprocess.run([sys.executable, str(ROOT / "tools/validate_delegation_execution_tree.py"),
                    "--target-root", str(root), "--receipt", str(root / "receipt.json"),
                    "--policy", str(root / "policy.json"), "--capability", str(root / "capability.json")], capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, mutation == "valid", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                if mutation != "failed-worker":
                    self.assertEqual(not list(Draft7Validator(schema).iter_errors(receipt)), mutation == "valid")

    def test_valid_convergence_states_remain_supported(self):
        states = {"pending": ("RUNNING", None), "completed": ("DONE", "evidence-sufficient"),
                  "blocked": ("BLOCKED", "semantic-decision-required"), "cancelled": ("CANCELLED", "cancelled-by-primary")}
        for state, (root_status, stop) in states.items():
            with self.subTest(state=state), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                tree = recursive_execution_fixture(root)
                tree["nodes"][0].update(status=root_status, stop_reason_id=stop)
                tree["primary_convergence"].update(status=state, final_stop_reason_id=stop)
                validate_execution_tree(tree, policy_fixture(), artifact_root=root)

    def test_malformed_enum_fields_are_diagnostics_not_crashes(self):
        for field in ("status", "final_stop_reason_id"):
            for bad in ({}, [], None, True, 5):
                with self.subTest(field=field, bad=bad), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    tree = recursive_execution_fixture(root)
                    tree["primary_convergence"][field] = bad
                    result = tree_cli(root, tree)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn("Traceback", result.stderr)

    def test_parent_and_edge_ids_are_typed_before_hash_lookups(self):
        for location, field in (("node", "parent_node_id"), ("edge", "parent_node_id"), ("edge", "child_node_id")):
            for bad in ({}, [], None, True, 1):
                with self.subTest(location=location, field=field, bad=bad), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    tree = recursive_execution_fixture(root)
                    target = tree["nodes"][1] if location == "node" else tree["edges"][0]
                    target[field] = bad
                    result = tree_cli(root, tree)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(field, result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_stale_shared_baseline_and_unicode_scoped_child(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = recursive_execution_fixture(root)
            envelope = json.loads((root / "evidence/envelope.json").read_text())
            envelope["context_packet_sha256"] = "0" * 64
            bind_branch(root, tree, envelope=envelope)
            with self.assertRaisesRegex(DelegationEvidenceError, "coordinator context"):
                validate_execution_tree(tree, policy_fixture(), artifact_root=root)
            envelope["context_packet_sha256"] = tree["nodes"][1]["context_evidence"]["sha256"]
            child = json.loads((root / "evidence/child-result.json").read_text())
            child["validation"].append("review caf\u00e9")
            child["touched_surfaces"] = ["tools/source_worker_contract.py"]
            bind_branch(root, tree, child, envelope)
            result = tree_cli(root, tree)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_selector_containment_positive_and_negative_boundaries(self):
        from delegation_evidence import _matches_surface, _selector_within
        cases = [
            ("tools/x.py", ["tools/?.py"], True),
            ("tools/?.py", ["tools/?.py"], True),
            ("tools/sub/*.py", ["tools/**"], True),
            ("tools/*.py", ["tools/?.py"], False),
            ("tools-extra/*.py", ["tools/**"], False),
            ("tools/a.py", [], False),
            ("C:/escape.py", ["**"], False),
            ("tools/../escape.py", ["**"], False),
            ("tools//a.py", ["tools/**"], False),
        ]
        for child, parents, expected in cases:
            with self.subTest(child=child, parents=parents):
                self.assertEqual(_selector_within(child, parents), expected)
        self.assertFalse(_matches_surface("tools/*.py", ["tools/**"]))

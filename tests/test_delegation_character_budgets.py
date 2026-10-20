import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from delegation_evidence import CHARACTERS_PER_WORD_LIMIT, enforce_character_limit, validate_execution_tree, validate_single_read_only_receipt
from tests import test_source_worker_contract as fixtures
from tests.test_source_worker_contract import (
    canonical_value_sha256, measured_artifact,
    policy_fixture, recursive_execution_fixture,
)


class CharacterBudgetTests(unittest.TestCase):
    def test_normative_character_factor_matches_the_canonical_enforcer(self):
        owner = (ROOT / "framework/subagent-delegation.md").read_text()
        factor = re.search(r"character ceiling of (\d+) times", owner)
        self.assertIsNotNone(factor)
        self.assertEqual(int(factor[1]), CHARACTERS_PER_WORD_LIMIT)
        schema = json.loads((ROOT / "schemas/alatyr-delegation-policy.schema.json").read_text())
        factor = re.search(r"ceiling of (\d+) times", schema["$comment"])
        self.assertIsNotNone(factor)
        self.assertEqual(int(factor[1]), CHARACTERS_PER_WORD_LIMIT)

    def test_character_below_at_above_boundary(self):
        for delta in (-1, 0, 1):
            with self.subTest(delta=delta):
                if delta > 0:
                    with self.assertRaisesRegex(ValueError, "1201.*1200"):
                        enforce_character_limit(1200 + delta, 100, "context")
                else:
                    enforce_character_limit(1200 + delta, 100, "context")

    def test_receipt_retains_context_raw_and_summary_character_bounds(self):
        for field, group, word_field in (
            ("context_artifact", "tree_policy", "max_context_words_total"),
            ("raw_artifact", "context_compaction", "max_result_words_total"),
            ("accepted_summary_artifact", "context_compaction", "max_primary_summary_words_total"),
        ):
            for delta in (-1, 0, 1):
                with tempfile.TemporaryDirectory() as directory, self.subTest(field=field, delta=delta):
                    root = Path(directory)
                    receipt, policy, capability = fixtures.SingleReadOnlyDelegationReceiptTests().build_fixture(root)
                    policy[group][word_field] = 100
                    if field == "raw_artifact":
                        policy["context_compaction"]["max_primary_summary_words_total"] = 100
                    receipt["policy_sha256"] = canonical_value_sha256(policy)
                    container = receipt["packet"] if field == "context_artifact" else receipt["result"]
                    container[field] = measured_artifact(root, field + ".txt", "x" * (1200 + delta))
                    if field == "raw_artifact":
                        receipt["result"]["accepted_summary_artifact"] = measured_artifact(root, "summary.txt", "y")
                    if field == "accepted_summary_artifact":
                        receipt["result"]["raw_artifact"] = measured_artifact(root, "raw.txt", "x" * 1300)
                    if delta > 0:
                        with self.assertRaisesRegex(ValueError, "character"):
                            validate_single_read_only_receipt(receipt, policy, capability, artifact_root=root)
                    else:
                        validate_single_read_only_receipt(receipt, policy, capability, artifact_root=root)

    def test_full_tree_checks_measured_dense_context(self):
        for delta in (-1, 0, 1):
            with tempfile.TemporaryDirectory() as directory, self.subTest(delta=delta):
                root = Path(directory)
                tree = recursive_execution_fixture(root)
                node = tree["nodes"][1]
                sibling_chars = tree["nodes"][2]["context_evidence"]["character_count"]
                node["context_evidence"] = measured_artifact(root, "dense-context.txt", "x" * (32000 * 12 - sibling_chars + delta))
                node["context_words"] = 1
                result = json.loads((root / node["result_evidence"]["path"]).read_text())
                result["input_context_packet_sha256"] = node["context_evidence"]["sha256"]
                result["subtree_sha256"] = fixtures.canonical_digest(result, "subtree_sha256")
                node["result_evidence"] = measured_artifact(root, node["result_evidence"]["path"], json.dumps(result))
                tree["aggregate_budget"]["used_context_words"] = 1 + tree["nodes"][2]["context_words"]
                if delta > 0:
                    with self.assertRaisesRegex(ValueError, "aggregate worker context.*character"):
                        validate_execution_tree(tree, policy_fixture(), artifact_root=root)
                else:
                    validate_execution_tree(tree, policy_fixture(), artifact_root=root)

    def test_full_tree_raw_and_summary_character_boundaries(self):
        for field, limit_field in (("raw_payload", "max_result_words"), ("accepted_summary", "max_summary_words")):
            for delta in (-1, 0, 1):
                with tempfile.TemporaryDirectory() as directory, self.subTest(field=field, delta=delta):
                    root = Path(directory)
                    tree = recursive_execution_fixture(root)
                    node = tree["nodes"][1]
                    result_path = root / node["result_evidence"]["path"]
                    result = json.loads(result_path.read_text())
                    count = node[limit_field] * 12 + delta
                    result[field] = measured_artifact(root, field + ".txt", "x" * (count - 2) + " a")
                    result["subtree_sha256"] = fixtures.canonical_digest(result, "subtree_sha256")
                    node["result_evidence"] = measured_artifact(root, node["result_evidence"]["path"], json.dumps(result))
                    if field == "accepted_summary":
                        node["accepted_summary_evidence"] = result[field]
                        checkpoint_path = root / node["branch_checkpoint"]
                        checkpoint = json.loads(checkpoint_path.read_text())
                        checkpoint["accepted_summary"] = result[field]
                        checkpoint["checkpoint_sha256"] = fixtures.canonical_digest(checkpoint, "checkpoint_sha256")
                        checkpoint_path.write_text(json.dumps(checkpoint))
                        node["branch_checkpoint_sha256"] = checkpoint["checkpoint_sha256"]
                    child = json.loads((root / tree["nodes"][2]["result_evidence"]["path"]).read_text())
                    tree["aggregate_budget"]["used_result_words"] = result["raw_payload"]["word_count"] + child["raw_payload"]["word_count"]
                    tree["aggregate_budget"]["used_primary_summary_words"] = result["accepted_summary"]["word_count"]
                    if delta > 0:
                        with self.assertRaisesRegex(ValueError, "character"):
                            validate_execution_tree(tree, policy_fixture(), artifact_root=root)
                    else:
                        validate_execution_tree(tree, policy_fixture(), artifact_root=root)

    def test_public_receipt_cli_rejects_dense_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt, policy, capability = fixtures.SingleReadOnlyDelegationReceiptTests().build_fixture(root)
            policy["tree_policy"]["max_context_words_total"] = 1000
            receipt["policy_sha256"] = canonical_value_sha256(policy)
            receipt["packet"]["context_artifact"] = measured_artifact(root, "context.txt", "x" * 40000)
            for name, value in (("receipt", receipt), ("policy", policy), ("capability", capability)):
                (root / (name + ".json")).write_text(json.dumps(value))
            command = [sys.executable, str(ROOT / "tools/validate_delegation_execution_tree.py"), "--target-root", str(root)]
            for name in ("receipt", "policy", "capability"):
                command.extend(["--" + name, str(root / (name + ".json"))])
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("40000", result.stderr)
            self.assertIn("12000", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

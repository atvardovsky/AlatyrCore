from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from worker_model_selection import review_selection
from tests.worker_model_fixtures import selection_fixture, write_selection


class WorkerModelSelectionTests(unittest.TestCase):
    def review(self, record, **options):
        return review_selection(record, packet_id="packet-1", node_id="worker-1",
                                capability_sha256="a" * 64, execution_state="DONE", **options)

    def test_cheapest_eligible_option_and_justified_semantic_model(self):
        record = selection_fixture()
        self.assertEqual(self.review(record)["selected"]["id"], "economy")
        record["selected_option"] = "reasoning"
        with self.assertRaisesRegex(ValueError, "more costly"):
            self.review(record)
        record["task_class"] = "semantic"
        record["observed"].update(model="fixture-reasoning", reasoning="high")
        self.assertEqual(self.review(record)["selected"]["id"], "reasoning")

    def test_evidence_backed_exclusion_is_required_not_a_generic_rationale(self):
        record = selection_fixture()
        record["selected_option"] = "reasoning"
        record["rationale"] = "Prefer more reasoning"
        record["observed"].update(model="fixture-reasoning", reasoning="high")
        with self.assertRaises(ValueError): self.review(record)
        record["exclusions"] = [{"option_id": "economy", "reason": "observed-quality-failure", "evidence_ref": "review/failed-economy-case"}]
        self.assertEqual(self.review(record)["selected"]["id"], "reasoning")

    def test_model_and_effort_mismatch_and_unverified_budget_do_not_pass(self):
        for field in ("model", "reasoning"):
            record = selection_fixture()
            record["observed"][field] = "different"
            with self.assertRaisesRegex(ValueError, "differs"):
                self.review(record)
        record = selection_fixture()
        record["observed"] = {"state": "unverified", "model": None, "reasoning": None, "evidence_ref": None}
        with self.assertRaisesRegex(ValueError, "bounded-cost"):
            self.review(record)
        record["max_cost_rank"] = None
        self.assertEqual(self.review(record)["verification"], "unverified")

    def test_rank_below_at_above_ceiling_and_unavailable_or_unauthorized(self):
        for limit in (0, 1, 2):
            record = selection_fixture(); record["max_cost_rank"] = limit
            if limit == 0:
                with self.assertRaises(ValueError): self.review(record)
            else:
                self.assertEqual(self.review(record)["selected"]["id"], "economy")
        for key, value in (("availability", "unknown"), ("availability", "unavailable"), ("authorized", False)):
            record = selection_fixture(); record["options"][0][key] = value
            with self.assertRaises(ValueError): self.review(record)
        record = selection_fixture()
        record["options"][0]["selection_modes"] = ["client-default"]
        with self.assertRaises(ValueError): self.review(record)

    def test_malformed_fields_have_diagnostics_not_type_errors(self):
        for bad in ({}, [], None, True, 1, "unknown"):
            for field in ("task_class", "options", "exclusions", "selection_mode", "selected_option", "observed"):
                if field == "exclusions" and bad == []:
                    continue
                record = selection_fixture(); record[field] = bad
                with self.subTest(field=field, bad=bad), self.assertRaises(ValueError): self.review(record)
            for field in ("cost_rank", "eligible_for", "availability", "authorized"):
                if field == "authorized" and bad is True or field == "cost_rank" and type(bad) is int and bad == 1:
                    continue
                record = selection_fixture(); record["options"][0][field] = bad
                with self.subTest(option=field, bad=bad), self.assertRaises(ValueError): self.review(record)
        for field in ("packet_id", "node_id", "capability_sha256"):
            record = selection_fixture(); record[field] = "different"
            with self.assertRaises(ValueError): self.review(record)

    def test_public_cli_selects_null_choice_and_never_dispatches(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder); record = selection_fixture(); record["selected_option"] = None
            write_selection(target, "choice.json", record)
            result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "plan-worker-model",
                "--target", str(target), "--record", "choice.json"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            delegated = subprocess.run([sys.executable, "-B", str(ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"),
                "plan-worker-model", "--target", str(target), "--framework-source", str(ROOT), "--record", "choice.json"],
                capture_output=True, text=True)
            self.assertEqual(delegated.returncode, 0, delegated.stdout + delegated.stderr)
            self.assertEqual(json.loads(delegated.stdout), json.loads(result.stdout))
            payload = json.loads(result.stdout)
            self.assertEqual(payload["record"]["selected_option"], "economy")
            self.assertFalse(payload["authorization_granted"])
            self.assertFalse(payload["acceptance_granted"])
            self.assertEqual(list(target.iterdir()), [target / "choice.json"])

    def test_resolved_fixture_matches_the_published_schema(self):
        import jsonschema
        schema = json.loads((ROOT / "schemas/alatyr-worker-model-selection.schema.json").read_text())
        jsonschema.Draft7Validator.check_schema(schema)
        jsonschema.validate(selection_fixture(), schema)

    def test_full_and_lightweight_receipts_share_selection_enforcement(self):
        from delegation_evidence import validate_execution_tree, validate_single_read_only_receipt, DelegationEvidenceError
        from tests.test_source_worker_contract import SingleReadOnlyDelegationReceiptTests, recursive_execution_fixture, policy_fixture, canonical_value_sha256
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            receipt, policy, capability = SingleReadOnlyDelegationReceiptTests().build_fixture(target)
            policy["model_selection"] = "required"
            receipt["policy_sha256"] = canonical_value_sha256(policy)
            tree = recursive_execution_fixture(target)
            tree_policy = policy_fixture(); tree_policy["model_selection"] = "required"
            tree["policy_revision"] = canonical_value_sha256(tree_policy)
            for node in tree["nodes"]:
                if node["depth"]:
                    node["model_selection"] = write_selection(target, node["node_id"] + "-choice.json",
                        selection_fixture(node["packet_id"], node["node_id"], tree["capability_evidence_sha256"]))
            receipt["model_selection"] = write_selection(target, "single-choice.json",
                selection_fixture(capability_sha256=receipt["capability_sha256"]))
            validate_execution_tree(tree, tree_policy, artifact_root=target)
            validate_single_read_only_receipt(receipt, policy, capability, artifact_root=target)
            for selected, selected_policy, call in ((receipt, policy, lambda: validate_single_read_only_receipt(receipt, policy, capability, artifact_root=target)),
                    (tree["nodes"][1], tree_policy, lambda: validate_execution_tree(tree, tree_policy, artifact_root=target))):
                original = copy.deepcopy(selected["model_selection"])
                selected.pop("model_selection")
                with self.assertRaisesRegex(DelegationEvidenceError, "required"): call()
                selected["model_selection"] = original
                choice = json.loads((target / original["path"]).read_text())
                choice["selected_option"] = "reasoning"
                selected["model_selection"] = write_selection(target, original["path"], choice)
                with self.assertRaisesRegex(DelegationEvidenceError, "more costly"): call()
                choice["selected_option"] = "economy"
                selected["model_selection"] = write_selection(target, original["path"], choice)

    def test_actual_receipt_cli_rejects_expensive_selection_with_correct_digests(self):
        from tests.test_source_worker_contract import SingleReadOnlyDelegationReceiptTests
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            receipt, policy, capability = SingleReadOnlyDelegationReceiptTests().build_fixture(target)
            for name, value in (("receipt", receipt), ("policy", policy), ("capability", capability)):
                (target / (name + ".json")).write_text(json.dumps(value))
            command = [sys.executable, "-B", str(ROOT / "tools/validate_delegation_execution_tree.py"),
                "--target-root", str(target), "--receipt", str(target / "receipt.json"),
                "--policy", str(target / "policy.json"), "--capability", str(target / "capability.json")]
            valid = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
            choice = selection_fixture(capability_sha256=receipt["capability_sha256"])
            choice["selected_option"] = "reasoning"
            receipt["model_selection"] = write_selection(target, "single-model.json", choice)
            (target / "receipt.json").write_text(json.dumps(receipt))
            invalid = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("more costly", invalid.stdout + invalid.stderr)


if __name__ == "__main__":
    unittest.main()

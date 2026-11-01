from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from contract_work import verify_work_delegation
from tests.active_task_fixture import ActiveTaskFixture
from tests.test_contract_work import contract_model
from tests import test_source_worker_contract as delegation_fixtures
from tests import test_delegation_evidence_closure as closure_fixtures


class ContractDelegationIntegrationTests(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        self.model = contract_model()
        part = self.model["contract_work"]["parts"][0]
        part.update(implementation_level="L1", executor="worker", reason="An independent bounded inspection is required",
                    delegation_evidence={"kind": "single-read-only-receipt", "path": "receipt.json",
                                         "node_id": "worker-1", "capability_path": "capability.json"})
        self.model["contract_work"]["delegation_preference"] = "require-supported"
        self.receipt, self.policy, self.capability = delegation_fixtures.SingleReadOnlyDelegationReceiptTests().build_fixture(self.target)
        self.policy.update(default_preference="require-supported", state="enabled")
        self.receipt.update(operation_id=self.model["operation_id"], analysis_strategy_id=self.model["primary_strategy_id"],
                            base_revision=self.model["repository_binding"]["base_revision"], policy_sha256=delegation_fixtures.canonical_value_sha256(self.policy))
        assigned = ["part-positive", "part-negative"]
        self.receipt["packet"]["proof_obligation_ids"] = assigned
        self.receipt["packet"]["canonical_owner_refs"] = ["design.md"]
        self.receipt["result"]["satisfied_proof_obligation_ids"] = assigned
        self.write_model(); self.write_index()
        self.receipt["problem_model_sha256"] = self.task["problem_model"]["sha256"]
        self.save_evidence()

    def save_evidence(self):
        for name, value in (("receipt.json", self.receipt), ("capability.json", self.capability),
                            (".ai/assistant/delegation-policy.json", self.policy)):
            (self.target / name).write_text(json.dumps(value), encoding="utf-8")

    def test_current_receipt_flows_through_registered_model_validation(self):
        checked = self.check()
        self.assertEqual(self.errors(checked), set(), checked.findings)
        self.close()
        checked = self.check()
        self.assertEqual(self.errors(checked), set(), checked.findings)

    def test_wrong_operation_revision_model_and_node_are_rejected(self):
        original = copy.deepcopy(self.receipt)
        for field in ("operation_id", "base_revision", "problem_model_sha256"):
            self.receipt = copy.deepcopy(original)
            self.receipt[field] = "0" * 64
            self.save_evidence()
            self.assertIn("CONTRACT_WORK_DELEGATION", self.errors(self.check()), field)
        self.receipt = original
        self.receipt["packet"]["node_id"] = "other-worker"
        self.save_evidence()
        self.assertIn("CONTRACT_WORK_DELEGATION", self.errors(self.check()))

    def test_receipt_cannot_substitute_unassigned_obligations_or_implementation(self):
        self.receipt["packet"]["proof_obligation_ids"] = ["other-proof"]
        self.receipt["result"]["satisfied_proof_obligation_ids"] = ["other-proof"]
        self.save_evidence()
        self.assertIn("CONTRACT_WORK_DELEGATION", self.errors(self.check()))
        self.receipt["packet"]["proof_obligation_ids"] = ["part-positive", "part-negative"]
        self.receipt["result"]["satisfied_proof_obligation_ids"] = ["part-positive", "part-negative"]
        self.model["contract_work"]["parts"][0]["implementation_level"] = "L4"
        self.write_model(); self.write_index()
        self.receipt["problem_model_sha256"] = self.task["problem_model"]["sha256"]
        self.save_evidence()
        self.assertIn("CONTRACT_WORK_DELEGATION", self.errors(self.check()))

    def test_arbitrary_json_and_changed_actual_payload_cannot_prove_delegation(self):
        (self.target / "receipt.json").write_text('{"status": "succeeded"}', encoding="utf-8")
        self.assertIn("CONTRACT_WORK_DELEGATION", self.errors(self.check()))
        self.save_evidence()
        (self.target / "raw.txt").write_text("unreviewed replacement", encoding="utf-8")
        self.assertIn("CONTRACT_WORK_DELEGATION", self.errors(self.check()))

    def test_matching_obligations_do_not_replace_the_correct_contract_owner(self):
        self.receipt["packet"]["canonical_owner_refs"] = ["unrelated-contract.md"]
        self.save_evidence()
        self.assertIn("CONTRACT_WORK_DELEGATION", self.errors(self.check()))
        self.receipt["packet"]["canonical_owner_refs"] = ["design.md#module-contract"]
        self.save_evidence()
        self.assertEqual(self.errors(self.check()), set())

    def test_component_receipt_does_not_discharge_end_to_end_completion(self):
        self.model["proof_obligations"][-1]["status"] = "open"
        self.write_model(); self.write_index()
        self.receipt["problem_model_sha256"] = self.task["problem_model"]["sha256"]
        self.save_evidence(); self.close()
        self.assertIn("ANALYSIS_REQUIRED_OBLIGATION_OPEN", self.errors(self.check()))

    def test_delegation_reads_use_the_same_coherent_view(self):
        from target_adapter_validation.context import TargetRepositoryView
        view = TargetRepositoryView(self.target)
        def read(path, limit):
            result = view.read_bytes_result(path, max_bytes=limit)
            if result.value is None:
                raise ValueError(result.error)
            return result.value
        self.assertEqual(verify_work_delegation(self.model, model_sha256=self.task["problem_model"]["sha256"],
            policy=self.policy, target=self.target, read=read, completion=True), [])
        (self.target / "raw.txt").write_text("changed after lookup", encoding="utf-8")
        self.assertTrue(view.finalize())

    def test_primary_finalization_keeps_original_worker_payloads_immutable(self):
        paths = ("context.txt", "raw.txt", "summary.txt")
        original = {path: (self.target / path).read_bytes() for path in paths}
        self.model["proof_obligations"][0]["evidence_refs"].append("fixture:primary-review")
        self.write_model(); self.write_index()
        self.receipt["problem_model_sha256"] = self.task["problem_model"]["sha256"]
        self.save_evidence(); self.close()
        self.assertEqual(self.errors(self.check()), set())
        self.assertEqual(original, {path: (self.target / path).read_bytes() for path in paths})

    def use_tree(self):
        tree = delegation_fixtures.recursive_execution_fixture(self.target)
        self.policy["tree_policy"]["worker_child_behavior"] = "primary-preauthorized-read-only"
        tree["policy_revision"] = delegation_fixtures.canonical_value_digest(self.policy)
        self.model.update(operation_id=tree["operation_id"])
        tree["analysis_strategy_id"] = self.model["primary_strategy_id"]
        self.model["repository_binding"]["base_revision"] = tree["base_revision"]
        self.task["operation_id"] = tree["operation_id"]
        part = self.model["contract_work"]["parts"][0]
        part["delegation_evidence"] = {"kind": "execution-tree", "path": "tree.json", "node_id": "coordinator", "capability_path": None}
        assigned = part["positive_obligation_ids"] + part["negative_obligation_ids"]
        for node in tree["nodes"][1:]:
            node["proof_obligation_ids"] = assigned
            node["satisfied_proof_obligation_ids"] = assigned
            node["canonical_owner_refs"] = ["design.md"]
            path = self.target / node["result_evidence"]["path"]
            result = json.loads(path.read_bytes())
            result.update(proof_obligation_ids=assigned, satisfied_proof_obligation_ids=assigned)
            closure_fixtures.bind_result(self.target, node, result)
        envelope = json.loads((self.target / "evidence/envelope.json").read_bytes())
        envelope["proof_obligation_ids"] = assigned
        path = self.target / "evidence/checkpoint.json"
        checkpoint = json.loads(path.read_bytes())
        checkpoint["completed_proof_obligation_ids"] = assigned
        closure_fixtures.save(path, checkpoint)
        closure_fixtures.bind_branch(self.target, tree, envelope=envelope)
        tree["primary_convergence"].update(required_proof_obligation_ids=assigned, satisfied_proof_obligation_ids=assigned)
        self.write_model(); self.write_index(); self.save_evidence()
        tree["problem_model_sha256"] = self.task["problem_model"]["sha256"]
        (self.target / "tree.json").write_text(json.dumps(tree), encoding="utf-8")
        return tree

    def test_full_tree_uses_the_same_registered_part_and_completion_checks(self):
        self.use_tree()
        self.assertEqual(self.errors(self.check()), set())
        self.close()
        checked = self.check()
        self.assertEqual(self.errors(checked), set(), checked.findings)

    def test_full_tree_cannot_use_an_unrelated_operation_or_primary_node(self):
        tree = self.use_tree()
        tree["operation_id"] = "unrelated-operation"
        (self.target / "tree.json").write_text(json.dumps(tree), encoding="utf-8")
        self.assertIn("CONTRACT_WORK_DELEGATION", self.errors(self.check()))
        self.model["contract_work"]["parts"][0]["delegation_evidence"]["node_id"] = "root"
        self.write_model(); self.write_index()
        tree["operation_id"] = self.model["operation_id"]
        tree["problem_model_sha256"] = self.task["problem_model"]["sha256"]
        (self.target / "tree.json").write_text(json.dumps(tree), encoding="utf-8")
        self.assertIn("CONTRACT_WORK_DELEGATION", self.errors(self.check()))


if __name__ == "__main__":
    unittest.main()

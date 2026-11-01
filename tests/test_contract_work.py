from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from analysis_strategy_contract import validate_problem_model
from contract_work import MAX_ARTIFACT_BYTES, MAX_TOTAL_BYTES, work_failures, verify_work_artifacts
from target_adapter_validation.harness_scenarios.analysis_strategies import _model
from tests.active_task_fixture import ActiveTaskFixture


def contract_model():
    model = _model()
    source = model["proof_obligations"][0]
    model["proof_obligations"] = []
    for name in ("part-positive", "part-negative", "integrated", "outcome"):
        row = copy.deepcopy(source)
        row.update(id=name, required=True, status="passed", evidence_refs=["fixture:" + name])
        model["proof_obligations"].append(row)
    model["risk_classes"].append("contract-sensitive-multipart")
    model["contract_work"] = {
        "delegation_preference": "auto",
        "parts": [{"id": "producer-consumer", "implementation_level": "L4",
                   "contract_refs": [{"path": "design.md", "sha256": hashlib.sha256(b"accepted design\n").hexdigest()}],
                   "positive_obligation_ids": ["part-positive"], "negative_obligation_ids": ["part-negative"],
                   "executor": "primary", "reason": "This bounded part does not justify worker setup", "delegation_evidence": None}],
        "integration_obligation_ids": ["integrated"], "end_to_end_obligation_ids": ["outcome"]}
    return model


class ContractWorkTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads((ROOT / "schemas/alatyr-problem-model.schema.json").read_bytes())
        self.model = contract_model()

    def test_valid_and_absent_work_keep_existing_model_versions(self):
        self.assertEqual(validate_problem_model(self.model, self.schema), [])
        self.assertEqual(validate_problem_model(_model(), self.schema), [])
        self.assertEqual(verify_work_artifacts(_model(), lambda *_: self.fail("unselected artifact read")), [])

    def test_classified_work_cannot_omit_its_contract_parts(self):
        del self.model["contract_work"]
        self.assertIn("requires contract_work", ";".join(validate_problem_model(self.model, self.schema)))

    def test_all_structured_fields_reject_malformed_json_values(self):
        for field in self.model["contract_work"]:
            for bad in (None, {}, [], True, 1, "unknown"):
                model = copy.deepcopy(self.model)
                model["contract_work"][field] = bad
                self.assertTrue(validate_problem_model(model, self.schema), (field, bad))
        part = self.model["contract_work"]["parts"][0]
        for field in part:
            for bad in ({}, [], True, 1):
                model = copy.deepcopy(self.model)
                model["contract_work"]["parts"][0][field] = bad
                self.assertTrue(validate_problem_model(model, self.schema), (field, bad))

    def test_each_acceptance_layer_needs_distinct_required_obligations(self):
        for field in ("integration_obligation_ids", "end_to_end_obligation_ids"):
            model = copy.deepcopy(self.model)
            model["contract_work"][field] = ["part-positive"]
            self.assertTrue(validate_problem_model(model, self.schema))
        for mutation in ("missing", "not-required"):
            model = copy.deepcopy(self.model)
            if mutation == "missing":
                model["proof_obligations"].pop()
            else:
                model["proof_obligations"][-1]["required"] = False
            self.assertTrue(validate_problem_model(model, self.schema))

    def test_required_delegation_forbids_silent_primary_substitution(self):
        work = self.model["contract_work"]
        for preference in ("require-supported", "auto"):
            work["delegation_preference"] = preference
            policy = {"default_preference": "require-supported", "state": "enabled"}
            self.assertIn("requires a worker", ";".join(work_failures(self.model, policy=policy)))
        work["parts"][0]["executor"] = "blocked"
        for row in self.model["proof_obligations"][:2]:
            row["status"] = "blocked"
        self.assertEqual(work_failures(self.model, policy=policy), [])
        self.assertTrue(work_failures(self.model, completion=True, policy=policy))

    def test_multiple_receipts_or_trees_cannot_reset_operation_wide_budgets(self):
        work = self.model["contract_work"]
        first = work["parts"][0]
        first.update(executor="worker", implementation_level="L1",
            delegation_evidence={"kind": "single-read-only-receipt", "path": "receipt.json", "node_id": "worker-1", "capability_path": "capability.json"})
        second = copy.deepcopy(first)
        second.update(id="second-part", positive_obligation_ids=["second-positive"], negative_obligation_ids=["second-negative"])
        work["parts"].append(second)
        for identity in ("second-positive", "second-negative"):
            proof = copy.deepcopy(self.model["proof_obligations"][0])
            proof["id"] = identity
            self.model["proof_obligations"].append(proof)
        self.assertEqual(validate_problem_model(self.model, self.schema), [])
        second["delegation_evidence"]["path"] = "another-receipt.json"
        self.assertIn("one operation-wide", ";".join(validate_problem_model(self.model, self.schema)))
        for part in work["parts"]:
            part["delegation_evidence"].update(kind="execution-tree", capability_path=None)
        self.assertIn("one operation-wide", ";".join(validate_problem_model(self.model, self.schema)))
        second["delegation_evidence"]["path"] = "receipt.json"
        self.assertEqual(validate_problem_model(self.model, self.schema), [])

    def test_forbid_and_primary_owned_levels_override_worker_requests(self):
        work = self.model["contract_work"]
        part = work["parts"][0]
        part["executor"] = "worker"
        policy = {"default_preference": "auto", "state": "enabled"}
        self.assertEqual(work_failures(self.model, policy=policy, policy_checked=True), [])
        self.assertTrue(work_failures(self.model, completion=True, policy=policy))
        for level in ("L0", "L5", "L6", "L7"):
            part["implementation_level"] = level
            self.assertTrue(work_failures(self.model, policy=policy))
        part["implementation_level"] = "L4"
        for preference in ("forbid", "require-supported"):
            work["delegation_preference"] = preference
            self.assertTrue(work_failures(self.model, policy={**policy, "default_preference": "forbid"}))
        work["delegation_preference"] = "auto"
        for policy in (None, {}, {"state": "disabled", "default_preference": "auto"}):
            self.assertTrue(work_failures(self.model, policy=policy, policy_checked=True))

    def test_hashes_are_verified_and_repeated_contracts_read_only_once(self):
        part = self.model["contract_work"]["parts"][0]
        part["contract_refs"].append(dict(part["contract_refs"][0]))
        reads = []
        def read(path, limit):
            reads.append((path, limit))
            return b"accepted design\n"
        self.assertEqual(verify_work_artifacts(self.model, read), [])
        self.assertEqual(reads, [("design.md", MAX_ARTIFACT_BYTES)])
        self.assertTrue(verify_work_artifacts(self.model, lambda *_: b"changed"))

    def test_paths_conflicting_bindings_and_duplicate_parts_fail(self):
        for path in ("../escape", "/absolute", "C:\\escape", "design.md#section", "unknown"):
            model = copy.deepcopy(self.model)
            model["contract_work"]["parts"][0]["contract_refs"][0]["path"] = path
            self.assertTrue(validate_problem_model(model, self.schema), path)
        part = self.model["contract_work"]["parts"][0]
        part["contract_refs"].append({"path": "design.md", "sha256": "0" * 64})
        self.assertIn("conflicting artifact", ";".join(validate_problem_model(self.model, self.schema)))
        self.model["contract_work"]["parts"].append(copy.deepcopy(part))
        self.assertIn("duplicate", ";".join(validate_problem_model(self.model, self.schema)))

    def test_artifact_byte_and_total_boundaries(self):
        for size in (MAX_ARTIFACT_BYTES - 1, MAX_ARTIFACT_BYTES, MAX_ARTIFACT_BYTES + 1):
            data = b"x" * size
            self.model["contract_work"]["parts"][0]["contract_refs"][0]["sha256"] = hashlib.sha256(data).hexdigest()
            self.assertEqual(bool(verify_work_artifacts(self.model, lambda *_: data)), size > MAX_ARTIFACT_BYTES)
        part = self.model["contract_work"]["parts"][0]
        data = b"x" * MAX_ARTIFACT_BYTES
        for count in (7, 8, 9):
            part["contract_refs"] = [{"path": f"contract-{i}", "sha256": hashlib.sha256(data).hexdigest()} for i in range(count)]
            seen = []
            def read(path, limit):
                seen.append(limit)
                if limit < len(data):
                    raise ValueError("artifact exceeds remaining byte budget")
                return data
            self.assertEqual(bool(verify_work_artifacts(self.model, read)), count * len(data) > MAX_TOTAL_BYTES)
            self.assertTrue(all(limit <= MAX_ARTIFACT_BYTES for limit in seen))

    def test_indeterminate_failed_reads_cannot_spend_the_budget_repeatedly(self):
        part = self.model["contract_work"]["parts"][0]
        part["contract_refs"] = [{"path": f"contract-{i}", "sha256": "0" * 64} for i in range(9)]
        calls = []
        def read(path, limit):
            calls.append(limit)
            raise ValueError("reader consumed its allowance before detecting instability")
        self.assertTrue(verify_work_artifacts(self.model, read))
        self.assertEqual(calls, [MAX_ARTIFACT_BYTES])

    def test_unique_artifact_ceiling_is_checked_before_reads(self):
        for count in (31, 32, 33):
            part = self.model["contract_work"]["parts"][0]
            part["contract_refs"] = [{"path": f"contract-{i}", "sha256": hashlib.sha256(b"").hexdigest()} for i in range(count)]
            calls = []
            def read(path, _limit):
                calls.append(path)
                return b""
            self.assertEqual(bool(verify_work_artifacts(self.model, read)), count > 32)
            self.assertEqual(len(calls), count if count <= 32 else 0)


class RegisteredContractWorkTests(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        self.model = contract_model()
        self.write_model(); self.write_index()

    def test_registered_active_task_route_checks_real_contract_bytes(self):
        checked = self.check()
        self.assertEqual(self.errors(checked), set(), checked.findings)
        (self.target / "design.md").write_bytes(b"unreviewed contract\n")
        self.assertIn("CONTRACT_WORK_ARTIFACT", self.errors(self.check()))

    def test_registered_route_enforces_target_preference(self):
        path = self.target / ".ai/assistant/delegation-policy.json"
        path.write_text(json.dumps({"default_preference": "require-supported", "state": "enabled"}), encoding="utf-8")
        self.assertIn("CONTRACT_WORK_INVALID", self.errors(self.check()))

    def test_full_completion_requires_wider_obligations_not_only_component_passes(self):
        self.model["proof_obligations"][-1]["status"] = "open"
        self.write_model(); self.close()
        self.assertIn("ANALYSIS_REQUIRED_OBLIGATION_OPEN", self.errors(self.check()))


if __name__ == "__main__":
    unittest.main()

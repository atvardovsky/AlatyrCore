"""Exercise adopted harness controls through the registered capability path."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tests import test_test_execution_contract as fixtures
from tests.test_test_execution_contract import TestExecutionContract, nested_paths, set_path
from target_adapter_validation.context import TargetRepositoryView
from test_harness_contract import accounting_failures, harness_digest, input_paths, MAX_FILE_BYTES, MAX_TOTAL_BYTES


def counts(n):
    return {"discovered": n, "executed": n, "passed": n, "failed": 0, "skipped": 0}


class HarnessContractTests(unittest.TestCase):
    fixture = fixtures.RegisteredTestingExecutionTests.fixture
    write = fixtures.RegisteredTestingExecutionTests.write
    findings = fixtures.RegisteredTestingExecutionTests.findings

    def prepare(self, root):
        policy, record = self.fixture(root)
        policy["execution_contract"]["schema_version"] = record["schema_version"] = 4
        execution = policy["commands"][0]["execution"]
        execution.update(harness_inputs=["harness.css"], behavioral_accounting="required")
        self.write(root, "harness.css", "fixture-specific-css")
        self.write(root, ".ai/project/testing/test-first-policy.json", policy)
        digest = lambda path: hashlib.sha256((root / path).read_bytes()).hexdigest()
        record["policy_sha256"] = digest(".ai/project/testing/test-first-policy.json")
        record["input_sha256"]["harness.css"] = digest("harness.css")
        identity = harness_digest(TargetRepositoryView(root), record, execution, ".ai/project/testing/test-first-policy.json")
        record["harness_identity"] = {"sha256": identity, "observations_pointer": "/harness"}
        record["case_accounting"] = {"observations_pointer": "/accounting"}
        artifact = {"harness": identity, "accounting": {"behavioral": counts(1), "supporting": counts(0)}}
        self.save(root, record, artifact)
        return policy, record, artifact

    def save(self, root, record, artifact):
        self.write(root, "result.txt", artifact)
        record["result_artifact"]["sha256"] = hashlib.sha256((root / "result.txt").read_bytes()).hexdigest()
        self.write(root, "current.json", record)

    def errors(self, root):
        return [row for row in self.findings(root) if row.level == "error"]

    def test_registered_valid_and_material_identity_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); policy, record, artifact = self.prepare(root)
            self.assertEqual(self.errors(root), [])
            (root / "harness.css").write_bytes(b"other-css")
            self.assertTrue(self.errors(root))
            # Even updated input hashes cannot reuse the old observed identity.
            record["input_sha256"]["harness.css"] = hashlib.sha256(b"other-css").hexdigest()
            self.save(root, record, artifact)
            self.assertTrue(any("harness identity" in row.message for row in self.errors(root)))
            identity = harness_digest(TargetRepositoryView(root), record, policy["commands"][0]["execution"], ".ai/project/testing/test-first-policy.json")
            record["harness_identity"]["sha256"] = artifact["harness"] = identity
            self.save(root, record, artifact)
            self.assertEqual(self.errors(root), [])

    def test_registered_supporting_only_cannot_claim_behavior(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); _, record, artifact = self.prepare(root)
            artifact["accounting"] = {"behavioral": counts(0), "supporting": counts(1)}
            self.save(root, record, artifact)
            self.assertTrue(any("supporting/setup/no-op" in row.message for row in self.errors(root)))
            record["claim"] = "none"; self.save(root, record, artifact)
            self.assertEqual(self.errors(root), [])

    def test_missing_wrong_and_malformed_bindings_return_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); _, record, artifact = self.prepare(root)
            for field in ("harness_identity", "case_accounting"):
                for value in (None, {}, [], True, 7, {"observations_pointer": "/missing"}):
                    changed = copy.deepcopy(record); changed[field] = value
                    self.save(root, changed, artifact)
                    with self.subTest(field=field, value=value): self.assertTrue(self.errors(root))
                changed = copy.deepcopy(record); del changed[field]
                self.save(root, changed, artifact); self.assertTrue(self.errors(root))

    def test_accounting_mutations_never_crash_or_hide_counts(self):
        original = {"behavioral": counts(1), "supporting": counts(0)}
        rec = {"counts": counts(1), "claim": "full"}
        self.assertEqual(accounting_failures(original, rec), [])
        for path in [(), *nested_paths(original)]:
            for bad in (None, {}, [], True, 1.0, -1, "unknown"):
                changed = copy.deepcopy(original)
                if path: set_path(changed, path, bad)
                else: changed = bad
                with self.subTest(path=path, bad=bad): self.assertTrue(accounting_failures(changed, rec))
        huge = 2**54 + 1
        rec["counts"] = counts(huge)
        self.assertEqual(accounting_failures({"behavioral": counts(huge), "supporting": counts(0)}, rec), [])

    def test_control_versions_and_legacy_remain_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); policy, record, _ = self.prepare(root)
            contract = TestExecutionContract()
            for version in (2, 3):
                changed = copy.deepcopy(policy); changed["execution_contract"]["schema_version"] = version
                self.assertTrue(contract.policy_failures(changed))
                changed["commands"][0]["execution"].pop("harness_inputs")
                changed["commands"][0]["execution"].pop("behavioral_accounting")
                self.assertEqual(contract.policy_failures(changed), [])
                old = copy.deepcopy(record); old["schema_version"] = version
                self.assertTrue(contract.evidence_failures(old, policy["commands"][0], policy["execution_contract"]))
            frozen = json.loads((Path(__file__).resolve().parents[1] / "schemas/test-execution-contract-v3.schema.json").read_text())
            self.assertEqual(frozen["$defs"]["contract"]["properties"]["schema_version"]["const"], 3)

    def test_material_path_and_file_budget_boundaries(self):
        for n in (1, 64, 65):
            execution = {"configuration_paths": [], "harness_inputs": [f"{i}.cfg" for i in range(n)]}
            if n <= 64: self.assertEqual(len(input_paths(execution)), n)
            else:
                with self.assertRaises(ValueError): input_paths(execution)
        for path in ("../outside", "/absolute", "./alias", "a//b", "a\\b", "a*", "bad\ud800"):
            with self.assertRaises(ValueError): input_paths({"configuration_paths": [], "harness_inputs": [path]})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); policy, record, _ = self.prepare(root)
            execution = policy["commands"][0]["execution"]
            for n in (MAX_FILE_BYTES - 1, MAX_FILE_BYTES, MAX_FILE_BYTES + 1):
                (root / "harness.css").write_bytes(b"x" * n)
                record["input_sha256"]["harness.css"] = hashlib.sha256(b"x" * n).hexdigest()
                if n <= MAX_FILE_BYTES:
                    harness_digest(TargetRepositoryView(root), record, execution, ".ai/project/testing/test-first-policy.json")
                else:
                    with self.assertRaises(ValueError): harness_digest(TargetRepositoryView(root), record, execution, ".ai/project/testing/test-first-policy.json")

    def test_total_byte_and_union_file_bounds_preserve_exact_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); policy, record, _ = self.prepare(root)
            execution = policy["commands"][0]["execution"]
            execution["configuration_paths"] = []
            execution["harness_inputs"] = [f"part-{i}.cfg" for i in range(9)]
            for i, path in enumerate(execution["harness_inputs"]):
                raw = b"x" * MAX_FILE_BYTES if i < 8 else b""
                (root / path).write_bytes(raw)
                record["input_sha256"][path] = hashlib.sha256(raw).hexdigest()
            self.write(root, ".ai/project/testing/test-first-policy.json", policy)
            record["policy_sha256"] = hashlib.sha256((root / ".ai/project/testing/test-first-policy.json").read_bytes()).hexdigest()
            harness_digest(TargetRepositoryView(root), record, execution, ".ai/project/testing/test-first-policy.json")
            (root / "part-8.cfg").write_bytes(b"x")
            record["input_sha256"]["part-8.cfg"] = hashlib.sha256(b"x").hexdigest()
            with self.assertRaises(ValueError): harness_digest(TargetRepositoryView(root), record, execution, ".ai/project/testing/test-first-policy.json")
        for size in (255, 256, 257):
            execution = {"configuration_paths": [f"cfg-{i}" for i in range(size - 1)], "harness_inputs": ["material"]}
            if size <= 256: self.assertEqual(len(input_paths(execution)), size)
            else:
                with self.assertRaises(ValueError): input_paths(execution)


if __name__ == "__main__":
    unittest.main()

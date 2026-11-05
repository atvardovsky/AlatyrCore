"""Exercise adopted harness controls through the registered capability path."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
import subprocess
import sys
from pathlib import Path

from tests import test_test_execution_contract as fixtures
from tests.test_test_execution_contract import TestExecutionContract, nested_paths, set_path
from target_adapter_validation.context import TargetRepositoryView
from test_harness_contract import accounting_failures, harness_digest, input_paths, MAX_FILE_BYTES, MAX_TOTAL_BYTES
from test_input_state import capture_inputs, selected_inputs, stability_failures


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

    def prepare_stability(self, root):
        policy, record, artifact = self.prepare(root)
        execution = policy['commands'][0]['execution']
        execution['source_stability'] = 'required'
        execution['harness_inputs'].append('src/app.py')
        self.write(root, '.ai/framework/test-execution-selection.md', 'Conditional execution controls')
        record['input_sha256']['.ai/framework/test-execution-selection.md'] = hashlib.sha256((root / '.ai/framework/test-execution-selection.md').read_bytes()).hexdigest()
        self.write(root, '.ai/project/testing/test-first-policy.json', policy)
        record['policy_sha256'] = hashlib.sha256((root / '.ai/project/testing/test-first-policy.json').read_bytes()).hexdigest()
        observed = capture_inputs(TargetRepositoryView(root), execution, record['files']['selected'])
        record['input_sha256'].update(observed)
        identity = harness_digest(TargetRepositoryView(root), record, execution, '.ai/project/testing/test-first-policy.json')
        record['harness_identity']['sha256'] = artifact['harness'] = identity
        record['input_stability'] = {'observations_pointer': '/stability'}
        artifact['stability'] = {'before': dict(observed), 'after': dict(observed)}
        self.save(root, record, artifact)
        return policy, record, artifact

    def test_registered_source_stability_checks_actual_inputs_not_just_updated_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); policy, record, artifact = self.prepare_stability(root)
            self.assertEqual(self.errors(root), [])
            self.write(root, 'src/app.py', 'changed while test was running')
            observed = capture_inputs(TargetRepositoryView(root), policy['commands'][0]['execution'], record['files']['selected'])
            record['input_sha256'].update(observed)
            identity = harness_digest(TargetRepositoryView(root), record, policy['commands'][0]['execution'], '.ai/project/testing/test-first-policy.json')
            record['harness_identity']['sha256'] = artifact['harness'] = identity
            artifact['stability']['after'] = dict(observed)
            self.save(root, record, artifact)
            self.assertTrue(any('input stability changed or stale' in row.message for row in self.errors(root)))
            artifact['stability']['before'] = dict(observed)
            self.save(root, record, artifact)
            self.assertEqual(self.errors(root), [])

    def test_registered_source_stability_missing_and_malformed_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); policy, record, artifact = self.prepare_stability(root)
            for value in (None, [], True, 7, {}, {'before': {}, 'after': {}},
                          {'before': [], 'after': {}}, {'before': {}, 'after': {}, 'extra': 1}):
                changed = copy.deepcopy(artifact); changed['stability'] = value
                self.save(root, record, changed)
                with self.subTest(value=value): self.assertTrue(self.errors(root))
            changed = copy.deepcopy(record); del changed['input_stability']
            self.save(root, changed, artifact); self.assertTrue(self.errors(root))
            for path in [('before', 'src/app.py'), ('after', 'tests/a.py')]:
                for bad in (None, {}, [], True, 1, 'not-a-digest'):
                    changed = copy.deepcopy(artifact); changed['stability'][path[0]][path[1]] = bad
                    self.save(root, record, changed)
                    with self.subTest(path=path, bad=bad): self.assertTrue(self.errors(root))
            self.save(root, record, artifact)
            policy['commands'][0]['execution'].pop('source_stability')
            self.assertTrue(TestExecutionContract().evidence_failures(record, policy['commands'][0], policy['execution_contract']))

    def test_unexecuted_partial_controls_do_not_crash_or_claim_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); _, record, artifact = self.prepare_stability(root)
            record['counts'] = counts(0)
            record['counts'].update(discovered=1, skipped=1)
            record['claim'] = 'none'
            record['state'] = 'skipped'
            record['files']['executed'] = []
            artifact['accounting']['behavioral'] = dict(record['counts'])
            for supplied in (False, True):
                changed = copy.deepcopy(record)
                if not supplied: changed.pop('input_stability')
                self.save(root, changed, artifact)
                with self.subTest(supplied=supplied): self.assertEqual(self.errors(root), [])
            artifact['stability']['after'] = {}
            self.save(root, record, artifact)
            self.assertTrue(any('input stability' in row.message for row in self.errors(root)))

    def test_unexecuted_sibling_bindings_remain_independently_optional(self):
        from testing_controls import selected_control_failures
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); policy, record, artifact = self.prepare_stability(root)
            execution = policy['commands'][0]['execution']
            execution.update(timing_qualification='required', selection_contract='required')
            execution['resources'][0]['access'] = record['resources'][0]['access'] = 'exclusive'
            self.write(root, '.ai/project/testing/test-first-policy.json', policy)
            record['policy_sha256'] = hashlib.sha256((root / '.ai/project/testing/test-first-policy.json').read_bytes()).hexdigest()
            identity = harness_digest(TargetRepositoryView(root), record, execution, '.ai/project/testing/test-first-policy.json')
            record['harness_identity']['sha256'] = artifact['harness'] = identity
            record.update(state='skipped', claim='none')
            record['counts'] = dict(counts(0), discovered=1, skipped=1)
            record['files']['executed'] = []
            artifact['accounting']['behavioral'] = dict(record['counts'])
            for fields in (('input_stability',), ('harness_identity',), ('case_accounting',),
                           ('harness_identity', 'input_stability'), ()):
                changed = copy.deepcopy(record)
                changed['selection_evidence'] = changed['qualification_window'] = None
                for name in ('input_stability', 'harness_identity', 'case_accounting'):
                    if name not in fields: changed.pop(name)
                self.save(root, changed, artifact)
                with self.subTest(fields=fields): self.assertEqual(self.errors(root), [])
                self.assertEqual(selected_control_failures(TargetRepositoryView(root), changed, execution), [])

    def test_unexecuted_null_controls_do_not_require_a_result_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); policy, record = self.fixture(root)
            policy['execution_contract']['schema_version'] = record['schema_version'] = 4
            execution = policy['commands'][0]['execution']
            execution.update(selection_contract='required', timing_qualification='required')
            execution['resources'][0]['access'] = record['resources'][0]['access'] = 'exclusive'
            self.write(root, '.ai/framework/test-execution-selection.md', 'Conditional execution controls')
            record['input_sha256']['.ai/framework/test-execution-selection.md'] = hashlib.sha256((root / '.ai/framework/test-execution-selection.md').read_bytes()).hexdigest()
            self.write(root, '.ai/project/testing/test-first-policy.json', policy)
            record['policy_sha256'] = hashlib.sha256((root / '.ai/project/testing/test-first-policy.json').read_bytes()).hexdigest()
            record.update(state='skipped', claim='none', result_artifact=None,
                          selection_evidence=None, qualification_window=None)
            record['counts'] = dict(counts(0), discovered=1, skipped=1)
            record['files']['executed'] = []
            self.write(root, 'current.json', record)
            self.assertEqual(self.errors(root), [])

    def test_public_input_state_capture_and_comparison_are_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); _, record, _ = self.prepare_stability(root)
            command = [sys.executable, '-B', str(Path(__file__).resolve().parents[1] / 'tools/alatyr.py'),
                       'test-input-state', '--target', str(root), '--command', record['command_id'], '--test-file', 'tests/a.py']
            captured = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(captured.returncode, 0, captured.stderr + captured.stdout)
            snapshot = json.loads(captured.stdout)
            self.assertEqual(snapshot['state'], 'captured')
            self.assertFalse(snapshot['execution_performed'])
            self.write(root, 'before.json', snapshot)
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file() and '.git' not in p.parts}
            same = subprocess.run([*command, '--before', 'before.json'], capture_output=True, text=True)
            self.assertEqual(same.returncode, 0, same.stdout + same.stderr)
            self.assertEqual(json.loads(same.stdout)['state'], 'unchanged')
            self.assertEqual(before, {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file() and '.git' not in p.parts})
            self.write(root, 'src/app.py', 'actual edit')
            changed = subprocess.run([*command, '--before', 'before.json'], capture_output=True, text=True)
            self.assertEqual(changed.returncode, 1, changed.stdout + changed.stderr)
            self.assertEqual(json.loads(changed.stdout)['state'], 'changed')
            snapshot['policy_sha256'] = '0' * 64; self.write(root, 'before.json', snapshot)
            stale = subprocess.run([*command, '--before', 'before.json'], capture_output=True, text=True)
            self.assertEqual(stale.returncode, 2, stale.stdout)
            self.assertNotIn('Traceback', stale.stderr)
            for value in (None, [], {}, False, 0, 'capture',
                          {**snapshot, 'policy_sha256': json.loads(captured.stdout)['policy_sha256'], 'inputs': None},
                          {**json.loads(captured.stdout), 'inputs': {}},
                          {**json.loads(captured.stdout), 'schema_version': True}):
                self.write(root, 'before.json', value)
                invalid = subprocess.run([*command, '--before', 'before.json'], capture_output=True, text=True)
                with self.subTest(before=value):
                    self.assertEqual(invalid.returncode, 2, invalid.stdout + invalid.stderr)
                    self.assertEqual(json.loads(invalid.stdout)['state'], 'unavailable')
                    self.assertNotIn('Traceback', invalid.stderr)
            empty = subprocess.run([*command, '--before', ''], capture_output=True, text=True)
            self.assertEqual(empty.returncode, 2, empty.stdout)

    def test_stability_selection_aliases_and_optional_adoption_are_rejected(self):
        execution = {'harness_inputs': ['source.py'], 'configuration_paths': [], 'suite_patterns': ['tests/*.py']}
        for path in ('./tests/a.py', 'tests//a.py', '../tests/a.py', 'tests\\a.py', '/tests/a.py', 'tests/a*.py', 'tests/bad\ud800.py'):
            with self.subTest(path=path), self.assertRaises((ValueError, UnicodeError)):
                selected_inputs(execution, [path])
        self.assertEqual(selected_inputs(execution, ['tests/a.py']), ['source.py', 'tests/a.py'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); policy, _, _ = self.prepare_stability(root)
            for version in (2, 3):
                changed = copy.deepcopy(policy); changed['execution_contract']['schema_version'] = version
                self.assertTrue(TestExecutionContract().policy_failures(changed))
            for value in (None, {}, [], True, 4, 'unknown'):
                changed = copy.deepcopy(policy); changed['commands'][0]['execution']['source_stability'] = value
                with self.subTest(value=value): self.assertTrue(TestExecutionContract().policy_failures(changed))

    def test_stability_budget_limits_and_digest_shape(self):
        execution = {'harness_inputs': ['source.py'], 'configuration_paths': [], 'suite_patterns': ['tests/*.py']}
        for n in (254, 255, 256):
            files = [f'tests/{i}.py' for i in range(n)]
            if n <= 255: self.assertEqual(len(selected_inputs(execution, files)), n + 1)
            else:
                with self.assertRaises(ValueError): selected_inputs(execution, files)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for size in (MAX_FILE_BYTES - 1, MAX_FILE_BYTES, MAX_FILE_BYTES + 1):
                self.write(root, 'source.py', 'x' * size)
                if size <= MAX_FILE_BYTES: capture_inputs(TargetRepositoryView(root), execution, [])
                else:
                    with self.assertRaises(ValueError): capture_inputs(TargetRepositoryView(root), execution, [])
            execution['harness_inputs'] = [f'{i}.cfg' for i in range(9)]
            for i, path in enumerate(execution['harness_inputs']): self.write(root, path, 'x' * MAX_FILE_BYTES if i < 8 else '')
            capture_inputs(TargetRepositoryView(root), execution, [])
            self.write(root, '8.cfg', 'x')
            with self.assertRaises(ValueError): capture_inputs(TargetRepositoryView(root), execution, [])

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

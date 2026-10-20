from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from test_execution_contract import SURFACES, TestExecutionContract, surface_binding_failures
from target_adapter_validation.modules import dispatch_capability_checks
from validate_target_adapter import Validator, AdapterValidatorConfig
from target_validation_support import ManifestData, Scalar
import check_test_first_development as test_first_check


def policy():
    return {
        "schema_version": 1, "policy_kind": "target-test-first-development-policy",
        "project": "fixture", "state": "enabled", "owner": "maintainer",
        "decision_authority": "maintainer", "last_reviewed": "2026-10-16", "evidence_revision": "fixture",
        "suggestion": {"mode": "advisory", "minimum_result": "recommended", "max_per_task": 1, "suppress_after_decline": True, "cost_statement_required": True},
        "available_modes": ["contract-first"],
        "activation_triggers": [{"id": "contract", "state": "required", "mode": "contract-first", "changed_fact_classes": ["behavior"], "conditions": ["contract change"], "test_level_ids": ["unit"], "exceptions": []}],
        "test_levels": [{"id": "unit", "purpose": "unit contract", "feedback_time": "fast", "paths": ["tests/a.py"], "command_ids": ["unit"], "fixtures_and_helpers": ["deterministic fixtures"]}],
        "commands": [{"id": "unit", "command": "never-execute-this-policy-command", "scope": "selected tests", "live_external_actions": "forbidden", "execution": {
            "kind": "automated-test", "configuration_paths": ["test.cfg"], "suite_patterns": ["tests/*.py"], "prerequisites": ["isolated runtime"], "effects": ["temporary-files"], "resources": [{"kind": "directory", "id": "unit-output", "namespace": None, "access": "write", "isolation": "shared"}], "environment": "disposable", "suite_scope": "full", "proof_boundary": "unit", "filtering": {"state": "supported", "syntax_or_reason": "explicit file argument"}
        }}],
        "isolation": {k: "isolated fixture" for k in ("clock", "randomness", "database", "queue", "filesystem", "network", "secrets")},
        "exceptions": [], "evidence_requirements": ["actual result"], "known_gaps": [],
        "execution_contract": {"schema_version": 2, "canonical_policy": ".ai/project/testing/test-first-policy.json", "canonical_coverage_matrix": None, "coverage_not_applicable_reason": "No coverage matrix in this fixture", "timing": "after-manual-review", "red_requirement": "when-authorized", "review_authority": "maintainer", "evidence_records": []},
    }


def record():
    return {
        "schema_version": 2, "record_kind": "target-test-execution-evidence", "command_id": "unit", "repository_revision": "a" * 40,
        "resources": [{"kind": "directory", "id": "unit-output", "namespace": None, "access": "write", "isolation": "shared"}],
        "resource_coordination": {"decision": "serialized", "evidence_ref": "fixture:single-run"},
        "policy_sha256": "b" * 64, "input_sha256": {"tests/a.py": "c" * 64, "test.cfg": "d" * 64},
        "state": "passed", "claim": "full", "proof_boundary": "unit", "environment": "disposable", "authorization": "authorized", "authorization_source": "current task request", "timing_disposition": "manual-review-complete", "availability": "available", "prerequisites_satisfied": True, "filter": None,
        "counts": {"discovered": 1, "executed": 1, "passed": 1, "failed": 0, "skipped": 0},
        "files": {"universe": ["tests/a.py"], "selected": ["tests/a.py"], "executed": ["tests/a.py"], "excluded": []},
        "result_artifact": {"path": "result.txt", "sha256": "e" * 64},
    }


def set_path(value, path, replacement):
    for part in path[:-1]:
        value = value[part]
    value[path[-1]] = replacement


def nested_paths(value, prefix=()):
    if isinstance(value, dict):
        return [path for k, v in value.items() for path in [(*prefix, k), *nested_paths(v, (*prefix, k))]]
    if isinstance(value, list):
        return [path for k, v in enumerate(value) for path in [(*prefix, k), *nested_paths(v, (*prefix, k))]]
    return []


class ExecutionDocumentationTests(unittest.TestCase):
    def setUp(self):
        self.schema = TestExecutionContract().schema
        self.version = self.schema["$defs"]["contract"]["properties"]["schema_version"]["const"]
        self.labels = ("Command/evidence execution contract", "Policy `execution_contract`")
        self.text = "\n".join(f"{label} version {self.version} records the contract." for label in self.labels)

    def failures(self, text, schema=None):
        return test_first_check.execution_documentation_failures(text, self.schema if schema is None else schema)

    def test_current_canonical_document_and_templates_match_the_schema(self):
        self.assertEqual(self.failures(test_first_check.FRAMEWORK.read_text()), [])
        execution = TestExecutionContract()
        policy_template = json.loads(test_first_check.POLICY.read_text())
        self.assertEqual(policy_template["schema_version"], 1)
        self.assertEqual(execution.policy_failures(policy_template, placeholders=True), [])
        evidence = json.loads((ROOT / "templates/target/.ai/assistant/templates/test-execution-evidence.json").read_text())
        self.assertEqual(execution.shape(evidence, "evidence", placeholders=True), [])

    def test_each_reference_rejects_stale_future_and_malformed_versions(self):
        for label in self.labels:
            for version in (str(self.version - 1), str(self.version + 1), f"{self.version}.0", f"{self.version}-invalid", f"0{self.version}", "unknown", ""):
                text = self.text.replace(f"{label} version {self.version}", f"{label} version {version}")
                with self.subTest(label=label, version=version):
                    self.assertTrue(self.failures(text))
            missing = "\n".join(line for line in self.text.splitlines() if not line.startswith(label))
            self.assertTrue(self.failures(missing))
            self.assertTrue(self.failures(self.text + f"\n{label} version {self.version - 1} contradicts it."))

    def test_schema_is_the_oracle_and_wrapping_does_not_change_the_reference(self):
        for text in (self.text, self.text.replace(" ", "\n"), self.text.replace("\n", "\r\n"), self.text.replace(f"version {self.version}", f"version {self.version},")):
            self.assertEqual(self.failures(text), [])
        changed = copy.deepcopy(self.schema)
        for definition in ("contract", "evidence"):
            changed["$defs"][definition]["properties"]["schema_version"]["const"] += 1
        self.assertTrue(self.failures(self.text, changed))
        self.assertEqual(self.failures(self.text.replace(f"version {self.version}", f"version {self.version + 1}"), changed), [])
        changed["$defs"]["evidence"]["properties"]["schema_version"]["const"] += 1
        self.assertTrue(self.failures(self.text.replace(f"version {self.version}", f"version {self.version + 1}"), changed))

    def test_invalid_schema_version_oracles_return_findings(self):
        self.assertTrue(self.failures(self.text, {}))
        for definition in ("contract", "evidence"):
            for value in (None, {}, [], True, 0, -1, float(self.version), str(self.version)):
                changed = copy.deepcopy(self.schema)
                changed["$defs"][definition]["properties"]["schema_version"]["const"] = value
                with self.subTest(definition=definition, value=value):
                    self.assertTrue(self.failures(self.text, changed))
            changed = copy.deepcopy(self.schema)
            del changed["$defs"][definition]["properties"]["schema_version"]["const"]
            self.assertTrue(self.failures(self.text, changed))

    def test_public_source_checker_rejects_each_conflicting_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            paths = {value for value in vars(test_first_check).values()
                     if isinstance(value, Path) and value.is_file() and value.is_relative_to(ROOT)}
            paths.update(ROOT / name for name in (
                "tools/check_test_first_development.py", "schemas/test-execution-contract.schema.json",
                "templates/target/.ai/assistant/templates/test-execution-evidence.json",
            ))
            for source in paths:
                destination = root / source.relative_to(ROOT)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            framework_path = "framework/test-first-development.md"
            policy_path = "templates/target/.ai/project/testing/test-first-policy.json"
            evidence_path = "templates/target/.ai/assistant/templates/test-execution-evidence.json"
            originals = {name: (root / name).read_text() for name in (framework_path, policy_path, evidence_path)}
            text = originals[framework_path]
            variants = [("valid", {}, "")]
            for label in self.labels:
                variants.append((label, {framework_path: text.replace(f"{label} version {self.version}", f"{label} version {self.version - 1}")}, "must match schema"))
            for name, key in ((policy_path, ("execution_contract", "schema_version")), (evidence_path, ("schema_version",))):
                value = json.loads(originals[name])
                set_path(value, key, self.version - 1)
                variants.append((name, {name: json.dumps(value)}, "schema_version"))
            environment = dict(os.environ, PYTHONPATH=str(ROOT / "tools"))
            for label, replacements, diagnostic in variants:
                with self.subTest(label=label):
                    for name, content in {**originals, **replacements}.items():
                        (root / name).write_text(content)
                    result = subprocess.run([sys.executable, "-B", str(root / "tools/check_test_first_development.py")],
                                            cwd=root, env=environment, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0 if label == "valid" else 1, result.stdout + result.stderr)
                    if label != "valid":
                        self.assertIn(diagnostic, result.stdout)
                        self.assertNotIn("Traceback", result.stderr)


class TestExecutionContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = TestExecutionContract()
        self.policy = policy()

    def failures(self, value):
        return self.contract.evidence_failures(value, self.policy["commands"][0], self.policy["execution_contract"])

    def test_valid_policy_and_full_result(self):
        self.assertEqual(self.contract.policy_failures(self.policy), [])
        self.assertEqual(self.failures(record()), [])

    def test_execution_authority_availability_timing_and_filter_are_independent(self):
        for path, value in [(('authorization',), 'awaiting-review'), (('availability',), 'unavailable'), (('prerequisites_satisfied',), False), (('timing_disposition',), 'not-run')]:
            item = record(); set_path(item, path, value)
            with self.subTest(path=path): self.assertTrue(self.failures(item))
        self.policy['commands'][0]['execution']['filtering']['state'] = 'unsupported'
        item = record(); item['filter'] = 'tests/a.py'; item['claim'] = 'focused'
        self.assertTrue(self.failures(item))
        self.policy['execution_contract']['red_requirement'] = 'required-before-implementation'
        # Review or an explicit request can authorize RED before implementation.
        self.assertEqual(self.contract.policy_failures(self.policy), [])

    def test_unexecuted_static_and_mocked_evidence_cannot_upgrade_claims(self):
        for state in ['authored', 'discovered', 'skipped', 'blocked']:
            item = record(); item['state'] = state
            with self.subTest(state=state): self.assertTrue(self.failures(item))
        item = record(); item['counts'] = {'discovered': 1, 'executed': 0, 'passed': 0, 'failed': 0, 'skipped': 1}; item['files']['executed'] = []
        self.assertTrue(self.failures(item))
        self.policy['commands'][0]['execution']['kind'] = 'metadata-check'
        self.assertTrue(self.contract.policy_failures(self.policy))
        self.assertTrue(self.failures(record()))
        self.policy['commands'][0]['execution']['kind'] = 'automated-test'
        self.policy['commands'][0]['execution']['proof_boundary'] = 'browser-mocked'
        item = record(); item['proof_boundary'] = 'end-to-end'
        self.assertTrue(self.failures(item))

    def test_suite_universe_exclusions_and_counts_are_conserved(self):
        item = record(); item['files']['universe'].append('tests/b.py')
        self.assertTrue(self.failures(item))
        item['files']['excluded'] = [{'path': 'tests/b.py', 'reason': 'explicit unsupported fixture'}]
        self.assertTrue(self.failures(item))
        item['claim'] = 'suite'
        self.assertEqual(self.failures(item), [])
        for reason in ['', 'unknown', '{EXPLAIN}']:
            item['files']['excluded'][0]['reason'] = reason
            self.assertTrue(self.failures(item))
        for version in [True, 2.0, 0, 1]:
            item = record(); item['schema_version'] = version
            with self.subTest(version=version): self.assertTrue(self.failures(item))
        item = record(); item['counts']['executed'] = True
        self.assertTrue(self.failures(item))

    def test_discovery_without_execution_is_not_misreported_as_skipped_or_passed(self):
        item=record(); item.update(state='discovered',claim='none',timing_disposition='not-run',authorization='awaiting-review')
        item['counts']={'discovered':3,'executed':0,'passed':0,'failed':0,'skipped':0,'not_run':3}
        item['files']['executed']=[]; item['result_artifact']=None
        self.assertEqual(self.failures(item), [])
        item['claim']='full'
        self.assertTrue(self.failures(item))

    def test_all_required_evidence_fields_are_required(self):
        for key in record():
            item=record(); del item[key]
            with self.subTest(key=key): self.assertTrue(self.failures(item))

    def test_all_nested_json_mutations_return_findings_without_crashing(self):
        for baseline, check in [(self.policy, self.contract.policy_failures), (record(), self.failures)]:
            for path in nested_paths(baseline):
                for bad in [None, True, 7, '', [], {}, ['wrong'], {'wrong': []}]:
                    changed = copy.deepcopy(baseline); set_path(changed, path, bad)
                    with self.subTest(path=path, bad=bad): self.assertIsInstance(check(changed), list)

    def test_surface_binding_is_safe_for_malformed_yaml_and_cannot_override_policy(self):
        for text in ['', '---\n[\n---\n', '---\n[]\n---\n', '---\nalatyr_test_execution: null\n---\n']:
            self.assertTrue(surface_binding_failures(text))
        for path in SURFACES:
            text=(ROOT/'templates/target'/path).read_text()
            for variant in [text, text.replace('\n','\r\n'), '\ufeff'+text]:
                self.assertEqual(surface_binding_failures(variant), [])

    def test_policy_rejects_unresolved_text_unsafe_patterns_and_wrong_environments(self):
        for key, value in [('prerequisites', ['{RESOLVE}']), ('suite_patterns', ['../tests/*']), ('effects', ['shared-db-writes'])]:
            p = policy(); p['commands'][0]['execution'][key] = value
            with self.subTest(key=key): self.assertTrue(self.contract.policy_failures(p))
        p = policy(); p['commands'][0]['execution']['filtering']['syntax_or_reason'] = 'unknown'
        self.assertTrue(self.contract.policy_failures(p))
        item = record(); item['environment'] = 'shared-review'
        self.assertTrue(self.failures(item))
        self.policy['commands'][0]['execution']['proof_boundary'] = 'browser-mocked'
        item = record(); item['proof_boundary'] = 'browser-mocked'
        self.assertTrue(self.failures(item))
        item['claim'] = 'suite'
        self.assertEqual(self.failures(item), [])


class RegisteredTestingExecutionTests(unittest.TestCase):
    def write(self, root, path, data):
        target = root/path; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data) if not isinstance(data, str) else data)

    def fixture(self, root):
        p = policy(); p['execution_contract']['evidence_records'] = ['current.json']
        for path in SURFACES:
            self.write(root, path, (ROOT/'templates/target'/path).read_text())
        self.write(root, '.ai/assistant/templates/test-execution-evidence.json', (ROOT/'templates/target/.ai/assistant/templates/test-execution-evidence.json').read_text())
        for path in ['.ai/project/testing/README.md', '.ai/assistant/context/intents/test-first-request.json', '.ai/assistant/flows/test-first-configuration.flow.md', '.ai/framework/test-first-development.md']:
            self.write(root, path, 'fixture')
        self.write(root, '.ai/assistant/module-profile.md', 'Module: `test-first-development`\nState: `enabled`\n')
        self.write(root, '.ai/assistant/operation-catalog.json', {'operations': [{'id':'test-first-configuration','required_module':'core-profile'},{'id':'test-first-change','required_module':'test-first-development'}]})
        self.write(root, '.ai/assistant/context-router.json', {'intent_overlays':{'test-first-request':{'operation_candidates':['test-first-configuration','test-first-change'],'required_module':'core-profile','activation_target_module':'test-first-development','execution_required_module':'test-first-development','disabled_module_behavior':'configuration only'}}})
        self.write(root, '.ai/project/testing/test-first-policy.json', p)
        for path in ['tests/a.py', 'src/app.py', 'test.cfg', 'result.txt']: self.write(root, path, 'fixture')
        subprocess.run(['git','init','-q'], cwd=root, check=True)
        subprocess.run(['git','add','.'], cwd=root, check=True)
        subprocess.run(['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture'], cwd=root, check=True)
        r = record(); r['repository_revision'] = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        digest = lambda path: hashlib.sha256((root/path).read_bytes()).hexdigest()
        r['policy_sha256'] = digest('.ai/project/testing/test-first-policy.json')
        r['input_sha256'] = {path:digest(path) for path in ['tests/a.py','test.cfg']}
        r['result_artifact']['sha256'] = digest('result.txt')
        self.write(root, 'current.json', r)
        return p, r

    def findings(self, root, *, manifest=None, allow_placeholders=False):
        validator = Validator(root, framework_source=None, diff_ref=None, approval_records=[], enforce_approval_scope=False, change_packages=[], enforce_change_package=False, migration_diff=None, allow_placeholders=allow_placeholders, allow_local_paths=[], config=AdapterValidatorConfig())
        dispatch_capability_checks(validator, ['test-first-development'], manifest)
        return validator.findings

    def test_registered_handler_checks_current_records_and_freshness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); p, r = self.fixture(root)
            self.assertEqual([x.code for x in self.findings(root) if x.level=='error'], [])
            for mutation in ['zero', 'stale', 'missing', 'malformed']:
                self.write(root, 'current.json', r)
                with self.subTest(mutation=mutation):
                    changed = copy.deepcopy(r)
                    if mutation=='zero': changed['counts']={'discovered':1,'executed':0,'passed':0,'failed':0,'skipped':1}
                    elif mutation=='stale': changed['repository_revision']='b'*40
                    elif mutation=='missing': (root/'current.json').unlink()
                    else: changed['authorization']={}
                    if mutation!='missing': self.write(root,'current.json',changed)
                    self.assertTrue([x for x in self.findings(root) if x.level=='error'])
            self.write(root,'current.json',r)
            self.write(root,'tests/a.py','changed test')
            self.assertIn('TDD_EXECUTION_EVIDENCE_STALE', [x.code for x in self.findings(root)])

    def test_legacy_policy_warns_without_inventing_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); p,_=self.fixture(root); p.pop('execution_contract')
            self.write(root,'.ai/project/testing/test-first-policy.json',p)
            self.assertIn('TDD_EXECUTION_CONTRACT_MISSING', [x.code for x in self.findings(root)])
            manifest=ManifestData(set(), {('schema_version',):Scalar('74',1)}, {}, [])
            missing=[x for x in self.findings(root,manifest=manifest) if x.code=='TDD_EXECUTION_CONTRACT_MISSING']
            self.assertEqual([x.level for x in missing], ['error'])

    def test_allow_placeholders_does_not_skip_resolved_record_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); _, r=self.fixture(root)
            r['authorization']='not-authorized'; self.write(root,'current.json',r)
            self.assertIn('TDD_EXECUTION_EVIDENCE', [x.code for x in self.findings(root,allow_placeholders=True)])

    def test_suite_discovery_catches_new_files_and_exclusions_before_full_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); _, r=self.fixture(root)
            self.write(root,'tests/b.py','new test')
            self.assertIn('TDD_SUITE_SELECTION_DRIFT', [x.code for x in self.findings(root)])
            r['claim']='suite'; r['files']['universe'].append('tests/b.py')
            r['files']['excluded']=[{'path':'tests/b.py','reason':'explicit unsupported fixture'}]
            r['input_sha256']['tests/b.py']=hashlib.sha256((root/'tests/b.py').read_bytes()).hexdigest()
            self.write(root,'current.json',r)
            self.assertEqual([x.code for x in self.findings(root) if x.level=='error'], [])
            r['claim']='full'; self.write(root,'current.json',r)
            self.assertIn('TDD_EXECUTION_EVIDENCE', [x.code for x in self.findings(root)])

    def test_implementation_edits_and_result_collisions_do_not_hide_staleness(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); _, r=self.fixture(root)
            self.write(root,'src/app.py','changed implementation')
            self.assertIn('TDD_EXECUTION_EVIDENCE_STALE', [x.code for x in self.findings(root)])
            r['input_sha256']['src/app.py']=hashlib.sha256((root/'src/app.py').read_bytes()).hexdigest()
            self.write(root,'current.json',r)
            self.assertEqual([x.code for x in self.findings(root) if x.level=='error'], [])
            r['input_sha256']['tests/a.py']='0'*64
            r['result_artifact']={'path':'tests/a.py','sha256':hashlib.sha256((root/'tests/a.py').read_bytes()).hexdigest()}
            self.write(root,'current.json',r)
            self.assertIn('TDD_EXECUTION_EVIDENCE_STALE', [x.code for x in self.findings(root)])

    def test_canonical_projection_binding_and_artifact_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); p, _=self.fixture(root)
            self.write(root,'result.txt','tampered result')
            self.assertIn('TDD_EXECUTION_EVIDENCE_STALE', [x.code for x in self.findings(root)])
            p['execution_contract']['canonical_policy']='testing-policy.json'
            self.write(root,'testing-policy.json',p)
            mirror=copy.deepcopy(p); mirror['owner']='different owner'
            self.write(root,'.ai/project/testing/test-first-policy.json',mirror)
            self.assertIn('TDD_POLICY_PROJECTION_DRIFT', [x.code for x in self.findings(root)])
            self.write(root,SURFACES[0],'no policy binding')
            self.assertIn('TDD_SURFACE_POLICY_BINDING', [x.code for x in self.findings(root)])

    def test_deleted_implementation_bindings_do_not_allow_missing_test_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); _, r=self.fixture(root)
            (root/'src/app.py').unlink(); r['input_sha256']['src/app.py']=None
            self.write(root,'current.json',r)
            self.assertEqual([x.code for x in self.findings(root) if x.level=='error'], [])
            self.write(root,'src/app.py','recreated implementation')
            self.assertIn('TDD_EXECUTION_EVIDENCE_STALE', [x.code for x in self.findings(root)])
            (root/'src/app.py').unlink(); (root/'tests/a.py').unlink()
            r['input_sha256']['tests/a.py']=None; self.write(root,'current.json',r)
            self.assertIn('TDD_EXECUTION_EVIDENCE', [x.code for x in self.findings(root)])

    def test_old_policy_enum_reference_and_routing_mutations_do_not_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); p,_=self.fixture(root)
            paths=[('suggestion','mode'),('suggestion','minimum_result'),('available_modes',),('activation_triggers',0,'state'),('activation_triggers',0,'mode'),('activation_triggers',0,'exceptions'),('activation_triggers',0,'test_level_ids'),('test_levels',0,'command_ids'),('commands',0,'live_external_actions')]
            for path in paths:
                for bad in [None, True, 7, {}, [], [{}]]:
                    changed=copy.deepcopy(p);set_path(changed,path,bad)
                    self.write(root,'.ai/project/testing/test-first-policy.json',changed)
                    with self.subTest(path=path,bad=bad):
                        findings = self.findings(root)
                        if bad != [] or path != ('activation_triggers',0,'exceptions'):
                            self.assertTrue([x for x in findings if x.level=='error'])
            self.write(root,'.ai/project/testing/test-first-policy.json',p)
            for bad in [None, True, 7, {}, [{}]]:
                self.write(root,'.ai/assistant/operation-catalog.json',{'operations':bad})
                self.assertTrue([x for x in self.findings(root) if x.level=='error'])

    def test_source_checker_cli_uses_the_shared_contract(self):
        result=subprocess.run([sys.executable,str(ROOT/'tools/check_test_first_development.py')],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

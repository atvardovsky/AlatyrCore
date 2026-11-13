from __future__ import annotations

import hashlib
import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.context import (  # noqa: E402
    TargetFileState,
    TargetPathEscapeError,
    TargetRepositoryView,
    ValidationContext,
)
from validate_target_adapter import AdapterValidatorConfig, Validator  # noqa: E402
from target_validation_support import GitEvidenceState, GitEvidenceView  # noqa: E402
import validate_target_adapter  # noqa: E402


class HistoricalLocalPathBindingTests(unittest.TestCase):
    def setUp(self):
        import base64
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.name = '.ai/assistant/task-evidence/fixture/history.md'
        self.literal = '/tmp/historical-control/old'
        self.document = self.root / self.name
        self.document.parent.mkdir(parents=True)
        self.document.write_text(self.literal + '\n', encoding='utf-8')
        self.row = {'path': self.name, 'sha256': hashlib.sha256(self.document.read_bytes()).hexdigest(),
                    'literals_base64': [base64.b64encode(self.literal.encode()).decode()],
                    'reason': 'Immutable historical evidence; no current authority.'}
        self.config_path = self.root / '.ai/assistant/validator-config.json'

    def validator(self, rows=None, **kwargs):
        from validate_target_adapter import load_validator_config
        self.config_path.write_text(json.dumps({'schema_version': 1,
            'historical_local_path_bindings': [self.row] if rows is None else rows}), encoding='utf-8')
        config, findings = load_validator_config(self.root, None)
        return self.from_config(config, initial_findings=findings, **kwargs)

    def from_config(self, config, **kwargs):
        values = dict(framework_source=None, diff_ref=None, approval_records=[],
            enforce_approval_scope=False, change_packages=[], enforce_change_package=False,
            migration_diff=None, allow_placeholders=False, allow_local_paths=[], config=config)
        values.update(kwargs)
        return Validator(self.root, **values)

    def test_exact_binding_exempts_only_its_historical_file_and_literal(self):
        current = self.root / '.ai/project/current.md'
        current.parent.mkdir(parents=True)
        current.write_text(self.literal + '\n' + self.literal + '-lookalike\n', encoding='utf-8')
        self.document.write_text(self.literal + '\n/tmp/unlisted/value\n', encoding='utf-8')
        self.row['sha256'] = hashlib.sha256(self.document.read_bytes()).hexdigest()
        validator = self.validator()
        validator.check_local_paths()
        errors = [row for row in validator.findings if row.level == 'error']
        self.assertEqual([row.code for row in errors], ['LOCAL_PATH_LEAKAGE'] * 3)
        self.assertEqual(sum(row.path.startswith('.ai/project/current.md:') for row in errors), 2)
        self.assertTrue(any(row.path == self.name + ':2' for row in errors))

    def test_config_has_no_plaintext_path_exemption(self):
        self.row['reason'] = self.literal
        validator = self.validator()
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_LEAKAGE'
                            and row.path == '.ai/assistant/validator-config.json' for row in validator.findings))

    def test_absent_bindings_preserve_existing_failures(self):
        validator = self.validator([])
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_LEAKAGE' for row in validator.findings))

    def test_exact_decoded_structured_literal(self):
        import base64
        self.document.unlink()
        self.name = '.ai/assistant/task-evidence/fixture/history.json'
        self.document = self.root / self.name
        self.document.write_text(r'{"path":"\/tmp\/historical-control\/old"}', encoding='utf-8')
        self.row.update(path=self.name, sha256=hashlib.sha256(self.document.read_bytes()).hexdigest(),
                        literals_base64=[base64.b64encode(self.literal.encode()).decode()])
        validator = self.validator()
        validator.check_local_paths()
        self.assertEqual([row.code for row in validator.findings], ['VALIDATOR_CONFIG_LOADED'])

    def test_malformed_bindings_fail_closed_as_a_complete_set(self):
        import base64
        import copy
        invalid = [None, {}, [None], [{**self.row, 'extra': True}],
            [{**self.row, 'path': '../outside.md'}], [{**self.row, 'path': '/tmp/outside.md'}],
            [{**self.row, 'path': '.ai/assistant/task-evidence-lookalike/history.md'}],
            [{**self.row, 'path': '.ai/project/current.md'}],
            [{**self.row, 'path': self.name.replace('/', '\\')}],
            [{**self.row, 'sha256': '0' * 64}],
            [{**self.row, 'literals_base64': []}], [{**self.row, 'literals_base64': ['']}],
            [{**self.row, 'literals_base64': [base64.b64encode(b'/tmp/not-present').decode()]}],
            [{**self.row, 'literals_base64': self.row['literals_base64'] * 2}],
            [self.row, copy.deepcopy(self.row)],
            [self.row, {**self.row, 'path': self.name.upper()}], [self.row] * 65]
        for rows in invalid:
            with self.subTest(rows=rows):
                validator = self.validator(rows)
                # None means the helper default; explicitly retain a malformed null here.
                if rows is None:
                    validator.config.historical_local_path_bindings = None
                validator.check_local_paths()
                self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))
                self.assertTrue(any(row.code == 'LOCAL_PATH_LEAKAGE' for row in validator.findings))

    def test_noncanonical_or_invalid_encoded_literals_reject(self):
        import base64
        values = ['%%%=', 'YQ', 'YQ===', 'Y R==', 'YR==', '_w==', '/w==',
                  self.row['literals_base64'][0] + '\n', base64.b64encode(b'not a local path').decode()]
        for value in values:
            with self.subTest(value=value):
                validator = self.validator([{**self.row, 'literals_base64': [value]}])
                validator.check_local_paths()
                self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))
                self.assertTrue(any(row.code == 'LOCAL_PATH_LEAKAGE' for row in validator.findings))

    def test_missing_changed_nontext_and_oversized_history_reject(self):
        from target_adapter_validation import local_paths
        original = self.document.read_bytes()
        for data in (b'changed', b'\xff', b'\x00', None):
            with self.subTest(data=data):
                self.document.write_bytes(original)
                validator = self.validator()
                if data is None:
                    self.document.unlink()
                else:
                    self.document.write_bytes(data)
                validator.check_local_paths()
                self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))
        self.document.write_bytes(original)
        validator = self.validator()
        with patch.object(local_paths, 'MAX_HISTORY_FILE_BYTES', 1):
            validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))

    def test_leaf_and_ancestor_symlinks_reject(self):
        original = self.document.read_bytes()
        self.document.unlink()
        outside = self.root / 'original.md'
        outside.write_bytes(original)
        try:
            self.document.symlink_to(outside)
        except OSError as exc:
            self.skipTest(str(exc))
        validator = self.validator()
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))
        self.document.unlink()
        self.document.parent.rmdir()
        alternate = self.root / 'alternate'
        alternate.mkdir()
        (alternate / 'history.md').write_bytes(original)
        self.document.parent.symlink_to(alternate, target_is_directory=True)
        validator = self.validator()
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))

    def test_selected_current_authority_is_not_exempt(self):
        for key in ('approval_records', 'problem_models', 'change_packages'):
            with self.subTest(key=key):
                validator = self.validator(**{key: [self.document]})
                validator.check_local_paths()
                self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))
                self.assertTrue(any(row.code == 'LOCAL_PATH_LEAKAGE' for row in validator.findings))

    def test_current_package_cannot_use_a_retained_plan_exemption(self):
        old = self.document
        self.name = '.ai/assistant/change-packages/old-retained-' + self.row['sha256'] + '-plan.md'
        self.document = self.root / self.name
        self.document.parent.mkdir(parents=True, exist_ok=True)
        old.rename(self.document)
        self.row['path'] = self.name
        index = self.document.parent / 'index.json'
        package = self.document.parent / 'current.json'
        index.write_text(json.dumps({'records': [{'record': '.ai/assistant/change-packages/current.json'}]}))
        package.write_text(json.dumps({'evidence_classification': 'historical-record',
                                      'status': 'implementing', 'plan': {'file': self.name}}))
        validator = self.validator()
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))
        package.write_text(json.dumps({'evidence_classification': 'historical-record',
                                      'status': 'complete', 'plan': {'file': self.name}}))
        validator = self.validator()
        validator.check_local_paths()
        self.assertEqual([row.code for row in validator.findings], ['VALIDATOR_CONFIG_LOADED'])

    def test_configuration_drift_before_and_after_construction_blocks(self):
        from validate_target_adapter import load_validator_config
        self.validator()
        config, _ = load_validator_config(self.root, None)
        self.config_path.write_text(self.config_path.read_text() + '\n')
        validator = self.from_config(config)
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))
        validator = self.validator()
        validator.check_local_paths()
        self.assertEqual([row.code for row in validator.findings], ['VALIDATOR_CONFIG_LOADED'])
        self.config_path.write_text(self.config_path.read_text() + '\n')
        self.assertTrue(validator.context.finalize())
        self.document.write_text(self.literal + '-changed\n')
        validator = self.validator()
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))

    def test_duplicate_configuration_fields_do_not_grant_exemptions(self):
        self.validator()
        raw = self.config_path.read_text()
        self.config_path.write_text(raw[:-1] + ', "schema_version": 1}')
        config, errors = validate_target_adapter.load_validator_config(self.root, None)
        validator = self.from_config(config, initial_findings=errors)
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))

    def test_selected_package_approval_lists_and_selected_model_evidence_remain_current(self):
        for kind in ('package', 'model'):
            with self.subTest(kind=kind):
                owner = self.root / '.ai/assistant/task-evidence/fixture/owner.json'
                data = ({'evidence_classification': 'historical-record', 'status': 'complete',
                         'approved_scope': {'approval_records': [self.name]}}
                        if kind == 'package' else {'proof': {'path': self.name}})
                owner.write_text(json.dumps(data))
                kwargs = {'change_packages' if kind == 'package' else 'problem_models': [owner]}
                validator = self.validator(**kwargs)
                validator.check_local_paths()
                self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))
                self.assertTrue(any(row.code == 'LOCAL_PATH_LEAKAGE' for row in validator.findings))

    def test_initial_config_acquisition_is_bounded_before_decoding(self):
        self.config_path.write_bytes(b' ' * (4 * 1024 * 1024 + 1))
        config, errors = validate_target_adapter.load_validator_config(self.root, None)
        self.assertTrue(any(row.level == 'error' and row.code == 'VALIDATOR_CONFIG_READ_ERROR' for row in errors))
        self.assertEqual(config.historical_local_path_bindings, ())

    def test_project_root_alias_preserves_exact_config_binding(self):
        self.validator()
        alias = self.root.parent / (self.root.name + '-alias')
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except OSError as exc:
            self.skipTest(str(exc))
        self.addCleanup(alias.unlink)
        config, findings = validate_target_adapter.load_validator_config(alias, None)
        validator = self.from_config(config, initial_findings=findings)
        validator.check_local_paths()
        self.assertEqual([row.code for row in validator.findings], ['VALIDATOR_CONFIG_LOADED'])

    def test_selected_model_authority_and_evidence_reference_fields_stay_strict(self):
        owner = self.root / '.ai/assistant/task-evidence/fixture/owner.json'
        for key in ('authority_ref', 'normative_source_ref', 'positive_evidence_refs', 'enforcement_refs'):
            with self.subTest(key=key):
                owner.write_text(json.dumps({key: [self.name] if key.endswith('_refs') else self.name}))
                validator = self.validator(problem_models=[owner])
                validator.check_local_paths()
                self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))

    def test_indexed_validated_package_bound_to_selected_model_is_current(self):
        owner = self.root / '.ai/assistant/task-evidence/fixture/owner.json'
        owner.write_text('{}')
        package = self.root / '.ai/assistant/change-packages/current.json'
        package.parent.mkdir(parents=True)
        package.write_text(json.dumps({'evidence_classification': 'historical-record', 'status': 'validated',
            'incident_continuity': {'problem_model': {'path': owner.relative_to(self.root).as_posix()}},
            'plan': {'file': self.name}}))
        (package.parent / 'index.json').write_text(json.dumps({'records': [{'record': package.relative_to(self.root).as_posix()}]}))
        validator = self.validator(problem_models=[owner])
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))

    def test_bindings_without_the_parsed_config_owner_fail_closed(self):
        validator = self.validator()
        validator.config.source = None
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))

    def test_hardlinked_history_and_malformed_structured_bytes_fail_closed(self):
        import os
        linked = self.root / 'linked.md'
        try:
            os.link(self.document, linked)
        except OSError as exc:
            self.skipTest(str(exc))
        validator = self.validator()
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))
        linked.unlink()
        self.document.unlink()
        self.name = '.ai/assistant/task-evidence/fixture/history.json'
        self.document = self.root / self.name
        self.document.write_text('{"path": "' + self.literal + '"')
        self.row.update(path=self.name, sha256=hashlib.sha256(self.document.read_bytes()).hexdigest())
        validator = self.validator()
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))
        self.assertTrue(any(row.code == 'LOCAL_PATH_LEAKAGE' for row in validator.findings))

    def test_selected_approval_plan_and_active_header_owner_stay_current(self):
        owner = self.root / '.ai/assistant/task-evidence/fixture/owner.json'
        owner.write_text(json.dumps({'plan': {'file': self.name}}))
        validator = self.validator(approval_records=[owner])
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))
        active = self.root / '.ai/assistant/active-tasks.json'
        active.write_text(json.dumps({'tasks': [{'state': 'active', 'canonical_owners': [self.name]}]}))
        validator = self.validator()
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))

    def test_schema_rejection_does_not_install_optional_bindings(self):
        self.validator()
        data = json.loads(self.config_path.read_text())
        data['schema_version'] = 999
        self.config_path.write_text(json.dumps(data))
        config, findings = validate_target_adapter.load_validator_config(self.root, None)
        self.assertEqual(config.historical_local_path_bindings, ())
        validator = self.from_config(config, initial_findings=findings)
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'VALIDATOR_CONFIG_SCHEMA_VERSION' for row in validator.findings))
        self.assertTrue(any(row.code == 'LOCAL_PATH_LEAKAGE' for row in validator.findings))

    def test_valid_literal_with_noncanonical_pad_bits_is_rejected(self):
        import base64
        literal = self.literal + 'x'
        while len(literal.encode()) % 3 != 1:
            literal += 'x'
        self.document.write_text(literal + '\n')
        canonical = base64.b64encode(literal.encode()).decode()
        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
        encoded = canonical[:-3] + alphabet[alphabet.index(canonical[-3]) | 1] + '=='
        self.assertEqual(base64.b64decode(encoded, validate=True), literal.encode())
        self.row.update(sha256=hashlib.sha256(self.document.read_bytes()).hexdigest(), literals_base64=[encoded])
        validator = self.validator()
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))

    def test_binary_rejection_is_independent_of_the_file_hash(self):
        for raw in (b'\xff', b'\x00' + self.literal.encode()):
            with self.subTest(raw=raw):
                self.document.write_bytes(raw)
                self.row['sha256'] = hashlib.sha256(raw).hexdigest()
                validator = self.validator()
                validator.check_local_paths()
                self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))

    def test_unique_row_and_literal_count_limits_are_independent(self):
        import base64
        rows = []
        for index in range(65):
            name = self.name.replace('history.md', f'history{index}.md')
            (self.root / name).write_bytes(self.document.read_bytes())
            rows.append({**self.row, 'path': name})
        validator = self.validator(rows)
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))
        literals = [self.literal + str(index) for index in range(65)]
        self.document.write_text('\n'.join(literals) + '\n')
        self.row.update(sha256=hashlib.sha256(self.document.read_bytes()).hexdigest(),
                        literals_base64=[base64.b64encode(value.encode()).decode() for value in literals])
        validator = self.validator()
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))

    def test_aggregate_limit_and_all_or_nothing_binding_disposition(self):
        from target_adapter_validation import local_paths
        second = {**self.row, 'path': self.name.replace('history.md', 'second.md')}
        (self.root / second['path']).write_bytes(self.document.read_bytes())
        validator = self.validator([self.row, second])
        budget = self.config_path.stat().st_size * 2 + self.document.stat().st_size * 2
        with patch.object(local_paths, 'MAX_HISTORY_TOTAL_BYTES', budget - 1):
            validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))
        self.assertEqual(sum(row.code == 'LOCAL_PATH_LEAKAGE' for row in validator.findings), 2)
        validator = self.validator([self.row, second])
        with patch.object(local_paths, 'MAX_HISTORY_TOTAL_BYTES', budget):
            validator.check_local_paths()
        self.assertEqual([row.code for row in validator.findings], ['VALIDATOR_CONFIG_LOADED'])

    def test_retained_plan_name_hash_and_parsed_binding_mutation_reject(self):
        original = self.document
        for embedded in ('0' * 64, self.row['sha256'][:-1]):
            with self.subTest(embedded=embedded):
                name = '.ai/assistant/change-packages/old-retained-' + embedded + '-plan.md'
                path = self.root / name
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(original.read_bytes())
                validator = self.validator([{**self.row, 'path': name}])
                validator.check_local_paths()
                self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))
                path.unlink()
        validator = self.validator()
        validator.config.historical_local_path_bindings[0]['reason'] += ' altered'
        validator.check_local_paths()
        self.assertTrue(any(row.code == 'LOCAL_PATH_SCAN_INCOMPLETE' for row in validator.findings))


class ValidationContextTests(unittest.TestCase):
    def test_validator_phase_plan_is_closed_and_stably_ordered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            validator = Validator(
                Path(directory),
                framework_source=None,
                diff_ref=None,
                approval_records=[],
                enforce_approval_scope=False,
                change_packages=[],
                enforce_change_package=False,
                migration_diff=None,
                allow_placeholders=True,
                allow_local_paths=[],
                config=AdapterValidatorConfig(),
            )

            phases = validator.validation_phases(None, "full", set())
            phase_ids = [phase.phase_id for phase in phases]

            self.assertEqual(phase_ids[0], "installation-state")
            self.assertEqual(phase_ids[-1], "finalize-inputs")
            self.assertEqual(len(phase_ids), len(set(phase_ids)))
            self.assertTrue(
                all(
                    dependency in phase_ids[:index]
                    for index, phase in enumerate(phases)
                    for dependency in phase.dependencies
                )
            )
            self.assertEqual(
                next(phase for phase in phases if phase.phase_id == "capabilities").cost_class,
                "heavy",
            )
            self.assertEqual(
                set(phases[-1].dependencies),
                set(phase_ids[:-1]),
            )

    def test_git_evidence_view_caches_queries_and_detects_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            tracked = target / "tracked.txt"
            tracked.write_text("before\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=target, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Alatyr Tests",
                    "-c",
                    "user.email=tests@example.invalid",
                    "commit",
                    "-qm",
                    "Create fixture",
                ],
                cwd=target,
                check=True,
            )
            evidence = GitEvidenceView(target)

            first = evidence.resolve_ref("HEAD")
            second = evidence.resolve_ref("HEAD")

            self.assertEqual(first, second)
            self.assertEqual(evidence.telemetry()["query_misses"], 1)
            self.assertEqual(evidence.telemetry()["cache_hits"], 1)
            tracked.write_text("after\n", encoding="utf-8")

            self.assertFalse(evidence.finalize())
            self.assertEqual(evidence.telemetry()["stability"], "mutated")

    def test_git_evidence_uses_one_snapshot_per_observation_and_reuses_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            tracked = target / "tracked.txt"
            tracked.write_text("stable\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=target, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Alatyr Tests",
                    "-c",
                    "user.email=tests@example.invalid",
                    "commit",
                    "-qm",
                    "Create fixture",
                ],
                cwd=target,
                check=True,
            )
            evidence = GitEvidenceView(target)

            with patch.object(
                evidence,
                "_repository_snapshot",
                wraps=evidence._repository_snapshot,
            ) as snapshot:
                self.assertTrue(evidence.finalize())
                self.assertEqual(evidence.telemetry()["stability"], "stable")

            self.assertEqual(snapshot.call_count, 1)

            tracked.write_text("mutated\n", encoding="utf-8")
            self.assertFalse(evidence.finalize())

    def test_git_evidence_preserves_normal_detached_unborn_and_non_repo_states(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            tracked = target / "tracked.txt"
            tracked.write_text("stable\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=target, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Alatyr Tests",
                    "-c",
                    "user.email=tests@example.invalid",
                    "commit",
                    "-qm",
                    "Create fixture",
                ],
                cwd=target,
                check=True,
            )

            normal = GitEvidenceView(target)
            self.assertIs(normal.initial_state, GitEvidenceState.STABLE)
            self.assertIsNotNone(normal.head_revision())
            self.assertNotEqual(normal.branch_name(), "detached HEAD")
            self.assertTrue(normal.finalize())

            head_change = GitEvidenceView(target)
            tracked.write_text("next revision\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=target, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Alatyr Tests",
                    "-c",
                    "user.email=tests@example.invalid",
                    "commit",
                    "-qm",
                    "Advance fixture",
                ],
                cwd=target,
                check=True,
            )
            self.assertFalse(head_change.finalize())

            branch_change = GitEvidenceView(target)
            subprocess.run(
                ["git", "switch", "-q", "-c", "alternate"], cwd=target, check=True
            )
            self.assertFalse(branch_change.finalize())

            subprocess.run(["git", "checkout", "--detach", "-q"], cwd=target, check=True)
            detached = GitEvidenceView(target)
            self.assertIs(detached.initial_state, GitEvidenceState.STABLE)
            self.assertEqual(detached.branch_name(), "detached HEAD")
            self.assertTrue(detached.finalize())

        with tempfile.TemporaryDirectory() as directory:
            unborn_target = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=unborn_target, check=True)
            unborn = GitEvidenceView(unborn_target)
            self.assertIs(unborn.initial_state, GitEvidenceState.UNAVAILABLE)
            self.assertIsNone(unborn.head_revision())
            self.assertIsNotNone(unborn.branch_name())
            self.assertFalse(unborn.finalize())

        with tempfile.TemporaryDirectory() as directory:
            unavailable = GitEvidenceView(Path(directory))
            self.assertIs(unavailable.initial_state, GitEvidenceState.UNAVAILABLE)
            self.assertIsNone(unavailable.head_revision())
            self.assertIsNone(unavailable.branch_name())
            self.assertFalse(unavailable.finalize())

    def test_validator_records_sequential_phase_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            validator = Validator(
                Path(directory),
                framework_source=None,
                diff_ref=None,
                approval_records=[],
                enforce_approval_scope=False,
                change_packages=[],
                enforce_change_package=False,
                migration_diff=None,
                allow_placeholders=True,
                allow_local_paths=[],
                config=AdapterValidatorConfig(),
            )

            validator.run()

            phase_ids = [item["phase_id"] for item in validator.phase_telemetry]
            self.assertEqual(phase_ids[0], "installation-state")
            self.assertEqual(phase_ids[-1], "finalize-inputs")
            self.assertTrue(
                all(item["duration_seconds"] >= 0 for item in validator.phase_telemetry)
            )
            self.assertEqual(
                validator.phase_telemetry[-1]["cost_class"], "standard"
            )

    def test_legacy_name_preserves_repository_view_contract(self) -> None:
        self.assertTrue(issubclass(ValidationContext, TargetRepositoryView))

    def test_exposes_coherent_bytes_text_json_and_digest_apis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            path = target / "example.json"
            for ending in (b'\n', b'\r\n'):
                with self.subTest(ending=ending):
                    raw = b'{"value": "before"}' + ending
                    path.write_bytes(raw)
                    context = ValidationContext(target)
                    byte_result = context.read_bytes_result(path)
                    text_result = context.read_text_result(path)
                    json_result = context.read_json_result(path)
                    path.write_bytes(b'{"value": "after"}' + ending)

                    self.assertEqual(byte_result.value, raw)
                    self.assertEqual(text_result.value, raw.decode('utf-8'))
                    self.assertEqual(json_result.value, {"value": "before"})
                    self.assertEqual(context.read_bytes(path), byte_result.value)
                    self.assertEqual(context.read_text(path), text_result.value)
                    self.assertEqual(context.content_digest(path), hashlib.sha256(raw).hexdigest())
                    self.assertEqual(byte_result.status.state, TargetFileState.FILE)

    def test_typed_results_distinguish_missing_invalid_text_and_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            context = ValidationContext(target)

            missing = context.read_text_result(target / "missing.txt")
            invalid_text_path = target / "invalid.txt"
            invalid_text_path.write_bytes(b"\xff")
            invalid_text = context.read_text_result(invalid_text_path)
            invalid_json_path = target / "invalid.json"
            invalid_json_path.write_text("{", encoding="utf-8")
            invalid_json = context.read_json_result(invalid_json_path)

            self.assertEqual(missing.status.state, TargetFileState.MISSING)
            self.assertIsNone(missing.value)
            self.assertEqual(invalid_text.status.state, TargetFileState.INVALID_TEXT)
            self.assertIsNone(invalid_text.value)
            self.assertEqual(invalid_json.status.state, TargetFileState.INVALID_JSON)
            self.assertIsNone(invalid_json.value)

    def test_finalize_detects_relevant_content_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            path = target / "example.txt"
            path.write_bytes(b"before\n")
            context = ValidationContext(target)

            self.assertEqual(context.read_text(path), "before\n")
            path.write_bytes(b"after\n")
            mutations = context.finalize()

            self.assertEqual(len(mutations), 1)
            self.assertEqual(mutations[0].path, path)
            self.assertTrue(mutations[0].content_changed)

    def test_finalize_accepts_stable_relevant_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            path = target / "example.txt"
            path.write_text("stable\n", encoding="utf-8")
            context = ValidationContext(target)

            context.read_text(path)

            self.assertEqual(context.finalize(), ())

    def test_validator_parses_manifest_once_per_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            manifest = target / ".ai/alatyr.yaml"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("schema_version: 44\n", encoding="utf-8")
            validator = Validator(
                target,
                framework_source=None,
                diff_ref=None,
                approval_records=[],
                enforce_approval_scope=False,
                change_packages=[],
                enforce_change_package=False,
                migration_diff=None,
                allow_placeholders=True,
                allow_local_paths=[],
                config=AdapterValidatorConfig(),
            )

            with patch.object(
                validate_target_adapter,
                "parse_manifest",
                wraps=validate_target_adapter.parse_manifest,
            ) as parser:
                validator.run()

            self.assertEqual(parser.call_count, 1)

    def test_validator_finalizes_relevant_target_input_observations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assert_validator_finalizes_observations(Path(directory))

    def test_validator_finalizes_observations_through_root_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            actual, alias = root / 'actual', root / 'alias'
            actual.mkdir()
            try:
                alias.symlink_to(actual, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Directory symlinks are unavailable on this host')
            self.assert_validator_finalizes_observations(alias)

    def assert_validator_finalizes_observations(self, target):
        manifest = target / ".ai/alatyr.yaml"
        manifest.parent.mkdir(parents=True)
        manifest.write_text("schema_version: 44\n", encoding="utf-8")
        validator = Validator(
            target,
            framework_source=None,
            diff_ref=None,
            approval_records=[],
            enforce_approval_scope=False,
            change_packages=[],
            enforce_change_package=False,
            migration_diff=None,
            allow_placeholders=True,
            allow_local_paths=[],
            config=AdapterValidatorConfig(),
        )

        def mutate_last_observed_input() -> None:
            manifest.write_text("schema_version: 45\n", encoding="utf-8")

        with patch.object(
            validator,
            "check_migration_diff_evidence",
            side_effect=mutate_last_observed_input,
        ):
            validator.run()

        self.assertEqual(len(validator.target_mutations), 1)
        self.assertEqual(validator.target_mutations[0].path, manifest.resolve())
        self.assertTrue(validator.target_mutations[0].content_changed)
        self.assertTrue(
            any(
                finding.code == "TARGET_INPUT_MUTATED"
                and finding.level == "error"
                and finding.path == ".ai/alatyr.yaml"
                for finding in validator.findings
            )
        )
        finding = next(f for f in validator.findings if f.code == "TARGET_INPUT_MUTATED")
        self.assertEqual(finding.to_json()["details"]["content"]["comparison"], "changed")
        self.assertIn("changed metadata:", finding.render())
        self.assertNotIn(str(target), json.dumps(finding.to_json()))
        self.assertNotIn(str(target.resolve()), json.dumps(finding.to_json()))

    def test_combined_local_path_scan_preserves_unix_and_windows_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            document = target / ".ai/project/paths.md"
            document.parent.mkdir(parents=True)
            document.write_text(
                "Unix: /home/example/project/file.txt\n"
                "Windows: C:\\Users\\Example\\project\\file.txt\n",
                encoding="utf-8",
            )
            validator = Validator(
                target,
                framework_source=None,
                diff_ref=None,
                approval_records=[],
                enforce_approval_scope=False,
                change_packages=[],
                enforce_change_package=False,
                migration_diff=None,
                allow_placeholders=False,
                allow_local_paths=[],
                config=AdapterValidatorConfig(),
            )

            validator.check_local_paths()

            self.assertEqual(
                [finding.code for finding in validator.findings],
                ["LOCAL_PATH_LEAKAGE", "LOCAL_PATH_LEAKAGE"],
            )

    def test_structured_local_path_scalars_preserve_semantics(self):
        from target_adapter_validation.local_paths import scan_local_paths
        cases = [
            ('.json', json.dumps({'code': 'if x:\n    pass'}), 0),
            ('.json', json.dumps({'code': 'x:\nvalue', 'path': 'C:\\Users\\Example\\file'}), 1),
            ('.json', r'{"path":"\/home\/example\/file"}', 1),
            ('.json', r'{"path":"\u002fhome\u002fexample\u002ffile"}', 1),
            ('.json', r'{"same":"/home/example/one","same":"C:\\Users\\Example\\two"}', 2),
            ('.json', json.dumps({'/home/example/key': ['ok', '/Users/example/value']}), 2),
            ('.yaml', 'code: "if x:\\n    pass"\n', 0),
            ('.yaml', 'path: "C:\\\\Users\\\\Example\\\\file"\n', 1),
            ('.yml', 'same: /home/example/one\nsame: /Users/example/two\n', 2),
            ('.yaml', '---\npath: /home/example/one\n---\npath: /Users/example/two\n', 2),
            ('.yaml', 'code: |\n  if x:\n      pass\n# /home/example/comment\n', 1),
            ('.md', 'Windows C:\\Users\\Example\\file', 1),
        ]
        for suffix, text, count in cases:
            with self.subTest(suffix=suffix, text=text):
                scan = scan_local_paths(text, suffix, '/not-a-local-root')
                self.assertEqual(scan.failures, [])
                self.assertEqual(len(scan.matches), count, scan)

    def test_structured_path_limits_and_malformed_input_fail_closed(self):
        from target_adapter_validation import local_paths
        for suffix, text in [('.json', '{"path":"C:\\\\Users\\\\Example\\\\file",'),
                             ('.yaml', 'paths: [unterminated'), ('.yaml', 'cycle: &cycle [*cycle]')]:
            with self.subTest(suffix=suffix, text=text):
                self.assertTrue(local_paths.scan_local_paths(text, suffix, '').failures)
        for limit in (9, 10, 11):
            with patch.object(local_paths, 'MAX_SCAN_BYTES', 10):
                scan = local_paths.scan_local_paths('x' * limit, '.md', '')
                self.assertEqual(bool(scan.failures), limit > 10)
        for limit, data, ceiling in [('MAX_SCAN_NODES', '[null,null]', 3),
                                      ('MAX_SCAN_DEPTH', '[[null]]', 2),
                                      ('MAX_SCAN_MATCHES', '["/home/a/b","/home/c/d"]', 2)]:
            for bound in (ceiling - 1, ceiling, ceiling + 1):
                with self.subTest(limit=limit, bound=bound), patch.object(local_paths, limit, bound):
                    scan = local_paths.scan_local_paths(data, '.json', '')
                    self.assertEqual(bool(scan.failures), bound < ceiling)

    def test_structured_scan_adversarial_tokens_and_diagnostic_locations(self):
        from target_adapter_validation import local_paths
        self.assertEqual(list(local_paths._json_fragments(r'\"' * 4000)), [])
        self.assertTrue(local_paths.scan_local_paths(r'\"' * 4000, '.json', '').failures)
        for text in ('path: "prefix\\n/home/example/repo"\n',
                     'path: >\n  prefix\n  /home/example/repo\n'):
            scan = local_paths.scan_local_paths(text, '.yaml', '')
            self.assertEqual(scan.failures, [])
            self.assertIsNone(scan.matches[0].line)
            self.assertEqual(scan.matches[0].scalar_start_line, 1)
        scan = local_paths.scan_local_paths('{"p":"/home/a/b","p":"/home/a/b"}', '.json', '')
        self.assertNotEqual(scan.matches[0].member_path, scan.matches[1].member_path)
        documents = '\n---\n'.join('path: /home/example/file' for _ in range(100))
        scan = local_paths.scan_local_paths(documents, '.yaml', '')
        self.assertEqual(scan.failures, [])
        self.assertEqual(len(scan.matches), 100)
        with patch.object(local_paths, 'MAX_SCAN_NODES', 3), patch.object(local_paths, 'safe_compose_all', side_effect=AssertionError('allocated oversized graph')):
            self.assertTrue(local_paths.scan_local_paths('[0,1,2]', '.yaml', '').failures)
        with patch.object(local_paths, 'safe_compose_all', side_effect=MemoryError('bounded allocation failed')):
            self.assertTrue(local_paths.scan_local_paths('[]', '.yaml', '').failures)
        with patch.object(local_paths, '_json_scalars', side_effect=MemoryError('allocation failed')), patch.object(local_paths, '_scan_scalar', side_effect=AssertionError('retried allocation after exhaustion')):
            self.assertTrue(local_paths.scan_local_paths('[]', '.json', '').failures)
        with patch.object(local_paths, '_scan_scalar', side_effect=MemoryError('fallback allocation failed')):
            self.assertTrue(local_paths.scan_local_paths('{bad', '.json', '').failures)
        # Stop at the node boundary without queuing every sibling/pointer first.
        scan = local_paths.PathScan()
        with patch.object(local_paths, 'MAX_SCAN_NODES', 5), patch.object(local_paths, '_pointer', wraps=local_paths._pointer) as pointer:
            with self.assertRaisesRegex(ValueError, 'node/depth'):
                local_paths._json_scalars(scan, [None] * 10000, '')
            self.assertLessEqual(pointer.call_count, 5)

    def test_public_validator_decodes_json_paths_without_code_false_positive(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            path = target / '.ai/project/paths.json'
            path.parent.mkdir(parents=True)
            command = [sys.executable, '-B', str(ROOT / 'tools/validate_target_adapter.py'),
                       '--target', str(target), '--json']
            for content, expected in [(json.dumps({'code': 'if x:\n    pass'}), False),
                                      (json.dumps({'path': 'C:\\Users\\Example\\file'}), True),
                                      (r'{"path":"/home/\ud800"}', True)]:
                path.write_text(content, encoding='utf-8')
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertNotIn('Traceback', result.stderr)
                report = json.loads(result.stdout)
                findings = report['findings']
                self.assertEqual(any(row['code'] == 'LOCAL_PATH_LEAKAGE' for row in findings), expected)

    def test_cached_content_is_stable_without_reopening_the_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            context = ValidationContext(target)
            path = target / "example.json"
            path.write_text('{"value": "before"}\n', encoding="utf-8")

            first = context.read_text(path)
            path.write_text('{"value": "after"}\n', encoding="utf-8")
            second = context.read_text(path)

            self.assertEqual(first, second)

    def test_missing_path_replaced_by_external_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "target"
            target.mkdir()
            outside = parent / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")
            path = target / "later.txt"
            context = ValidationContext(target)

            self.assertEqual(context.read_text(path), "")
            path.symlink_to(outside)

            with self.assertRaises(TargetPathEscapeError):
                context.read_text(path)

    def test_rejects_parent_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "target"
            target.mkdir()
            outside = parent / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")

            with self.assertRaises(TargetPathEscapeError):
                ValidationContext(target).read_text(target / ".." / "outside.txt")

            data, error = ValidationContext(target).read_json(
                target / ".." / "outside.txt"
            )
            self.assertIsNone(data)
            self.assertIn("resolves outside", error or "")

    def test_rejects_symlink_that_resolves_outside_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "target"
            target.mkdir()
            outside = parent / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")
            link = target / "linked.txt"
            try:
                link.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            with self.assertRaises(TargetPathEscapeError):
                ValidationContext(target).read_text(link)

    def test_allows_symlink_that_stays_inside_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            source = target / "source.txt"
            source.write_bytes(b"inside\n")
            link = target / "linked.txt"
            try:
                link.symlink_to(source)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            self.assertEqual(ValidationContext(target).read_text(link), "inside\n")

    def test_cached_internal_symlink_cannot_be_retargeted_outside(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "target"
            target.mkdir()
            inside = target / "inside.txt"
            inside.write_bytes(b"inside\n")
            outside = parent / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")
            link = target / "linked.txt"
            try:
                link.symlink_to(inside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            context = ValidationContext(target)

            self.assertEqual(context.read_text(link), "inside\n")
            link.unlink()
            link.symlink_to(outside)

            with self.assertRaises(TargetPathEscapeError):
                context.read_text(link)

    def test_validator_records_target_path_escape_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "target"
            target.mkdir()
            outside = parent / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")
            link = target / "linked.txt"
            try:
                link.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            validator = Validator(
                target,
                framework_source=None,
                diff_ref=None,
                approval_records=[],
                enforce_approval_scope=False,
                change_packages=[],
                enforce_change_package=False,
                migration_diff=None,
                allow_placeholders=False,
                allow_local_paths=[],
                config=AdapterValidatorConfig(),
            )

            first = validator.target_path("linked.txt")
            second = validator.target_path("linked.txt")

            self.assertFalse(first.exists())
            self.assertEqual(first, second)
            self.assertEqual(
                [item.code for item in validator.findings], ["TARGET_PATH_ESCAPE"]
            )

    def test_selected_records_must_stay_inside_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "target"
            target.mkdir()
            outside = parent / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")

            validator = Validator(
                target,
                framework_source=None,
                diff_ref=None,
                approval_records=[outside],
                enforce_approval_scope=False,
                change_packages=[Path("../outside.json")],
                enforce_change_package=False,
                migration_diff=None,
                allow_placeholders=False,
                allow_local_paths=[],
                config=AdapterValidatorConfig(),
            )

            self.assertEqual(validator.approval_records, [])
            self.assertEqual(validator.change_packages, [])
            self.assertEqual(
                [item.code for item in validator.findings],
                ["TARGET_PATH_ESCAPE", "TARGET_PATH_ESCAPE"],
            )

    def test_capability_module_cannot_follow_external_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "target"
            map_path = target / ".ai/project/consistency-map.json"
            map_path.parent.mkdir(parents=True)
            outside = parent / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            try:
                map_path.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            validator = Validator(
                target,
                framework_source=None,
                diff_ref=None,
                approval_records=[],
                enforce_approval_scope=False,
                change_packages=[],
                enforce_change_package=False,
                migration_diff=None,
                allow_placeholders=False,
                allow_local_paths=[],
                config=AdapterValidatorConfig(),
            )

            validator.check_consistency_map()

            self.assertEqual(
                [item.code for item in validator.findings], ["TARGET_PATH_ESCAPE"]
            )

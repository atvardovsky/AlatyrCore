from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from audit_external_case_identity import load_registry, scan_history, scan_worktree
import audit_external_case_identity as audit


class ExternalCaseIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'source'
        self.repo.mkdir()
        self.mapping = self.base / 'private-map.json'
        self.name = 'ConfidentialFixtureIdentity'
        self.data = {
            'schema_version': 1, 'registry_kind': 'alatyr-private-project-pseudonyms',
            'source_project': 'AlatyrCore',
            'cases': [{'case_id': 'CASE-001', 'identities': [self.name]}],
        }
        self.save()
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        (self.repo / '.gitignore').write_text('.ai/\ntmp/\n', encoding='utf-8')
        (self.repo / 'README.md').write_text('AlatyrCore\n', encoding='utf-8')
        self.git('add', '.')
        self.git('commit', '-qm', 'Initialize source fixture')

    def save(self) -> None:
        self.mapping.write_text(json.dumps(self.data), encoding='utf-8')

    def git(self, *args: str) -> str:
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, '-B', str(ROOT / 'tools/audit_external_case_identity.py'),
                               '--repo', str(self.repo), '--private-map', str(self.mapping), *args],
                              capture_output=True, text=True)

    def test_clean_current_tree_and_history(self) -> None:
        before = self.git('rev-parse', 'HEAD')
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['worktree']['findings'], [])
        self.assertEqual(report['history']['findings'], [])
        self.assertEqual(before, self.git('rev-parse', 'HEAD'))
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_hidden_ignored_report_is_checked_and_output_is_pseudonymized(self) -> None:
        directory = self.repo / '.ai' / 'reports'
        directory.mkdir(parents=True)
        (directory / (self.name + '.json')).write_text(self.name.lower(), encoding='utf-8')
        result = self.cli()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(self.name.casefold(), result.stdout.casefold())
        findings = json.loads(result.stdout)['worktree']['findings']
        self.assertEqual(findings[0]['location'], '.ai/reports/CASE-001.json')
        self.assertEqual(findings[0]['case_ids'], ['CASE-001'])

    def test_empty_named_directory_is_not_missed(self) -> None:
        (self.repo / self.name).mkdir()
        self.assertEqual(self.cli('--worktree-only').returncode, 1)

    def test_historical_blobs_names_messages_tags_and_refs_are_checked(self) -> None:
        path = self.repo / (self.name + '.md')
        path.write_text(self.name, encoding='utf-8')
        self.git('add', '.')
        self.git('commit', '-qm', 'Evidence for ' + self.name)
        self.git('tag', '-a', self.name, '-m', 'Historical ' + self.name)
        self.git('rm', path.name)
        self.git('commit', '-qm', 'Remove fixture')
        registry = load_registry(self.mapping, self.repo)
        self.assertEqual(scan_worktree(self.repo, registry)['findings'], [])
        report = scan_history(self.repo, registry)
        self.assertEqual({row['type'] for row in report['findings']}, {'commit', 'tree', 'blob', 'tag', 'ref'})
        result = self.cli('--history-only')
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(self.name.casefold(), result.stdout.casefold())

    def test_registry_must_be_outside_repository_even_when_ignored(self) -> None:
        inside = self.repo / 'tmp' / 'private-map.json'
        inside.parent.mkdir()
        inside.write_text(self.mapping.read_text(), encoding='utf-8')
        with self.assertRaises(ValueError):
            load_registry(inside, self.repo)

    def test_malformed_registry_fields_fail_without_crashing_cli(self) -> None:
        mutations = [
            lambda d: d.update(schema_version=True),
            lambda d: d.update(registry_kind={}),
            lambda d: d.update(cases={}),
            lambda d: d.update(source_project=[]),
            lambda d: d['cases'][0].update(case_id={}),
            lambda d: d['cases'][0].update(identities='not-a-list'),
            lambda d: d['cases'][0].update(identities=[{}]),
            lambda d: d['cases'][0].update(identities=['AlatyrCore']),
            lambda d: d['cases'][0].update(identities=['CASE-001']),
            lambda d: d['cases'].append(copy.deepcopy(d['cases'][0])),
            lambda d: d['cases'][0]['identities'].append(self.name.lower()),
            lambda d: d['cases'].append({'case_id': 'CASE-002', 'identities': ['CASE-002']}),
        ]
        initial = copy.deepcopy(self.data)
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.data = copy.deepcopy(initial)
                mutate(self.data)
                self.save()
                result = self.cli()
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)['status'], 'incomplete')
                self.assertNotIn('Traceback', result.stderr)

    def test_duplicate_json_fields_are_rejected(self) -> None:
        self.mapping.write_text('{"schema_version":1,"schema_version":1}', encoding='utf-8')
        self.assertEqual(self.cli().returncode, 2)

    def test_relative_external_registry_path_is_supported(self) -> None:
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/audit_external_case_identity.py'),
                                 '--repo', str(self.repo), '--private-map', '../private-map.json'],
                                cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_worktree_git_link_metadata_is_not_loaded_as_support(self) -> None:
        linked = self.base / self.name
        self.git('worktree', 'add', '-q', str(linked), '-b', self.name)
        registry = load_registry(self.mapping, linked)
        self.assertEqual(scan_worktree(linked, registry)['findings'], [])
        self.assertEqual(scan_history(linked, registry)['findings'][0]['type'], 'ref')

    def test_unicode_case_folding(self) -> None:
        self.data['cases'][0]['identities'] = ['Stra\u00dfeFixture']
        self.save()
        registry = load_registry(self.mapping, self.repo)
        self.assertEqual(registry.matches('STRASSEFIXTURE'), ['CASE-001'])
        self.assertEqual(registry.location('STRASSEFIXTURE/report.md'), 'CASE-001/report.md')

    def test_input_limit_does_not_produce_a_clean_result(self) -> None:
        registry = load_registry(self.mapping, self.repo)
        file = self.repo / 'bounded.txt'
        for size in (63, 64, 65):
            with self.subTest(size=size), patch('audit_external_case_identity.MAX_BYTES', 64):
                file.write_text('x' * size, encoding='utf-8')
                if size > 64:
                    with self.assertRaises(ValueError):
                        scan_worktree(self.repo, registry)
                else:
                    self.assertEqual(scan_worktree(self.repo, registry)['findings'], [])

    def test_unsafe_shallow_history_is_not_reported_clean(self) -> None:
        shallow = self.base / 'shallow'
        subprocess.run(['git', 'clone', '-q', '--depth', '1', self.repo.as_uri(), str(shallow)], check=True)
        registry = load_registry(self.mapping, shallow)
        with self.assertRaises(ValueError):
            scan_history(shallow, registry)

    def test_bare_mirror_is_supported(self) -> None:
        mirror = self.base / 'mirror.git'
        subprocess.run(['git', 'clone', '-q', '--mirror', str(self.repo), str(mirror)], check=True)
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/audit_external_case_identity.py'),
                                 '--repo', str(mirror), '--private-map', str(self.mapping), '--history-only'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_ref_advancement_during_inspection_is_incomplete(self) -> None:
        registry = load_registry(self.mapping, self.repo)
        original_git = audit.git
        advanced = False

        def advancing_git(repo, *args):
            nonlocal advanced
            result = original_git(repo, *args)
            if args[0] == 'rev-list' and not advanced:
                self.git('commit', '--allow-empty', '-qm', 'Advance during inspection')
                advanced = True
            return result

        with patch.object(audit, 'git', side_effect=advancing_git):
            with self.assertRaisesRegex(ValueError, 'refs changed'):
                scan_history(self.repo, registry)


if __name__ == '__main__':
    unittest.main()

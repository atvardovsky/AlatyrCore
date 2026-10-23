#!/usr/bin/env python3
"""Read-only private-map identity audit; never rewrite history or publish changes."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 32 * 1024 * 1024
EXCLUDED = {'.git', '__pycache__', '.venv', 'venv', 'node_modules', 'site-packages', 'vendor'}


@dataclass(frozen=True)
class Registry:
    identities: tuple[tuple[str, str], ...]

    def matches(self, text: str) -> list[str]:
        folded = text.casefold()
        return sorted({case for name, case in self.identities if name in folded})

    def location(self, text: str) -> str:
        folded = text.casefold()
        for name, case in sorted(self.identities, key=lambda row: len(row[0]), reverse=True):
            folded = folded.replace(name, case)
        return folded


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate registry field')
        result[key] = value
    return result


def load_registry(path: Path, repo: Path) -> Registry:
    if Path(os.path.abspath(path)).is_relative_to(repo) or path.resolve().is_relative_to(repo):
        raise ValueError('private registry must be outside the audited repository')
    if path.stat().st_size > 128 * 1024:
        raise ValueError('private registry exceeds 128 KiB')
    data = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object)
    fields = {'schema_version', 'registry_kind', 'source_project', 'cases'}
    if not isinstance(data, dict) or set(data) != fields:
        raise ValueError('invalid private registry fields')
    if type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise ValueError('unsupported private registry schema')
    if data['registry_kind'] != 'alatyr-private-project-pseudonyms':
        raise ValueError('invalid private registry kind')
    source = data['source_project']
    if not isinstance(source, str) or not source.strip() or source != source.strip():
        raise ValueError('invalid source project identity')
    cases = data['cases']
    if not isinstance(cases, list) or not 1 <= len(cases) <= 256:
        raise ValueError('registry must contain 1..256 cases')
    seen_cases, names, rows = set(), set(), []
    for case in cases:
        if not isinstance(case, dict) or set(case) != {'case_id', 'identities'}:
            raise ValueError('invalid case fields')
        case_id = case['case_id']
        if not isinstance(case_id, str) or not re.fullmatch(r'CASE-[0-9]{3,6}', case_id):
            raise ValueError('invalid case ID')
        if case_id in seen_cases:
            raise ValueError('duplicate case ID')
        seen_cases.add(case_id)
        identities = case['identities']
        if not isinstance(identities, list) or not 1 <= len(identities) <= 64:
            raise ValueError('case must contain 1..64 identities')
        for name in identities:
            if not isinstance(name, str) or not 4 <= len(name) <= 512 or name != name.strip():
                raise ValueError('invalid original identity')
            folded = name.casefold()
            if folded in names or folded in source.casefold():
                raise ValueError('duplicate or source-project identity')
            names.add(folded)
            rows.append((folded, case_id))
    if any(name in case.casefold() or case.casefold() in name for name, _ in rows for case in seen_cases):
        raise ValueError('original identity collides with a public case ID')
    return Registry(tuple(rows))


def git(repo: Path, *args: str) -> bytes:
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    result = subprocess.run(['git', '-C', str(repo), *args], env=env, capture_output=True)
    if result.returncode:
        raise ValueError('Git inspection failed; history audit is incomplete')
    return result.stdout


def scan_worktree(repo: Path, registry: Registry) -> dict:
    findings, count = [], 0

    def onerror(_error: OSError) -> None:
        raise ValueError('directory inspection failed; worktree audit is incomplete')

    for directory, dirs, files in os.walk(repo, followlinks=False, onerror=onerror):
        dirs[:] = sorted(name for name in dirs if name not in EXCLUDED)
        for name in [*dirs, *sorted(name for name in files if name != '.git')]:
            path = Path(directory) / name
            relative = path.relative_to(repo).as_posix()
            content = ''
            if path.is_symlink():
                content = os.readlink(path)
            elif path.is_file():
                if path.stat().st_size > MAX_BYTES:
                    raise ValueError('file exceeds scan limit; worktree audit is incomplete')
                content = path.read_bytes().decode('utf-8', errors='replace')
                count += 1
            matches = registry.matches(relative + '\n' + content)
            if matches:
                findings.append({'location': registry.location(relative), 'case_ids': matches})
    return {'files': count, 'findings': findings, 'excluded_directory_names': sorted(EXCLUDED),
            'symlink_policy': 'inspect link name and destination, never traverse'}


def scan_history(repo: Path, registry: Registry) -> dict:
    if git(repo, 'rev-parse', '--is-shallow-repository').strip() != b'false':
        raise ValueError('shallow history cannot establish a complete local-ref audit')
    ref_snapshot = git(repo, 'for-each-ref', '--format=%(refname) %(objectname)')
    refs = [line.split(' ', 1)[0] for line in ref_snapshot.decode('utf-8').splitlines()]
    findings = [{'type': 'ref', 'location': registry.location(ref), 'case_ids': registry.matches(ref)}
                for ref in refs if registry.matches(ref)]
    objects = git(repo, 'rev-list', '--objects', '--all', '--no-object-names').splitlines()
    counts = Counter()
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    process = subprocess.Popen(['git', '-C', str(repo), 'cat-file', '--batch'],
                               env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL)
    try:
        for oid in objects:
            process.stdin.write(oid + b'\n')
            process.stdin.flush()
            header = process.stdout.readline().split()
            if len(header) != 3 or header[0] != oid:
                raise ValueError('invalid Git object response; history audit is incomplete')
            size = int(header[2])
            if not 0 <= size <= MAX_BYTES:
                raise ValueError('Git object exceeds scan limit; history audit is incomplete')
            data = process.stdout.read(size)
            if len(data) != size or process.stdout.read(1) != b'\n':
                raise ValueError('incomplete Git object; history audit is incomplete')
            kind = header[1].decode('ascii')
            counts[kind] += 1
            matches = registry.matches(data.decode('utf-8', errors='replace'))
            if matches:
                findings.append({'type': kind, 'object_id': oid.decode('ascii'), 'case_ids': matches})
        process.stdin.close()
        if process.wait():
            raise ValueError('Git object inspection failed; history audit is incomplete')
    finally:
        if not process.stdin.closed:
            process.stdin.close()
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
        process.wait()
    if ref_snapshot != git(repo, 'for-each-ref', '--format=%(refname) %(objectname)'):
        raise ValueError('Git refs changed during inspection; history audit is incomplete')
    return {'refs': len(refs), 'objects': dict(counts), 'findings': findings,
            'scope': 'reachable objects and names of all locally available refs'}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--private-map', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--history-only', action='store_true')
    mode.add_argument('--worktree-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        repo = args.repo.resolve(strict=True)
        if not repo.is_dir():
            raise ValueError('repository must be a directory')
        registry = load_registry(args.private_map, repo)
        report = {'report_kind': 'alatyr-external-case-identity-audit', 'schema_version': 1}
        if not args.history_only:
            report['worktree'] = scan_worktree(repo, registry)
        if not args.worktree_only:
            report['history'] = scan_history(repo, registry)
        report['authority'] = 'observational; no lock, acceptance or publication grant'
        found = any(section.get('findings') for section in report.values() if isinstance(section, dict))
        print(json.dumps(report, indent=2, ensure_ascii=True))
        return 1 if found else 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        detail = str(error) if type(error) is ValueError else 'Check registry encoding, file access and Git availability'
        print(json.dumps({'status': 'incomplete', 'error_type': type(error).__name__, 'error': detail}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

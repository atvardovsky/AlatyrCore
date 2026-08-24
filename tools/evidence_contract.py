"""Deterministic source contract binding for captured assistant evidence."""

from __future__ import annotations

import hashlib
import io
import os
import subprocess
import tarfile
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

CONTRACT_PREFIXES = (
    "framework/",
    "installer/",
    "templates/target/",
    "schemas/",
    "conformance/fixtures/",
)
CONTRACT_FILES = {
    "AGENTS.md",
    "AI_ASSISTANTS.md",
    "INSTALL.md",
    "VERSION",
    "ADAPTER_SCHEMA_VERSION",
    "TEMPLATE_VERSION",
    "conformance/runs/assistant-surfaces.json",
    "conformance/runs/assistant-run-report-template.json",
    "conformance/benchmarks/benchmark-task-suite.json",
    "conformance/benchmarks/effectiveness-run-report-template.json",
    "tools/check_captured_effectiveness_results.py",
    "tools/check_conformance_matrix.py",
    "tools/check_conformance_reports.py",
    "tools/check_effectiveness_benchmark.py",
    "tools/evidence_contract.py",
    "tools/materialize_conformance_fixtures.py",
    "tools/prepare_conformance_run.py",
    "tools/prepare_conformance_matrix.py",
    "tools/prepare_effectiveness_benchmark.py",
    "tools/render_evidence_status.py",
    "tools/run_codex_conformance.py",
    "tools/run_codex_effectiveness_benchmark.py",
    "tools/scaffold_target.py",
    "tools/scaffold_target_structure.py",
    "tools/summarize_conformance_reports.py",
    "tools/summarize_effectiveness_benchmark.py",
    "tools/summarize_effectiveness_reports.py",
}
HEX = set("0123456789abcdef")


def is_contract_path(relpath: str) -> bool:
    return relpath in CONTRACT_FILES or relpath.startswith(CONTRACT_PREFIXES)


def valid_source_commit(value: str) -> bool:
    return len(value) in {40, 64} and set(value.lower()) <= HEX


def digest_entries(entries: Iterable[tuple[str, str, bytes]]) -> str:
    digest = hashlib.sha256(b"alatyr-evidence-contract-v1\0")
    for relpath, kind, content in sorted(entries):
        for value in [relpath.encode("utf-8"), kind.encode("ascii"), content]:
            digest.update(str(len(value)).encode("ascii"))
            digest.update(b":")
            digest.update(value)
            digest.update(b"\0")
    return digest.hexdigest()


def current_contract_digest(root: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", "ls-files", "-c", "-o", "--exclude-standard", "-z"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(message or "cannot enumerate evidence contract paths")

    entries: list[tuple[str, str, bytes]] = []
    for relpath in result.stdout.decode("utf-8", errors="surrogateescape").split("\0"):
        if not relpath or not is_contract_path(relpath):
            continue
        path = root / relpath
        try:
            if path.is_symlink():
                content = os.readlink(path).encode("utf-8", errors="surrogateescape")
                entries.append((relpath, "symlink", content))
            elif path.is_file():
                entries.append((relpath, "file", path.read_bytes()))
        except FileNotFoundError:
            continue
    return digest_entries(entries)


def contract_digest_at(commit: str, root: Path = ROOT) -> str | None:
    if not valid_source_commit(commit):
        return None
    result = subprocess.run(
        ["git", "archive", "--format=tar", commit],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None

    entries: list[tuple[str, str, bytes]] = []
    try:
        with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
            for member in archive.getmembers():
                relpath = member.name.rstrip("/")
                if not is_contract_path(relpath):
                    continue
                if member.issym():
                    entries.append((relpath, "symlink", member.linkname.encode("utf-8")))
                elif member.isfile():
                    extracted = archive.extractfile(member)
                    if extracted is not None:
                        entries.append((relpath, "file", extracted.read()))
    except tarfile.TarError:
        return None
    return digest_entries(entries)

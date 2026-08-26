"""Deterministic source contract binding for captured assistant evidence."""

from __future__ import annotations

import hashlib
import os
import subprocess
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
    "conformance/executors/executor-capabilities.json",
    "conformance/assistant-surface-integration-audits.json",
    "conformance/golden/shared-expectations.json",
    "conformance/operations/request-routing-protocol-expectations.json",
    "tools/bootstrap_index.py",
    "tools/capability_catalog.py",
    "tools/check_captured_effectiveness_results.py",
    "tools/check_assistant_capability_contract.py",
    "tools/check_assistant_surface_audits.py",
    "tools/check_conformance_matrix.py",
    "tools/check_conformance_reports.py",
    "tools/check_effectiveness_benchmark.py",
    "tools/conformance_execution/__init__.py",
    "tools/conformance_execution/codex.py",
    "tools/conformance_execution/codex_benchmark.py",
    "tools/conformance_execution/contract.py",
    "tools/context_receipt.py",
    "tools/evidence_contract.py",
    "tools/framework_packaging.py",
    "tools/materialize_conformance_fixtures.py",
    "tools/prepare_conformance_run.py",
    "tools/prepare_conformance_matrix.py",
    "tools/prepare_effectiveness_benchmark.py",
    "tools/render_evidence_status.py",
    "tools/run_codex_conformance.py",
    "tools/run_codex_effectiveness_benchmark.py",
    "tools/scaffold_profiles.json",
    "tools/scaffold_projection.py",
    "tools/scaffold_state.py",
    "tools/scaffold_target_structure.py",
    "tools/summarize_conformance_reports.py",
    "tools/summarize_effectiveness_benchmark.py",
    "tools/summarize_effectiveness_reports.py",
    "tools/target_adapter_validation/framework_baseline.py",
    "tools/render_rule_registry_docs.py",
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
        ["git", "ls-tree", "-rz", "--full-tree", commit],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None

    selected: list[tuple[str, str, bytes]] = []
    for raw_entry in result.stdout.split(b"\0"):
        if not raw_entry:
            continue
        try:
            metadata, raw_path = raw_entry.split(b"\t", 1)
            mode, object_type, object_id = metadata.split(b" ", 2)
        except ValueError:
            return None
        relpath = raw_path.decode("utf-8", errors="surrogateescape")
        if object_type != b"blob" or not is_contract_path(relpath):
            continue
        selected.append(
            (relpath, "symlink" if mode == b"120000" else "file", object_id)
        )

    object_ids = sorted({object_id for _, _, object_id in selected})
    blobs_result = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=root,
        input=b"".join(object_id + b"\n" for object_id in object_ids),
        check=False,
        capture_output=True,
    )
    if blobs_result.returncode != 0:
        return None

    blobs: dict[bytes, bytes] = {}
    offset = 0
    for requested_id in object_ids:
        header_end = blobs_result.stdout.find(b"\n", offset)
        if header_end < 0:
            return None
        header = blobs_result.stdout[offset:header_end].split()
        if len(header) != 3 or header[1] != b"blob":
            return None
        try:
            size = int(header[2])
        except ValueError:
            return None
        content_start = header_end + 1
        content_end = content_start + size
        if content_end >= len(blobs_result.stdout):
            return None
        blobs[requested_id] = blobs_result.stdout[content_start:content_end]
        if blobs_result.stdout[content_end:content_end + 1] != b"\n":
            return None
        offset = content_end + 1

    entries = [
        (relpath, kind, blobs[object_id])
        for relpath, kind, object_id in selected
        if object_id in blobs
    ]
    if len(entries) != len(selected):
        return None
    return digest_entries(entries)

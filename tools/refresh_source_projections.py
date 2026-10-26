#!/usr/bin/env python3
"""Plan source projection refresh in isolation; apply only with --write."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from projection_graph import ProjectionInput, ProjectionNode, ProjectionOutput, validate_projection_graph
from source_state import source_snapshot, SourceEntry
from target_validation_support import is_target_relative_path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Stage:
    name: str
    dependencies: tuple[str, ...]
    outputs: tuple[str, ...]
    command: tuple[str, ...]
    check: tuple[str, ...]
    preserve_current: bool = False
    check_first: bool = False


@dataclass(frozen=True)
class RefreshSnapshot:
    entries: dict[str, SourceEntry]
    revision: str


def revision(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


STAGES = (
    Stage("rules", (), ("framework/rule-registry.md", "framework/rule-ownership.md"), ("render_rule_registry_docs.py",), ("render_rule_registry_docs.py", "--check"), check_first=True),
    Stage("semantics", (), ("framework/semantics/index.json", "tools/source_context_router.json", "templates/target/.ai/assistant/context-router.json"), ("render_semantic_codebook.py",), ("render_semantic_codebook.py", "--check"), check_first=True),
    Stage("source-context", ("semantics",), ("tools/source-context/index.json", "tools/source-context/profiles/*.json"), ("source_context_selection.py", "--write"), ("source_context_selection.py", "--check"), check_first=True),
    Stage("findings", (), ("tools/target_adapter_validation/finding-codes.json", "docs/target-adapter-validator-findings.md"), ("render_target_validator_findings.py",), ("render_target_validator_findings.py", "--check"), check_first=True),
    Stage("compatibility", (), ("docs/target-adapter-contract-compatibility.md",), ("render_target_contract_compatibility.py",), ("render_target_contract_compatibility.py", "--check"), check_first=True),
    Stage("assistants", (), ("templates/target/.ai/assistant/assistant-capabilities.json",), ("render_assistant_capability_index.py", "--write"), ("render_assistant_capability_index.py",), check_first=True),
    Stage("operations", (), ("templates/target/.ai/assistant/operation-index.json",), ("render_operation_index.py", "--write"), ("render_operation_index.py",), check_first=True),
    Stage("consistency", (), ("templates/target/.ai/assistant/consistency-reverse-index.json",), ("render_consistency_reverse_index.py", "--target", "templates/target", "--write"), ("render_consistency_reverse_index.py", "--target", "templates/target"), check_first=True),
    Stage("entry", ("semantics", "operations", "assistants"), ("templates/target/.ai/assistant/entry-packet.json",), ("render_target_entry_packet.py", "--target", "templates/target", "--write"), ("render_target_entry_packet.py", "--target", "templates/target", "--check")),
    Stage("catalogs", ("rules", "entry", "findings", "compatibility", "consistency"), ("framework/context-index.json", "framework/catalog/*/context-index.json", "templates/target/.ai/*/context-index.json", "templates/target/.ai/*/*/context-index.json", "templates/target/.ai/*/*/*/context-index.json"), ("render_context_catalogs.py",), ("render_context_catalogs.py", "--check"), check_first=True),
    Stage("inventory", ("catalogs",), ("framework/file-inventory.json",), ("render_framework_file_inventory.py",), ("render_framework_file_inventory.py", "--check"), check_first=True),
    Stage("bootstrap", ("catalogs", "inventory"), ("templates/target/.ai/assistant/bootstrap-index.json", "templates/target/.ai/assistant/bootstrap-integrity.json"), ("render_target_bootstrap_index.py", "--target", "templates/target", "--write"), ("render_target_bootstrap_index.py", "--target", "templates/target", "--check")),
    Stage("support", ("bootstrap",), ("templates/target/.ai/support-state.json",), ("snapshot_target_support.py", "--target", "templates/target", "--write"), ("snapshot_target_support.py", "--target", "templates/target"), preserve_current=True),
    Stage("evidence", ("support",), ("conformance/evidence-status.json",), ("render_evidence_status.py",), ("render_evidence_status.py", "--check"), check_first=True),
)


def ordered_stages(stages: tuple[Stage, ...]) -> list[Stage]:
    # The conservative input closure includes membership and every source byte.
    # Narrow it only after a renderer-specific dependency contract is proved.
    nodes = [ProjectionNode(s.name, "tools/" + s.command[0], "source-projection", s.dependencies,
             (ProjectionInput("source-snapshot", "tracked-and-nonignored-files"),),
             tuple(ProjectionOutput(p, "source-generated", "replace-generated", "deterministic", False) for p in s.outputs),
             s.name, (s.name,)) for s in stages]
    order = validate_projection_graph(nodes)
    by_id = {s.name: s for s in stages}
    return [by_id[key] for key in order]


def _files(root: Path) -> dict[str, bytes]:
    result = {}
    for path in root.rglob("*"):
        if "__pycache__" in path.parts:
            continue
        if path.is_symlink():
            raise ValueError("source refresh refuses symbolic links")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def _run(root: Path, command: tuple[str, ...], env: dict[str, str], *, require_success: bool = True,
         diagnostics: list[str] | None = None) -> bool:
    result = subprocess.run([sys.executable, str(root / "tools" / command[0]), *command[1:]],
                            cwd=root, env=env, capture_output=True, text=True, timeout=120)
    if result.returncode and diagnostics is not None:
        diagnostics.append(result.stderr or result.stdout)
    if result.returncode and require_success:
        raise ValueError(f"projection {command[0]} failed: {result.stderr or result.stdout}")
    return result.returncode == 0


def verify_outputs(changes, stages: tuple[Stage, ...]) -> None:
    for path in changes:
        if not isinstance(path, str) or not is_target_relative_path(path):
            raise ValueError("source projection output must be a contained portable path")
        owners = [stage.name for stage in stages if any(fnmatch.fnmatchcase(path, p) for p in stage.outputs)]
        if len(owners) != 1:
            raise ValueError(f"source projection output lacks a unique declared owner: {path}")


def normalize_outputs(root: Path, stage: Stage) -> bool:
    changed = False
    for pattern in stage.outputs:
        for path in root.glob(pattern):
            if path.is_symlink():
                raise ValueError("source renderer output must not be a symlink")
            if path.is_file() and path.suffix in {".md", ".json"}:
                content = path.read_bytes()
                if b"\r\n" in content:
                    path.write_bytes(content.replace(b"\r\n", b"\n"))
                    changed = True
    return changed


def prepare(root: Path = ROOT, stages: tuple[Stage, ...] = STAGES, *, reuse_checks: bool = True):
    root = root.resolve()
    worktree = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=root, text=True).strip()).resolve()
    if worktree != root:
        raise ValueError("source refresh requires its repository root, not a nested vendor copy")
    before = RefreshSnapshot(source_snapshot(root), revision(root))
    ordered = ordered_stages(stages)
    git_dir = subprocess.check_output(["git", "rev-parse", "--absolute-git-dir"], cwd=root, text=True).strip()
    with tempfile.TemporaryDirectory(prefix="alatyr-source-projections-") as directory:
        mirror = Path(directory) / "source"
        mirror.mkdir()
        for path, entry in before.entries.items():
            if entry.kind != "file":
                raise ValueError(f"source refresh needs regular source files: {path}")
            destination = mirror / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / path, destination)
            destination.chmod(entry.mode)
        initial = _files(mirror)
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update(GIT_DIR=git_dir, GIT_WORK_TREE=str(mirror), PYTHONDONTWRITEBYTECODE="1")
        index_path = Path(subprocess.check_output(["git", "rev-parse", "--git-path", "index"], cwd=root, text=True).strip())
        if not index_path.is_absolute():
            index_path = root / index_path
        isolated_index = Path(directory) / "index"
        if index_path.is_file():
            shutil.copyfile(index_path, isolated_index)
        env["GIT_INDEX_FILE"] = str(isolated_index)
        current = initial
        passed_checks: set[tuple] = set()

        def git_refs() -> bytes:
            return subprocess.check_output(["git", "for-each-ref", "--format=%(refname) %(objectname)"], cwd=root, env=env)

        initial_refs = git_refs()

        def file_modes(files: dict[str, bytes]) -> tuple[tuple[str, int], ...]:
            return tuple((name, stat.S_IMODE((mirror / name).lstat().st_mode)) for name in sorted(files))

        def fingerprint(files: dict[str, bytes]) -> str:
            digest = hashlib.sha256()
            for name, content in sorted(files.items()):
                digest.update(json.dumps([name, len(content)]).encode("utf-8"))
                digest.update(content)
            return digest.hexdigest()

        current_fingerprint = fingerprint(current)

        def checked(stage: Stage, *, required: bool = False) -> bool:
            modes_before = file_modes(current)
            refs_before = git_refs()
            index_before = isolated_index.read_bytes() if isolated_index.exists() else None
            index_digest = hashlib.sha256(index_before).hexdigest() if index_before is not None else None
            key = (stage.check, current_fingerprint, index_digest, modes_before, refs_before)
            if reuse_checks and key in passed_checks:
                return True
            diagnostics: list[str] = []
            success = _run(mirror, stage.check, env, require_success=False, diagnostics=diagnostics)
            if _files(mirror) != current or (
                isolated_index.read_bytes() if isolated_index.exists() else None
            ) != index_before or file_modes(current) != modes_before or git_refs() != refs_before:
                raise ValueError(f"projection checker {stage.check[0]} modified its input snapshot")
            if success:
                passed_checks.add(key)
            elif required:
                raise ValueError(f"projection {stage.check[0]} failed: {''.join(diagnostics)}")
            return success

        repairing = False
        for _ in range(4):
            previous = current
            for stage in ordered:
                # Keep historical generation metadata when the canonical check passes.
                # Once outputs change, retain the canonical full repair path.
                # Only support's historical-metadata comparison remains eager.
                try_current = stage.preserve_current or (stage.check_first and not repairing)
                generated = not try_current or not checked(stage)
                modes_before = dict(file_modes(current)) if generated else {}
                if generated:
                    _run(mirror, stage.command, env)
                normalized = normalize_outputs(mirror, stage)
                if generated or normalized:
                    next_files = _files(mirror)
                    if generated and any((mirror / name).exists() and
                                         stat.S_IMODE((mirror / name).lstat().st_mode) != mode
                                         for name, mode in modes_before.items()):
                        raise ValueError("projection renderer changed source file permissions")
                    if next_files != current:
                        repairing = True
                        current = next_files
                        current_fingerprint = fingerprint(current)
            if current == previous:
                break
        else:
            raise ValueError("source projection closure did not stabilize; no source files were changed")
        for stage in ordered:
            checked(stage, required=True)
        if _files(mirror) != current or any(
            name in current and stat.S_IMODE((mirror / name).lstat().st_mode) != entry.mode
            for name, entry in before.entries.items()
        ):
            raise ValueError("projection snapshot changed after validation")
        if git_refs() != initial_refs:
            raise ValueError("repository refs changed while planning; rerun the refresh")
        changes = {path: current.get(path) for path in sorted(set(initial) | set(current))
                   if initial.get(path) != current.get(path)}
        verify_outputs(changes, stages)
    if source_snapshot(root) != before.entries or revision(root) != before.revision:
        raise ValueError("source changed while planning; rerun the refresh")
    return before, changes


def apply(root: Path, before, changes: dict[str, bytes | None], stages: tuple[Stage, ...] = STAGES) -> None:
    verify_outputs(changes, stages)
    if source_snapshot(root) != before.entries or revision(root) != before.revision:
        raise ValueError("source changed since refresh plan; no changes applied")
    for name, content in changes.items():
        path = root / name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root):
            raise ValueError("source projection output crosses a symlink")
        if content is None:
            path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        try:
            temporary.chmod(before.entries[name].mode if name in before.entries else 0o644)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    if any((root / p).read_bytes() != value if value is not None else (root / p).exists() for p, value in changes.items()):
        raise ValueError("source refresh was interrupted or modified; verify the partial result")
    after = source_snapshot(root)
    if revision(root) != before.revision or {
        p: entry for p, entry in after.items() if p not in changes
    } != {p: entry for p, entry in before.entries.items() if p not in changes}:
        raise ValueError("source inputs changed during refresh; verify the partial result and rerun")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        before, changes = prepare()
        if args.write:
            apply(ROOT, before, changes)
        print(json.dumps({"write": args.write, "changed_paths": list(changes),
                          "scope": "AlatyrCore source projections only; no target installation or golden acceptance"}, indent=2))
        return 1 if args.check and changes else 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {exc}; refresh is not accepted", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

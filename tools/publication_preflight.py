#!/usr/bin/env python3
"""Compare explicit deployable Git paths and selected evidence; never publish."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path, PurePosixPath

from target_validation_support import is_target_relative_path
from path_spec import logical_path

MAX_PATHS = 64
MAX_OUTPUT = 128 * 1024
COMMIT = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")


def _git(target: Path, *arguments: str, allowed_codes: tuple[int, ...] = (0,),
         max_output: int = MAX_OUTPUT) -> bytes:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1",
                       GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
    # Bound stdout during collection; diagnostics are discarded, never buffered.
    with subprocess.Popen(["git", "-c", "core.fsmonitor=false", "--literal-pathspecs", *arguments], cwd=target,
                          env=environment, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
        with ThreadPoolExecutor(max_workers=1) as reader:
            try:
                output = reader.submit(process.stdout.read, max_output + 1).result(timeout=30)
                if len(output) > max_output:
                    raise ValueError("publication Git output exceeds its byte limit")
                if process.wait(timeout=30) not in allowed_codes:
                    raise ValueError("publication comparison requires available bounded local Git objects")
                return output
            except FutureTimeoutError as exc:
                raise ValueError("publication Git observation timed out") from exc
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()


def _paths(paths: list[str], label: str = "required project paths") -> list[str]:
    if not isinstance(paths, list) or not 1 <= len(paths) <= MAX_PATHS:
        raise ValueError(f"select 1 to {MAX_PATHS} exact {label}")
    for path in paths:
        if (not isinstance(path, str) or len(path) > 1024 or not is_target_relative_path(path)
                or "\\" in path or "\x00" in path or path != PurePosixPath(path).as_posix()
                or any(part in {".", "..", ".git"} for part in path.split("/"))):
            raise ValueError(f"{label} must be contained POSIX file/subtree names")
        logical_path(path, pattern=True)  # Glyphs remain literal Git names, never patterns.
    if len(set(paths)) != len(paths):
        raise ValueError(f"{label} must not be duplicated")
    return paths


def _entries(target: Path, revision: str, paths: list[str]) -> dict[str, tuple[str, str, str]]:
    result = {}
    for row in _git(target, "ls-tree", "-t", "-z", "--full-tree", revision, "--", *paths).split(b"\0"):
        if not row:
            continue
        metadata, separator, name = row.partition(b"\t")
        parts = metadata.split()
        if not separator or len(parts) != 3:
            raise ValueError("Git returned an invalid tree entry")
        path = name.decode("utf-8")
        mode, kind, oid = (part.decode("ascii") for part in parts)
        if path in result or kind not in {"blob", "tree", "commit"} or not COMMIT.fullmatch(oid):
            raise ValueError("Git returned unsupported or duplicate tree entries")
        result[path] = (mode, kind, oid)
    return result


def _clean_candidate(target: Path, revision: str) -> None:
    root = _git(target, "rev-parse", "--show-toplevel").decode("utf-8").rstrip("\r\n")
    if Path(root).resolve() != target.resolve() or _git(target, "rev-parse", "HEAD").strip().decode("ascii") != revision:
        raise ValueError("selected evidence requires a checkout of the exact candidate at the Git worktree root")
    inventory = _git(target, "ls-files", "-v", "-z", max_output=8 * 1024 * 1024)
    if any(row[:2] != b"H " for row in inventory.split(b"\0") if row):
        raise ValueError("selected evidence requires a normal index without skip-worktree or assume-unchanged paths")
    if _git(target, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignore-submodules=none"):
        raise ValueError("selected evidence requires a clean candidate checkout; keep generated evidence ignored")


def publication_preflight(target: Path, source_revision: str, candidate_revision: str,
                          required_paths: list[str], *, absent_paths: list[str] | None = None,
                          context_index: str | None = None, context_paths: list[str] | None = None,
                          test_commands: list[str] | None = None) -> dict:
    paths = _paths(required_paths)
    absent = _paths(absent_paths, "absent paths") if absent_paths else []
    leaves = _paths(context_paths, "context paths") if context_paths else []
    if bool(context_index) != bool(leaves):
        raise ValueError("select --context-index and at least one --context-path together")
    commands = test_commands or []
    if (len(commands) > MAX_PATHS or any(not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,128}", name) for name in commands)
            or len(set(commands)) != len(commands)):
        raise ValueError("select bounded unique canonical test command IDs")
    # Refuse partial-clone discovery before any object lookup could fetch data.
    config = _git(target, "config", "--bool", "--get-regexp", r"remote\..*\.promisor", allowed_codes=(0, 1))
    if any(line.split()[-1:] == [b"true"] for line in config.splitlines()):
        raise ValueError("publication preflight requires a non-promisor local object store; no automatic fetch")
    for revision in (source_revision, candidate_revision):
        if not isinstance(revision, str) or not COMMIT.fullmatch(revision):
            raise ValueError("source and candidate must be immutable full lowercase Git commit IDs")
        resolved = _git(target, "rev-parse", "--verify", "--end-of-options", revision + "^{commit}").decode("ascii").strip()
        if resolved != revision:
            raise ValueError("source and candidate must identify exact local commits")
    source = _entries(target, source_revision, paths)
    candidate = _entries(target, candidate_revision, paths)
    failures = []
    for path in paths:
        left, right = source.get(path), candidate.get(path)
        if left is None or right is None:
            failures.append({"path": path, "reason": "required path is missing in source or candidate"})
        elif left[1] == "commit" or right[1] == "commit":
            failures.append({"path": path, "reason": "selected gitlink contents are not supported"})
        elif left != right:
            failures.append({"path": path, "reason": "required Git object type, mode or content differs"})
    if absent:
        forbidden = _entries(target, candidate_revision, absent)
        failures.extend({"path": path, "reason": "retired or forbidden path still exists in candidate"}
                        for path in absent if path in forbidden)
    if not failures and (leaves or commands):
        from publication_candidate_evidence import context_failures, test_evidence_failures

        _clean_candidate(target, candidate_revision)
        entries = lambda selected: _entries(target, candidate_revision, selected)
        if leaves:
            _paths([context_index], "context index paths")
            failures.extend(context_failures(target, context_index, leaves, entries))
        if commands:
            failures.extend(test_evidence_failures(target, candidate_revision, commands, entries))
        _clean_candidate(target, candidate_revision)
    return {"schema_version": 1, "report_kind": "alatyr-publication-preflight",
            "state": "different" if failures else "selected-tree-equivalent",
            "source_revision": source_revision, "candidate_revision": candidate_revision,
            "required_paths": paths, "absent_paths": absent, "context_index": context_index,
            "context_paths": leaves, "test_commands": commands, "failures": failures,
            "authorization_granted": False,
            "scope_completeness": "target-review-required",
            "publication_performed": False, "live_remote_verified": False,
            "limitation": "Selected Git paths and explicitly requested evidence only. Evidence is inspected, not executed or independently attested. Unselected paths, external gitlink contents and runtime behavior are not validated. Consume this exact candidate ID or repeat the comparison. Existing closure/publication checks still apply."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--candidate-ref", required=True)
    parser.add_argument("--path", action="append", required=True)
    parser.add_argument("--absent-path", action="append")
    parser.add_argument("--context-index")
    parser.add_argument("--context-path", action="append")
    parser.add_argument("--require-test-command", action="append")
    args = parser.parse_args()
    try:
        result = publication_preflight(
            args.target.resolve(), args.source_ref, args.candidate_ref, args.path,
            absent_paths=args.absent_path, context_index=args.context_index,
            context_paths=args.context_path, test_commands=args.require_test_command,
        )
        print(json.dumps(result, indent=2))
        return 1 if result["failures"] else 0
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"state": "unavailable", "error": str(exc), "publication_performed": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

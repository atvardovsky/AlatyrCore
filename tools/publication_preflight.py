#!/usr/bin/env python3
"""Compare explicit deployable Git paths before publication; never publish."""

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


def _git(target: Path, *arguments: str, allowed_codes: tuple[int, ...] = (0,)) -> bytes:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0")
    # Bound stdout during collection; diagnostics are discarded, never buffered.
    with subprocess.Popen(["git", "--literal-pathspecs", *arguments], cwd=target,
                          env=environment, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
        with ThreadPoolExecutor(max_workers=1) as reader:
            try:
                output = reader.submit(process.stdout.read, MAX_OUTPUT + 1).result(timeout=30)
                if len(output) > MAX_OUTPUT:
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


def _paths(paths: list[str]) -> list[str]:
    if not isinstance(paths, list) or not 1 <= len(paths) <= MAX_PATHS:
        raise ValueError(f"select 1 to {MAX_PATHS} exact required project paths")
    for path in paths:
        if (not isinstance(path, str) or len(path) > 1024 or not is_target_relative_path(path)
                or "\\" in path or "\x00" in path or path != PurePosixPath(path).as_posix()
                or any(part in {".", "..", ".git"} for part in path.split("/"))):
            raise ValueError("required paths must be exact contained POSIX file/subtree names")
        logical_path(path, pattern=True)  # Glyphs remain literal Git names, never patterns.
    if len(set(paths)) != len(paths):
        raise ValueError("required paths must not be duplicated")
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


def publication_preflight(target: Path, source_revision: str, candidate_revision: str, required_paths: list[str]) -> dict:
    paths = _paths(required_paths)
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
    return {"schema_version": 1, "report_kind": "alatyr-publication-preflight",
            "state": "different" if failures else "selected-tree-equivalent",
            "source_revision": source_revision, "candidate_revision": candidate_revision,
            "required_paths": paths, "failures": failures, "authorization_granted": False,
            "scope_completeness": "target-review-required",
            "publication_performed": False, "live_remote_verified": False,
            "limitation": "Exact selected Git object identity, including subtree modes and entries; unselected paths, external gitlink contents and runtime behavior are not validated. Consume this exact candidate ID before publication or repeat the comparison. Existing closure/publication checks still apply."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--candidate-ref", required=True)
    parser.add_argument("--path", action="append", required=True)
    args = parser.parse_args()
    try:
        result = publication_preflight(args.target.resolve(), args.source_ref, args.candidate_ref, args.path)
        print(json.dumps(result, indent=2))
        return 1 if result["failures"] else 0
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"state": "unavailable", "error": str(exc), "publication_performed": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Inspect or explicitly publish parent-scoped worker communication."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from local_file_lock import file_lock
from manage_session_presence import Once
from session_presence_store import git_identity, safe_hub, safe_regular
from source_context_selection import contained_source_path, source_json
from worker_communication import encode_view, project_group, read_source, select_group, validate_communication, validate_successor, validate_view_sizes, verify_bindings


def load_tree(raw: bytes) -> dict:
    try:
        return source_json(raw)
    except ValueError as exc:
        raise ValueError("worker communication ledger must be a strict JSON object") from exc


def ledger_lock_key(path: Path) -> str:
    safe_regular(path)
    info = path.parent.stat()
    if info.st_ino <= 0:
        raise ValueError("worker communication ledger has no stable local file identity")
    # Directory identity survives replacement and aliases without per-update locks.
    return hashlib.sha256(f"{info.st_dev}:{info.st_ino}".encode("ascii")).hexdigest()


def publish(target: Path, tree_path: str, raw: bytes, candidate_path: str, hub: Path) -> dict:
    output = target / tree_path
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    ignored = subprocess.run(["git", "-C", str(target), "check-ignore", "--no-index", "-q", "--", tree_path],
                             capture_output=True, timeout=10, check=False, env=env)
    if ignored.returncode != 0:
        raise ValueError("worker communication publication requires a Git-ignored ledger")
    tracked = subprocess.run(["git", "--literal-pathspecs", "-C", str(target), "ls-files", "--error-unmatch", "--", tree_path],
                             capture_output=True, timeout=10, check=False, env=env)
    if tracked.returncode != 1:
        raise ValueError("worker communication publication requires an untracked runtime ledger")
    candidate_raw = read_source(target, candidate_path)
    current, candidate = load_tree(raw), load_tree(candidate_raw)
    validate_successor(current, candidate)
    for group in candidate["communication"]["groups"]:
        if any(os.path.samefile(contained_source_path(target, row["path"]), output) for row in group["source_bindings"]):
            raise ValueError("worker communication cannot bind its own mutable ledger as evidence")
    validate_view_sizes(candidate, hashlib.sha256(candidate_raw).hexdigest())
    validate_communication(candidate, {row["node_id"]: row for row in candidate["nodes"]},
                           read_source=lambda path: read_source(target, path))
    safe_hub(hub, create=True)
    lock_path = hub / (ledger_lock_key(output) + ".lock")
    with file_lock(lock_path, timeout=5):
        if read_source(target, tree_path) != raw:
            raise ValueError("worker communication publication lost its snapshot comparison")
        validate_communication(candidate, {row["node_id"]: row for row in candidate["nodes"]},
                               read_source=lambda path: read_source(target, path))
        safe_regular(output)
        descriptor, temporary = tempfile.mkstemp(prefix=".worker-communication-", dir=output.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(candidate_raw)
                stream.flush()
                os.fsync(stream.fileno())
            deadline = time.monotonic() + 5
            while True:
                safe_regular(output)
                if read_source(target, tree_path) != raw:
                    raise ValueError("worker communication ledger changed before publication")
                try:
                    os.replace(temporary, output)
                    break
                except PermissionError:
                    if os.name != "nt" or time.monotonic() >= deadline:
                        raise
                    time.sleep(0.02)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return {"published": True, "generation": candidate["communication"]["generation"],
            "snapshot_sha256": hashlib.sha256(candidate_raw).hexdigest(),
            "authorization_granted": False, "acceptance_granted": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", type=Path, required=True, action=Once)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("identity", allow_abbrev=False)
    for name in ("inspect", "publish"):
        action = actions.add_parser(name, allow_abbrev=False)
        action.add_argument("--tree", required=True, action=Once, help="Target-relative existing execution-tree ledger.")
        for field in ("session-uid", "tree-uid", "parent-node", "participant-node", "expected-sha256"):
            action.add_argument("--" + field, required=True, action=Once)
        action.add_argument("--expected-generation", type=int, required=True, action=Once)
        if name == "publish":
            action.add_argument("--candidate", required=True, action=Once, help="Target-relative successor ledger; only communication may change.")
            action.add_argument("--write", required=True, action="store_true", help="Requires current primary-coordinator runtime-write authorization.")
    args = parser.parse_args()
    try:
        target = args.target.resolve(strict=True)
        worktree, presence_hub, repository_id = git_identity(target)
        worktree_id = hashlib.sha256(os.fsencode(str(worktree))).hexdigest()
        if args.action == "identity":
            sys.stdout.buffer.write(encode_view({"repository_id": repository_id, "worktree_id": worktree_id,
                                                "authentication_provided": False, "authorization_granted": False}))
            return 0
        raw = read_source(target, args.tree)
        digest = hashlib.sha256(raw).hexdigest()
        if digest != args.expected_sha256:
            raise ValueError("worker communication snapshot changed; reconcile before adopting a new digest")
        tree = load_tree(raw)
        bindings = dict(session_uid=args.session_uid, tree_uid=args.tree_uid,
            repository_id=repository_id, worktree_id=worktree_id,
            parent_node_id=args.parent_node, participant_node_id=args.participant_node,
            expected_generation=args.expected_generation)
        select_group(tree, **bindings)
        if args.action == "publish":
            if args.parent_node != tree["root_node_id"] or args.participant_node != tree["root_node_id"]:
                raise ValueError("only the primary coordinator publishes worker communication")
            result = publish(target, args.tree, raw, args.candidate,
                             presence_hub.parent / "alatyr-worker-communication")
            sys.stdout.buffer.write(encode_view(result))
            return 0
        result = project_group(tree, **bindings, read_source=lambda path: read_source(target, path))
        # Detect a coordinator publication or source update during selection.
        if read_source(target, args.tree) != raw:
            raise ValueError("worker communication snapshot changed during selection")
        verify_bindings(result["source_bindings"], lambda path: read_source(target, path))
        result["snapshot_sha256"] = digest
        sys.stdout.buffer.write(encode_view(result))
    except (OSError, ValueError, RuntimeError, RecursionError, subprocess.SubprocessError) as exc:
        print("FAIL: worker communication: " + str(exc)[:400], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

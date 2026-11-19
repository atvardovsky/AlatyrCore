"""Read-only target worktree routing checks for adapter work."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WorktreeRecord:
    path: Path
    branch: str | None
    detached: bool


def _git(target: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments],
        cwd=target,
        check=False,
        capture_output=True,
    )


def current_branch(target: Path) -> str:
    result = _git(target, "branch", "--show-current")
    if result.returncode != 0:
        return ""
    return result.stdout.decode("utf-8", errors="replace").strip()


def branch_exists(target: Path, branch: str) -> bool:
    result = _git(target, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}")
    return result.returncode == 0


def worktrees(target: Path) -> list[WorktreeRecord]:
    result = _git(target, "worktree", "list", "--porcelain")
    if result.returncode != 0:
        return []
    records: list[WorktreeRecord] = []
    path: Path | None = None
    branch: str | None = None
    detached = False
    for line in result.stdout.decode("utf-8", errors="surrogateescape").splitlines():
        if line.startswith("worktree "):
            if path is not None:
                records.append(WorktreeRecord(path, branch, detached))
            path = Path(line[len("worktree ") :])
            branch = None
            detached = False
        elif line.startswith("branch "):
            branch = line[len("branch ") :]
        elif line == "detached":
            detached = True
    if path is not None:
        records.append(WorktreeRecord(path, branch, detached))
    return records


def branch_policy(manifest: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        return {}
    policy = manifest.get("branch_policy")
    return policy if isinstance(policy, dict) else {}


def routing_issues(
    target: Path,
    manifest: dict[str, Any] | None,
    *,
    acceptance: bool = False,
    allow_detached: bool = False,
) -> list[dict[str, Any]]:
    """Return routing findings for the configured development branch.

    Targets without a configured branch policy, or whose configured branch does
    not exist locally, keep the previous behavior.  The check never prunes,
    switches, or mutates a worktree.
    """

    policy = branch_policy(manifest)
    canonical = policy.get("alatyr_development_branch")
    if not isinstance(canonical, str) or not canonical:
        return []
    if not branch_exists(target, canonical):
        return []

    current = current_branch(target)
    if current == canonical:
        return []
    if not current and allow_detached:
        return []

    strict = policy.get("require_canonical_worktree") is True
    level = "error" if acceptance and strict else "warning"
    records = [
        record
        for record in worktrees(target)
        if record.branch == f"refs/heads/{canonical}"
    ]
    valid = [record for record in records if os.path.isdir(record.path)]
    missing = [record for record in records if not os.path.isdir(record.path)]
    current_label = current or "detached HEAD"

    if valid:
        return [
            {
                "level": level,
                "blocking": True,
                "code": "WORKTREE_ROUTING_REQUIRED",
                "path": ".ai/alatyr.yaml",
                "message": (
                    f"current checkout is {current_label}; use the canonical "
                    f"{canonical} worktree at {valid[0].path.as_posix()}"
                ),
            }
        ]
    if missing:
        return [
            {
                "level": level,
                "blocking": True,
                "code": "WORKTREE_PATH_MISSING",
                "path": ".ai/alatyr.yaml",
                "message": (
                    f"canonical {canonical} worktree path is missing: "
                    f"{missing[0].path.as_posix()}; repair the worktree registration"
                ),
            }
        ]
    return [
        {
            "level": level,
            "blocking": True,
            "code": "WORKTREE_CANONICAL_UNAVAILABLE",
            "path": ".ai/alatyr.yaml",
            "message": (
                f"configured development branch {canonical} has no usable "
                "worktree; create or repair it before adapter work"
            ),
        }
    ]

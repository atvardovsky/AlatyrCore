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
        env={**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_OPTIONAL_LOCKS": "0"},
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


def _git_text(base: Path, *arguments: str) -> str | None:
    result = _git(base, *arguments)
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", errors="surrogateescape").strip()


def _git_path(base: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def worktree_identity_matches(target: Path, path: Path, branch: str) -> bool:
    """Confirm the directory is this repository's worktree root on the branch.

    Directory existence alone is insufficient: an old path can be recreated as
    an empty directory or reused by an unrelated repository.
    """

    if not os.path.isdir(path):
        return False
    try:
        if _git_text(path, "rev-parse", "--is-inside-work-tree") != "true":
            return False
        top = _git_path(
            path, _git_text(path, "rev-parse", "--show-toplevel")
        )
        if top is None or top != path.resolve():
            return False
        if _git_text(path, "branch", "--show-current") != branch:
            return False
        common = _git_path(
            path, _git_text(path, "rev-parse", "--git-common-dir")
        )
        target_common = _git_path(
            target, _git_text(target, "rev-parse", "--git-common-dir")
        )
        return common is not None and target_common is not None and common == target_common
    except (OSError, RuntimeError):
        return False


def branch_policy(manifest: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        return {}
    policy = manifest.get("branch_policy")
    return policy if isinstance(policy, dict) else {}


def upstream_issue(target: Path, policy: dict, acceptance: bool, tracking=None) -> list[dict[str, Any]]:
    if tracking is None:
        counts = (_git_text(target, "rev-list", "--left-right", "--count", "HEAD...@{upstream}") or "").split()
        ahead, behind = map(int, counts) if len(counts) == 2 and all(n.isascii() and n.isdigit() for n in counts) else (None, None)
    else:
        _, ahead, behind = tracking
    strict = policy.get("require_canonical_upstream_base") is True
    if behind is None:
        if not strict:
            return []
        code, message = "WORKTREE_UPSTREAM_UNAVAILABLE", "cannot establish the canonical checkout's locally recorded upstream base"
    elif behind:
        code = "WORKTREE_UPSTREAM_DIVERGED" if ahead else "WORKTREE_UPSTREAM_BEHIND"
        message = f"canonical checkout is {ahead or 0} ahead and {behind} behind its locally recorded upstream; reconcile the comparison base"
    else:
        return []
    return [{"level": "error" if acceptance and strict else "warning", "blocking": strict,
             "code": code, "path": ".ai/alatyr.yaml", "message": message + "; no remote state was queried"}]


def routing_issues(
    target: Path,
    manifest: dict[str, Any] | None,
    *,
    acceptance: bool = False,
    allow_detached: bool = False,
    tracking: tuple[str | None, int | None, int | None] | None = None,
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
        if policy.get("require_canonical_upstream_base") is True:
            return upstream_issue(target, policy, acceptance, (None, None, None))
        return []

    current = current_branch(target)
    if current == canonical:
        return upstream_issue(target, policy, acceptance, tracking)
    if not current and allow_detached:
        return []

    strict = policy.get("require_canonical_worktree") is True
    level = "error" if acceptance and strict else "warning"
    records = [
        record
        for record in worktrees(target)
        if record.branch == f"refs/heads/{canonical}"
    ]
    valid: list[WorktreeRecord] = []
    missing: list[WorktreeRecord] = []
    invalid: list[WorktreeRecord] = []
    for record in records:
        if not os.path.isdir(record.path):
            missing.append(record)
        elif worktree_identity_matches(target, record.path, canonical):
            valid.append(record)
        else:
            invalid.append(record)
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
    if invalid:
        return [
            {
                "level": level,
                "blocking": True,
                "code": "WORKTREE_PATH_INVALID",
                "path": ".ai/alatyr.yaml",
                "message": (
                    f"canonical {canonical} worktree path exists but is not a "
                    f"worktree root of this repository on {canonical}: "
                    f"{invalid[0].path.as_posix()}; repair the worktree registration"
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

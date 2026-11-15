"""Bounded Git control identity, separate from knowledge/content identity."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path


OID = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")


def validate_control(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != {"git_dir", "branch", "revision"}:
        raise ValueError("workspace control requires Git directory, branch and revision")
    if not isinstance(value["git_dir"], str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value["git_dir"]):
        raise ValueError("workspace control Git directory binding is invalid")
    branch, revision = value["branch"], value["revision"]
    if not isinstance(branch, str) or not (branch == "HEAD" or branch.startswith("refs/heads/") and len(branch) > 11) or "\n" in branch:
        raise ValueError("workspace control branch is invalid")
    if revision is not None and (not isinstance(revision, str) or not OID.fullmatch(revision)):
        raise ValueError("workspace control revision is invalid")
    if revision is None and branch == "HEAD":
        raise ValueError("detached workspace control requires a revision")
    return value


def capture_control(root: Path) -> dict | None:
    if not os.path.lexists(root / ".git"):
        return None
    environment = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    environment["GIT_OPTIONAL_LOCKS"] = "0"

    def git(*arguments):
        try:
            result = subprocess.run(["git", *arguments], cwd=root, env=environment,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=3, check=False)
            if len(result.stdout) > 16384:
                raise ValueError("workspace Git control output exceeds its bound")
            return result
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError("workspace Git control state is unavailable") from exc

    observed = git("rev-parse", "--show-toplevel", "--absolute-git-dir", "HEAD^{commit}", "--symbolic-full-name", "HEAD")
    lines = observed.stdout.decode("utf-8").splitlines()
    if observed.returncode == 0 and len(lines) == 4 and OID.fullmatch(lines[2]):
        top, directory, revision, branch = lines
    else:
        # An unborn branch is a valid installation target, not detached evidence.
        location = git("rev-parse", "--show-toplevel", "--absolute-git-dir")
        parts = location.stdout.decode("utf-8").splitlines()
        symbolic = git("symbolic-ref", "--quiet", "HEAD")
        branch = symbolic.stdout.decode("utf-8").strip()
        if location.returncode or len(parts) != 2 or symbolic.returncode or not branch.startswith("refs/heads/"):
            raise ValueError("workspace Git control state is invalid")
        missing = git("show-ref", "--verify", "--quiet", branch)
        if missing.returncode != 1:
            raise ValueError("workspace Git revision is invalid or changed during capture")
        top, directory = parts
        revision = None
    if Path(top).resolve() != root.resolve():
        raise ValueError("workspace control must name the worktree root, not a parent repository")
    return validate_control({"git_dir": "sha256:" + hashlib.sha256(str(Path(directory).resolve()).encode()).hexdigest(),
                             "branch": branch, "revision": revision})


def controls_match(before: dict, after: dict) -> bool:
    return before.get("control_state") == after.get("control_state")

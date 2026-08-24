"""Deterministic source-tree snapshots for read-only checker enforcement."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceEntry:
    kind: str
    mode: int
    digest: str


def _git_source_paths(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-c", "-o", "--exclude-standard", "-z"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(message or "cannot enumerate source paths")
    return sorted(
        path
        for path in result.stdout.decode("utf-8", errors="surrogateescape").split("\0")
        if path
    )


def source_snapshot(root: Path) -> dict[str, SourceEntry]:
    """Hash tracked and non-ignored untracked paths without following symlinks."""

    snapshot: dict[str, SourceEntry] = {}
    for relpath in _git_source_paths(root):
        path = root / relpath
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            snapshot[relpath] = SourceEntry("missing", 0, "")
            continue
        mode = stat.S_IMODE(metadata.st_mode)
        if stat.S_ISLNK(metadata.st_mode):
            try:
                target = os.readlink(path)
            except FileNotFoundError:
                snapshot[relpath] = SourceEntry("missing", 0, "")
                continue
            digest = hashlib.sha256(target.encode("utf-8", errors="surrogateescape")).hexdigest()
            snapshot[relpath] = SourceEntry("symlink", mode, digest)
        elif stat.S_ISREG(metadata.st_mode):
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            except FileNotFoundError:
                snapshot[relpath] = SourceEntry("missing", 0, "")
                continue
            snapshot[relpath] = SourceEntry("file", mode, digest)
        elif stat.S_ISDIR(metadata.st_mode):
            snapshot[relpath] = SourceEntry("directory", mode, "")
        else:
            snapshot[relpath] = SourceEntry("other", mode, "")
    return snapshot


def snapshot_changes(
    before: dict[str, SourceEntry], after: dict[str, SourceEntry]
) -> list[str]:
    changes: list[str] = []
    for relpath in sorted(set(before) | set(after)):
        if relpath not in before:
            changes.append(f"created {relpath}")
        elif relpath not in after:
            changes.append(f"removed {relpath}")
        elif before[relpath] != after[relpath]:
            changes.append(f"modified {relpath}")
    return changes

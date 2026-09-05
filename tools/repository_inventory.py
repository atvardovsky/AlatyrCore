"""Run-scoped Git-aware repository path inventory."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class RepositoryInventoryError(ValueError):
    """Raised when a repository inventory cannot be read safely."""


@dataclass(frozen=True)
class RepositoryPath:
    path: str
    kind: str


@dataclass(frozen=True)
class RepositoryInventory:
    root: Path
    entries: tuple[RepositoryPath, ...]

    @property
    def paths(self) -> tuple[str, ...]:
        """Return only paths that currently exist in the worktree."""

        return tuple(entry.path for entry in self.entries if entry.kind != "missing")

    @property
    def missing_paths(self) -> tuple[str, ...]:
        return tuple(entry.path for entry in self.entries if entry.kind == "missing")

    @classmethod
    def load(cls, root: Path) -> "RepositoryInventory":
        resolved = root.resolve()
        result = subprocess.run(
            ["git", "ls-files", "-c", "-o", "--exclude-standard", "-z"],
            cwd=resolved,
            check=False,
            capture_output=True,
        )
        if result.returncode != 0:
            message = result.stderr.decode("utf-8", errors="replace").strip()
            raise RepositoryInventoryError(
                message or f"cannot enumerate repository paths under {resolved}"
            )
        relpaths = sorted(
            path
            for path in result.stdout.decode(
                "utf-8", errors="surrogateescape"
            ).split("\0")
            if path
        )
        entries: list[RepositoryPath] = []
        for relpath in relpaths:
            path = resolved / relpath
            kind = (
                "symlink"
                if path.is_symlink()
                else "file"
                if path.is_file()
                else "missing"
            )
            entries.append(RepositoryPath(relpath, kind))
        return cls(root=resolved, entries=tuple(entries))

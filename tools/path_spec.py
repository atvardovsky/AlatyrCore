"""Named logical-path matching contracts shared by Alatyr source tools."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath, PureWindowsPath


class PathDialect(str, Enum):
    """Versioned matching semantics; names prevent accidental policy changes."""

    SOURCE_HOST_V1 = "source-host-v1"
    PORTABLE_FNMATCH_V1 = "portable-fnmatch-v1"
    SUPPORT_TREE_V1 = "support-tree-v1"
    APPROVAL_SCOPE_V1 = "approval-scope-v1"


def logical_path(value: str, *, pattern: bool = False) -> str:
    """Validate a strict repository-relative POSIX path or path pattern."""

    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("logical path must be a non-empty string")
    if "\\" in value or value.startswith("/") or "//" in value:
        raise ValueError(f"logical path must use normalized POSIX separators: {value}")
    if PureWindowsPath(value).drive:
        raise ValueError(f"logical path must not contain a Windows drive: {value}")
    raw_parts = value.split("/")
    parts = PurePosixPath(value).parts
    if any(part in {"", ".", ".."} for part in raw_parts) or any(
        part == ".." for part in parts
    ):
        raise ValueError(f"logical path must be normalized and repository-relative: {value}")
    if not pattern and any(marker in value for marker in "*?["):
        raise ValueError(f"logical path must not contain glob markers: {value}")
    return value


@dataclass(frozen=True)
class PathSpec:
    """One compiled policy pattern with explicit legacy-compatible semantics."""

    pattern: str
    dialect: PathDialect = PathDialect.PORTABLE_FNMATCH_V1

    def __post_init__(self) -> None:
        pattern = (
            self.pattern.replace("\\", "/")
            if self.dialect == PathDialect.APPROVAL_SCOPE_V1
            else self.pattern
        )
        logical_path(pattern, pattern=True)

    def matches(self, path: str) -> bool:
        candidate = path
        pattern = self.pattern
        if self.dialect == PathDialect.APPROVAL_SCOPE_V1:
            candidate = candidate.replace("\\", "/")
            pattern = pattern.replace("\\", "/")
        if self.dialect == PathDialect.SUPPORT_TREE_V1 and pattern.endswith("/**"):
            prefix = pattern[:-3].rstrip("/")
            return candidate == prefix or candidate.startswith(prefix + "/")
        if self.dialect == PathDialect.SOURCE_HOST_V1:
            return fnmatch.fnmatch(candidate, pattern)
        return fnmatch.fnmatchcase(candidate, pattern)


def matches_any(
    path: str,
    patterns: tuple[str, ...] | list[str],
    *,
    dialect: PathDialect = PathDialect.PORTABLE_FNMATCH_V1,
) -> bool:
    return any(PathSpec(pattern, dialect).matches(path) for pattern in patterns)


def select_paths(
    paths: tuple[str, ...] | list[str],
    patterns: tuple[str, ...] | list[str],
    *,
    dialect: PathDialect = PathDialect.PORTABLE_FNMATCH_V1,
) -> tuple[str, ...]:
    specs = tuple(PathSpec(pattern, dialect) for pattern in patterns)
    return tuple(sorted(path for path in paths if any(spec.matches(path) for spec in specs)))

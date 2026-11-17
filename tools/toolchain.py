"""Lightweight source-tooling prerequisite checks.

This module intentionally uses only the standard library and Python 3.8-compatible
syntax so it can report a clear failure before dependency-heavy modules load.
It applies to AlatyrCore *source tooling*, not to the Markdown framework or a
target adapter.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from typing import Callable, Iterable, Optional, Sequence, Tuple


MINIMUM_PYTHON = (3, 10)
REQUIRED_PACKAGES = ("yaml", "jsonschema")
MAX_REPORTED_PACKAGES = 8


class ToolchainError(RuntimeError):
    """One actionable prerequisite failure for source tooling."""


def format_version(version: Sequence[int]) -> str:
    return ".".join(str(part) for part in version[:3])


def python_failure(
    minimum: Tuple[int, int] = MINIMUM_PYTHON,
    *,
    version: Optional[Sequence[int]] = None,
) -> Optional[str]:
    """Return one message when the interpreter is too old, or None."""

    current = tuple(version if version is not None else sys.version_info[:3])
    required = ".".join(str(part) for part in minimum)
    if current[:2] < tuple(minimum):
        return (
            f"Python {required}+ is required for AlatyrCore source tooling "
            f"(found {format_version(current)}). Use a supported interpreter, "
            f"for example `python{required} tools/check_all.py`."
        )
    return None


def missing_packages(
    packages: Iterable[str] = REQUIRED_PACKAGES,
    *,
    find_spec: Optional[Callable[[str], object]] = None,
) -> Tuple[str, ...]:
    """Return declared packages that cannot be imported."""

    probe = find_spec or importlib.util.find_spec
    missing = []
    for name in packages:
        try:
            available = probe(name) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            available = False
        if not available:
            missing.append(name)
    return tuple(missing)


def package_failure(
    packages: Iterable[str] = REQUIRED_PACKAGES,
    *,
    find_spec: Optional[Callable[[str], object]] = None,
) -> Optional[str]:
    missing = missing_packages(packages, find_spec=find_spec)
    if not missing:
        return None
    shown = ", ".join(missing[:MAX_REPORTED_PACKAGES])
    suffix = "" if len(missing) <= MAX_REPORTED_PACKAGES else ", ..."
    return (
        f"missing source-tooling Python package(s): {shown}{suffix}. "
        "Install the documented dependencies with "
        "`python3 -m pip install -r requirements-dev.txt`."
    )


def git_failure(*, which: Optional[Callable[[str], Optional[str]]] = None) -> Optional[str]:
    finder = which or shutil.which
    if finder("git") is None:
        return (
            "Git is required for source snapshots, changed-path selection and "
            "release checks, but `git` was not found on PATH."
        )
    return None


def toolchain_failure(
    *,
    minimum: Tuple[int, int] = MINIMUM_PYTHON,
    version: Optional[Sequence[int]] = None,
    packages: Iterable[str] = REQUIRED_PACKAGES,
    require_git: bool = False,
    find_spec: Optional[Callable[[str], object]] = None,
    which: Optional[Callable[[str], Optional[str]]] = None,
) -> Optional[str]:
    """Return the first actionable prerequisite failure, or None.

    Checks are ordered cheapest and most fundamental first. The caller decides
    whether to print and exit; this helper never mutates state.
    """

    failures = (
        python_failure(minimum, version=version),
        package_failure(packages, find_spec=find_spec),
        git_failure(which=which) if require_git else None,
    )
    return next((failure for failure in failures if failure is not None), None)


def preflight(
    *,
    minimum: Tuple[int, int] = MINIMUM_PYTHON,
    version: Optional[Sequence[int]] = None,
    packages: Iterable[str] = REQUIRED_PACKAGES,
    require_git: bool = False,
    find_spec: Optional[Callable[[str], object]] = None,
    which: Optional[Callable[[str], Optional[str]]] = None,
) -> None:
    """Raise ToolchainError with one actionable message when a prerequisite fails."""

    failure = toolchain_failure(
        minimum=minimum,
        version=version,
        packages=packages,
        require_git=require_git,
        find_spec=find_spec,
        which=which,
    )
    if failure is not None:
        raise ToolchainError(failure)


def require_supported_python(
    minimum: Tuple[int, int] = MINIMUM_PYTHON,
    *,
    version: Optional[Sequence[int]] = None,
) -> None:
    """Exit with code 2 before dependency-heavy imports on an unsupported runtime."""

    failure = python_failure(minimum, version=version)
    if failure is not None:
        print(f"FAIL: {failure}", file=sys.stderr)
        raise SystemExit(2)

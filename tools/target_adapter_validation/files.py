"""File-presence helpers for target-adapter validation modules."""

from __future__ import annotations

from typing import Any, Iterable


def missing_target_files(host: Any, relpaths: Iterable[str]) -> list[str]:
    """Return target-relative files from relpaths that do not exist as files."""

    return [relpath for relpath in relpaths if not host.target_path(relpath).is_file()]

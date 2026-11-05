"""Bounded read-only evidence shared by optional project inspection tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from context_input_snapshot import ContextInputSnapshot
from path_spec import logical_path

MAX_FILE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 8 * MAX_FILE_BYTES
MAX_FILES = 256


class ProjectEvidence(ContextInputSnapshot):
    """Use the canonical freshness boundary with aggregate inspection ceilings."""

    def __init__(self, root: Path):
        super().__init__(root, regular_files_only=True)
        self.measured: dict[Path, int] = {}

    def read(self, path: Path, *, max_bytes: int | None = None) -> bytes:
        path = path.absolute()
        if path not in self.measured and len(self.measured) >= MAX_FILES:
            raise ValueError(f"evidence exceeds {MAX_FILES} unique files; decompose the selection")
        remaining = MAX_TOTAL_BYTES - sum(self.measured.values()) + self.measured.get(path, 0)
        limit = min(MAX_FILE_BYTES, remaining)
        if max_bytes is not None:
            if type(max_bytes) is not int or max_bytes < 1:
                raise ValueError("evidence byte limit must be a positive integer")
            limit = min(limit, max_bytes)
        raw = super().read(path, max_bytes=max(1, limit))
        if len(raw) > remaining:
            raise ValueError(f"evidence exceeds {MAX_TOTAL_BYTES} aggregate bytes")
        self.measured[path] = len(raw)
        return raw

    def exact(self, relpath: str) -> bytes:
        logical_path(relpath)
        return self.read(self.root / relpath)

    def object(self, relpath: str) -> dict[str, Any]:
        value = json.loads(self.exact(relpath))
        if not isinstance(value, dict):
            raise ValueError(f"{relpath} must contain a JSON object")
        return value

    def bindings(self) -> list[dict[str, str]]:
        return [{"path": path.relative_to(self.root).as_posix(), "sha256": digest}
                for path, digest in sorted(self.inputs.items())]

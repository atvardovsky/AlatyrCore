"""Cached filesystem reads shared by target-adapter validation modules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TargetPathEscapeError(ValueError):
    """Raised when a target-relative path resolves outside the target root."""


class ValidationContext:
    """Provide one read cache for a complete target validation run."""

    def __init__(self, target: Path) -> None:
        self.target = target.resolve()
        self._text_cache: dict[Path, str] = {}
        self._json_cache: dict[Path, tuple[Any | None, str | None]] = {}

    def resolve_path(self, path: Path) -> Path:
        resolved = path.resolve()
        try:
            resolved.relative_to(self.target)
        except ValueError as exc:
            raise TargetPathEscapeError(
                f"target path resolves outside {self.target}: {path} -> {resolved}"
            ) from exc
        return resolved

    def read_text(self, path: Path) -> str:
        if path in self._text_cache:
            return self._text_cache[path]
        resolved = self.resolve_path(path)
        try:
            text = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return ""
        self._text_cache[path] = text
        return text

    def read_json(self, path: Path) -> tuple[Any | None, str | None]:
        if path in self._json_cache:
            return self._json_cache[path]
        try:
            resolved = self.resolve_path(path)
        except (OSError, TargetPathEscapeError) as exc:
            return None, str(exc)
        try:
            data = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            return None, str(exc)
        self._json_cache[path] = (data, None)
        return self._json_cache[path]

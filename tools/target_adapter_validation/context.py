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
        resolved = self.resolve_path(path)
        if resolved not in self._text_cache:
            try:
                self._text_cache[resolved] = resolved.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                self._text_cache[resolved] = ""
        return self._text_cache[resolved]

    def read_json(self, path: Path) -> tuple[Any | None, str | None]:
        try:
            resolved = self.resolve_path(path)
        except (OSError, TargetPathEscapeError) as exc:
            return None, str(exc)
        if resolved not in self._json_cache:
            try:
                data = json.loads(resolved.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                self._json_cache[resolved] = (None, str(exc))
            else:
                self._json_cache[resolved] = (data, None)
        return self._json_cache[resolved]

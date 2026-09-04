"""Host boundary for extracted target-adapter domain validators."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from target_adapter_validation.context import ValidationContext


class DomainValidationHost(Protocol):
    """Operations domain validators may use from the validator orchestrator."""

    target: Path
    context: ValidationContext
    allow_placeholders: bool
    debug_git_state: bool
    debug_remote_ref: str | None

    def target_path(self, relpath: str) -> Path: ...

    def read_text(self, path: Path) -> str: ...

    def read_bytes(self, path: Path) -> bytes: ...

    def load_json_object(
        self, path: Path, code_prefix: str
    ) -> dict[str, Any] | None: ...

    def error(self, code: str, message: str, path: str | None = None) -> None: ...

    def warn(self, code: str, message: str, path: str | None = None) -> None: ...

    def info(self, code: str, message: str, path: str | None = None) -> None: ...

    def add_finding(
        self, level: str, code: str, message: str, path: str | None = None
    ) -> None: ...

    def check_policy_readme_projection(
        self,
        *,
        index: dict[str, Any],
        readme_relpath: str,
        fields: dict[str, str],
        code_prefix: str,
    ) -> None: ...

    def check_repository_binding(
        self, **kwargs: Any
    ) -> tuple[str | None, str | None]: ...

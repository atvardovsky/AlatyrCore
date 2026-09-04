"""Shared interface for target-adapter capability validators."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from target_adapter_validation.context import TargetFileStatus, TargetRepositoryView


class FindingSink(Protocol):
    """Receive findings through the validator's configured policy pipeline."""

    def error(self, code: str, message: str, path: str | None = None) -> None: ...

    def warn(self, code: str, message: str, path: str | None = None) -> None: ...

    def info(self, code: str, message: str, path: str | None = None) -> None: ...


@dataclass(frozen=True)
class CapabilityValidationContext:
    """Narrow host surface shared by extracted capability implementations."""

    filesystem: TargetRepositoryView
    findings: FindingSink
    allow_placeholders: bool
    resolve_target_path: Callable[[str], Path]
    read_target_text: Callable[[Path], str]
    load_target_json_object: Callable[[Path, str], dict[str, Any] | None]
    check_target_reference: Callable[[str, str, str], None]
    check_action_modes: Callable[[list[str], str, str], None]
    relative_target_path: Callable[[Path], str]
    module_enabled: Callable[[str, str, str, str], bool]

    @property
    def target(self) -> Path:
        return self.filesystem.target

    def target_path(self, relpath: str) -> Path:
        return self.resolve_target_path(relpath)

    def read_text(self, path: Path) -> str:
        return self.read_target_text(path)

    def read_bytes(self, path: Path) -> bytes:
        return self.filesystem.read_bytes(path)

    def content_digest(self, path: Path) -> str | None:
        return self.filesystem.content_digest(path)

    def status(self, path: Path) -> TargetFileStatus:
        return self.filesystem.status(path)

    def rel(self, path: Path) -> str:
        return self.relative_target_path(path)

    def load_json_object(
        self, path: Path, code_prefix: str
    ) -> dict[str, Any] | None:
        return self.load_target_json_object(path, code_prefix)

    def check_optional_target_reference(
        self, value: str, source: str, label: str
    ) -> None:
        self.check_target_reference(value, source, label)

    def check_allowed_actions(
        self, values: list[str], source: str, label: str
    ) -> None:
        self.check_action_modes(values, source, label)

    def module_validation_enabled(
        self,
        module_id: str,
        undeclared_code: str,
        state_missing_code: str,
        display_name: str,
    ) -> bool:
        return self.module_enabled(
            module_id,
            undeclared_code,
            state_missing_code,
            display_name,
        )

    def error(self, code: str, message: str, path: str | None = None) -> None:
        self.findings.error(code, message, path)

    def warn(self, code: str, message: str, path: str | None = None) -> None:
        self.findings.warn(code, message, path)

    def info(self, code: str, message: str, path: str | None = None) -> None:
        self.findings.info(code, message, path)


class CapabilityModule(Protocol):
    """Stable implementation contract for one extracted capability check."""

    check_id: str

    def validate(
        self,
        context: CapabilityValidationContext,
        manifest: Any,
    ) -> None: ...


@dataclass(frozen=True)
class FunctionCapabilityModule:
    """Bind one capability check function to the module dispatch contract."""

    check_id: str
    validator: Callable[[CapabilityValidationContext, Any], None]

    def validate(
        self,
        context: CapabilityValidationContext,
        manifest: Any,
    ) -> None:
        self.validator(context, manifest)

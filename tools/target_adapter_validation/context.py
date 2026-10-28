"""Coherent filesystem reads shared by target-adapter validation modules."""

from __future__ import annotations

if "." in (__package__ or ""):
    from ..context_input_snapshot import observe_context_bytes
else:
    from context_input_snapshot import observe_context_bytes

import hashlib
import json
import os
import stat
from dataclasses import dataclass, fields, replace
from enum import Enum
from pathlib import Path
from typing import Any, Generic, Iterator, TypeVar


MAX_DIRECTORY_ENTRIES = 1024
MAX_DIRECTORY_NAME_BYTES = 64 * 1024


class TargetPathEscapeError(ValueError):
    """Raised when a target-relative path resolves outside the target root."""


class TargetFileState(str, Enum):
    """Typed state for a target path or a decoded target value."""

    FILE = "file"
    DIRECTORY = "directory"
    OTHER = "other"
    MISSING = "missing"
    UNREADABLE = "unreadable"
    INVALID_TEXT = "invalid-text"
    INVALID_JSON = "invalid-json"
    UNSTABLE = "unstable"
    OUTSIDE_TARGET = "outside-target"


@dataclass(frozen=True)
class TargetFileStatus:
    """Filesystem identity captured for one target-relative path."""

    path: Path
    resolved_path: Path | None
    state: TargetFileState
    size: int | None = None
    mode: int | None = None
    mtime_ns: int | None = None
    device: int | None = None
    inode: int | None = None
    link_size: int | None = None
    link_mode: int | None = None
    link_mtime_ns: int | None = None
    error: str | None = None

    @property
    def exists(self) -> bool:
        return self.state not in {
            TargetFileState.MISSING,
            TargetFileState.OUTSIDE_TARGET,
        }

    @property
    def is_file(self) -> bool:
        return self.state == TargetFileState.FILE


T = TypeVar("T")


@dataclass(frozen=True)
class ValidationRead(Generic[T]):
    """Typed result from a run-scoped target read."""

    status: TargetFileStatus
    value: T | None
    error: str | None = None
    digest: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.value is not None

    def __iter__(self) -> Iterator[Any]:
        """Preserve the historical ``value, error = read_json(...)`` contract."""

        yield self.value
        yield self.error


@dataclass(frozen=True)
class _DirectorySnapshot:
    """Bounded immediate-entry metadata, never recursive content evidence."""

    state: str
    entries_measured: int = 0
    digest: str | None = None

    def diagnostics(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "entry_count": self.entries_measured if self.state == "complete" else None,
            "entries_measured": self.entries_measured,
            "sha256": self.digest,
        }


@dataclass(frozen=True)
class TargetMutation:
    """A relevant target path changed after its first observation."""

    path: Path
    before: TargetFileStatus
    after: TargetFileStatus
    content_changed: bool
    before_digest: str | None = None
    after_digest: str | None = None
    before_entries: _DirectorySnapshot | None = None
    after_entries: _DirectorySnapshot | None = None

    def diagnostics(self, root: Path) -> dict[str, Any]:
        """Explain captured changes without more I/O or exposing input contents."""

        def value(item: Any) -> Any:
            if isinstance(item, Path):
                try:
                    return item.relative_to(root).as_posix()
                except ValueError:
                    return "<outside-root>"
            if isinstance(item, Enum):
                return item.value
            return item

        changes = {}
        for field in fields(TargetFileStatus):
            if field.name in {"path", "error"}:
                continue
            before = getattr(self.before, field.name)
            after = getattr(self.after, field.name)
            if before != after:
                changes[field.name] = {"before": value(before), "after": value(after)}
        if self.before_digest is None:
            content_state = "not-measured"
        elif self.after_digest is None:
            content_state = "unavailable"
        else:
            content_state = "changed" if self.content_changed else "unchanged"
        details = {
            "before_state": self.before.state.value,
            "after_state": self.after.state.value,
            "metadata_changes": changes,
            "content": {
                "comparison": content_state,
                "before_sha256": self.before_digest,
                "after_sha256": self.after_digest,
            },
        }
        if self.before_entries is not None:
            before = self.before_entries
            after = self.after_entries or _DirectorySnapshot("unavailable")
            comparison = (
                "not-measured" if before.digest is None else
                "unavailable" if after.digest is None else
                "unchanged" if before.digest == after.digest else "changed"
            )
            details["directory_entries"] = {
                "scope": "immediate-child-names-and-lstat; not file contents or recursive evidence",
                "comparison": comparison,
                "before": before.diagnostics(),
                "after": after.diagnostics(),
            }
        return details

    @staticmethod
    def summary(diagnostics: dict[str, Any]) -> str:
        changed = ", ".join(diagnostics["metadata_changes"]) or "none"
        result = f"changed metadata: {changed}; content: {diagnostics['content']['comparison']}"
        if "directory_entries" in diagnostics:
            result += f"; directory entries: {diagnostics['directory_entries']['comparison']}"
        return result


@dataclass(frozen=True)
class _ObservedTarget:
    status: TargetFileStatus
    digest: str | None
    entries: _DirectorySnapshot | None = None


@dataclass(frozen=True)
class _ContentSnapshot:
    status: TargetFileStatus
    data: bytes
    digest: str


@dataclass(frozen=True)
class _ContextTextSource:
    """Path-like parser input whose content is owned by ValidationContext."""

    context: "TargetRepositoryView"
    path: Path

    def read_text(self, encoding: str = "utf-8") -> str:
        if encoding.casefold().replace("-", "") != "utf8":
            raise ValueError(f"unsupported target text encoding: {encoding}")
        return self.context.read_text(self.path)

    def __str__(self) -> str:
        return str(self.path)


class TargetRepositoryView:
    """Provide one verified, run-scoped view of target repository inputs."""

    def __init__(self, target: Path) -> None:
        self.target = target.resolve()
        self._bytes_cache: dict[Path, _ContentSnapshot] = {}
        self._text_cache: dict[tuple[Path, str], ValidationRead[str]] = {}
        self._json_cache: dict[tuple[Path, str], ValidationRead[Any]] = {}
        self._observed: dict[Path, _ObservedTarget] = {}

    def _candidate(self, path: Path) -> Path:
        return path if path.is_absolute() else self.target / path

    def _cache_key(self, path: Path) -> Path:
        return self._candidate(path).absolute()

    def resolve_path(self, path: Path) -> Path:
        candidate = self._candidate(path)
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.target)
        except ValueError as exc:
            raise TargetPathEscapeError(
                f"target path resolves outside {self.target}: {path} -> {resolved}"
            ) from exc
        return resolved

    def text_source(self, path: Path) -> _ContextTextSource:
        """Return a parser-compatible source backed by the coherent text cache."""

        return _ContextTextSource(self, self._candidate(path))

    def _status(self, path: Path) -> TargetFileStatus:
        candidate = self._candidate(path)
        key = self._cache_key(candidate)
        try:
            resolved = self.resolve_path(candidate)
        except TargetPathEscapeError as exc:
            return TargetFileStatus(
                path=key,
                resolved_path=None,
                state=TargetFileState.OUTSIDE_TARGET,
                error=str(exc),
            )
        try:
            link_info = candidate.lstat()
            info = resolved.stat()
        except FileNotFoundError as exc:
            return TargetFileStatus(
                path=key,
                resolved_path=resolved,
                state=TargetFileState.MISSING,
                error=str(exc),
            )
        except OSError as exc:
            return TargetFileStatus(
                path=key,
                resolved_path=resolved,
                state=TargetFileState.UNREADABLE,
                error=str(exc),
            )
        if stat.S_ISREG(info.st_mode):
            state = TargetFileState.FILE
        elif stat.S_ISDIR(info.st_mode):
            state = TargetFileState.DIRECTORY
        else:
            state = TargetFileState.OTHER
        return TargetFileStatus(
            path=key,
            resolved_path=resolved,
            state=state,
            size=info.st_size,
            mode=info.st_mode,
            mtime_ns=info.st_mtime_ns,
            device=info.st_dev,
            inode=info.st_ino,
            link_size=link_info.st_size,
            link_mode=link_info.st_mode,
            link_mtime_ns=link_info.st_mtime_ns,
        )

    def _remember(self, status: TargetFileStatus, digest: str | None = None) -> None:
        observed = self._observed.get(status.path)
        if observed is None:
            self._observed[status.path] = _ObservedTarget(
                status=status, digest=digest,
                entries=self._directory_snapshot(status)
                if status.state == TargetFileState.DIRECTORY else None,
            )
        elif observed.digest is None and digest is not None:
            self._observed[status.path] = replace(observed, digest=digest)

    def _directory_snapshot(self, before: TargetFileStatus) -> _DirectorySnapshot:
        """Capture diagnostic identity without following entries or reading content."""

        entries = []
        name_bytes = 0
        try:
            resolved = self.resolve_path(before.path)
            if resolved != before.resolved_path:
                return _DirectorySnapshot("unstable")
            with os.scandir(resolved) as children:
                for child in children:
                    name_bytes += len(os.fsencode(child.name))
                    if len(entries) >= MAX_DIRECTORY_ENTRIES or name_bytes > MAX_DIRECTORY_NAME_BYTES:
                        return _DirectorySnapshot("limit-exceeded", len(entries))
                    info = child.stat(follow_symlinks=False)
                    entries.append((child.name, info.st_dev, info.st_ino, info.st_mode,
                                    info.st_size, info.st_mtime_ns))
            if not self._same_status(before, self._status(before.path)):
                return _DirectorySnapshot("unstable", len(entries))
        except (OSError, TargetPathEscapeError):
            return _DirectorySnapshot("unavailable", len(entries))
        data = json.dumps(sorted(entries), ensure_ascii=True, separators=(",", ":")).encode("ascii")
        return _DirectorySnapshot("complete", len(entries), hashlib.sha256(data).hexdigest())

    def status(self, path: Path) -> TargetFileStatus:
        """Capture typed path state without caching path authorization."""

        status = self._status(path)
        if status.state == TargetFileState.OUTSIDE_TARGET:
            raise TargetPathEscapeError(status.error or "target path escapes target")
        self._remember(status)
        return status

    def is_target_file(self, path: str | Path) -> bool:
        """Return file presence while adding the path to the coherent view."""

        return self.status(Path(path)).is_file

    def is_target_dir(self, path: str | Path) -> bool:
        """Return directory presence while adding the path to the coherent view."""

        return self.status(Path(path)).state == TargetFileState.DIRECTORY

    def target_exists(self, path: str | Path) -> bool:
        """Return path presence while adding the path to the coherent view."""

        return self.status(Path(path)).exists

    def read_bytes_result(self, path: Path, *, max_bytes: int | None = None) -> ValidationRead[bytes]:
        """Read target bytes once while rechecking containment on every access."""

        candidate = self._candidate(path)
        key = self._cache_key(candidate)
        resolved = self.resolve_path(candidate)
        cached = self._bytes_cache.get(key)
        if cached is not None:
            if max_bytes is not None and len(cached.data) > max_bytes:
                return ValidationRead(status=cached.status, value=None, error=f"target file exceeds {max_bytes} bytes")
            if cached.status.resolved_path != resolved:
                status = replace(
                    self._status(candidate),
                    state=TargetFileState.UNSTABLE,
                    error="target path resolved to a different file during validation",
                )
                return ValidationRead(status=status, value=None, error=status.error)
            observe_context_bytes(self.target, resolved, cached.data)
            return ValidationRead(
                status=cached.status,
                value=cached.data,
                digest=cached.digest,
            )

        before = self._status(candidate)
        if before.state != TargetFileState.FILE:
            self._remember(before)
            return ValidationRead(
                status=before,
                value=None,
                error=before.error or before.state.value,
            )
        if max_bytes is not None and before.size is not None and before.size > max_bytes:
            self._remember(before)
            return ValidationRead(status=before, value=None, error=f"target file exceeds {max_bytes} bytes")
        try:
            if max_bytes is None:
                data = resolved.read_bytes()
            else:
                with resolved.open("rb") as handle:
                    data = handle.read(max_bytes + 1)
        except OSError as exc:
            unreadable = replace(
                before,
                state=TargetFileState.UNREADABLE,
                error=str(exc),
            )
            self._remember(unreadable)
            return ValidationRead(status=unreadable, value=None, error=str(exc))
        after = self._status(candidate)
        if before != after:
            unstable = replace(
                after,
                state=TargetFileState.UNSTABLE,
                error="target file changed while it was being read",
            )
            self._remember(unstable)
            return ValidationRead(status=unstable, value=None, error=unstable.error)
        if max_bytes is not None and len(data) > max_bytes:
            self._remember(after)
            return ValidationRead(status=after, value=None, error=f"target file exceeds {max_bytes} bytes")
        digest = hashlib.sha256(data).hexdigest()
        snapshot = _ContentSnapshot(status=after, data=data, digest=digest)
        self._bytes_cache[key] = snapshot
        self._remember(after, digest)
        observe_context_bytes(self.target, resolved, data)
        return ValidationRead(status=after, value=data, digest=digest)

    def read_text(self, path: Path) -> str:
        """Compatibility text API preserving the historical empty-string fallback."""

        result = self.read_text_result(path)
        return result.value if result.value is not None else ""

    def read_bytes(self, path: Path) -> bytes:
        """Compatibility bytes API; typed callers should use ``read_bytes_result``."""

        result = self.read_bytes_result(path)
        return result.value if result.value is not None else b""

    def read_text_result(self, path: Path) -> ValidationRead[str]:
        """Decode cached target bytes and expose invalid text as a typed state."""

        byte_result = self.read_bytes_result(path)
        if byte_result.value is None or byte_result.digest is None:
            return ValidationRead(
                status=byte_result.status,
                value=None,
                error=byte_result.error,
                digest=byte_result.digest,
            )
        key = (byte_result.status.path, byte_result.digest)
        cached = self._text_cache.get(key)
        if cached is not None:
            return cached
        try:
            text = byte_result.value.decode("utf-8")
        except UnicodeError as exc:
            status = replace(
                byte_result.status,
                state=TargetFileState.INVALID_TEXT,
                error=str(exc),
            )
            result = ValidationRead[str](
                status=status,
                value=None,
                error=str(exc),
                digest=byte_result.digest,
            )
        else:
            result = ValidationRead[str](
                status=byte_result.status,
                value=text,
                digest=byte_result.digest,
            )
        self._text_cache[key] = result
        return result

    def read_json_result(self, path: Path) -> ValidationRead[Any]:
        """Parse one cached target text snapshot and retain typed parse state."""

        try:
            text_result = self.read_text_result(path)
        except (OSError, TargetPathEscapeError) as exc:
            status = TargetFileStatus(
                path=self._cache_key(path),
                resolved_path=None,
                state=TargetFileState.OUTSIDE_TARGET,
                error=str(exc),
            )
            return ValidationRead(status=status, value=None, error=str(exc))
        if text_result.value is None or text_result.digest is None:
            return ValidationRead(
                status=text_result.status,
                value=None,
                error=text_result.error,
                digest=text_result.digest,
            )
        key = (text_result.status.path, text_result.digest)
        cached = self._json_cache.get(key)
        if cached is not None:
            return cached
        try:
            data = json.loads(text_result.value)
        except (json.JSONDecodeError, RecursionError) as exc:
            status = replace(
                text_result.status,
                state=TargetFileState.INVALID_JSON,
                error=str(exc),
            )
            result = ValidationRead[Any](
                status=status,
                value=None,
                error=str(exc),
                digest=text_result.digest,
            )
        else:
            result = ValidationRead[Any](
                status=text_result.status,
                value=data,
                digest=text_result.digest,
            )
        self._json_cache[key] = result
        return result

    def read_json(self, path: Path) -> ValidationRead[Any]:
        """Compatibility JSON API whose result can still be unpacked as a pair."""

        return self.read_json_result(path)

    def content_digest(self, path: Path) -> str | None:
        """Return the SHA-256 digest of the coherent target snapshot."""

        return self.read_bytes_result(path).digest

    @staticmethod
    def _same_status(before: TargetFileStatus, after: TargetFileStatus) -> bool:
        return replace(before, error=None) == replace(after, error=None)

    def finalize(self) -> tuple[TargetMutation, ...]:
        """Detect relevant target inputs changed after their first observation."""

        mutations: list[TargetMutation] = []
        for key, observed in sorted(self._observed.items(), key=lambda item: str(item[0])):
            after = self._status(key)
            after_digest: str | None = None
            if observed.digest is not None and after.state == TargetFileState.FILE:
                try:
                    resolved = self.resolve_path(key)
                    after_digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
                except (OSError, TargetPathEscapeError):
                    after_digest = None
            content_changed = (
                observed.digest is not None and after_digest != observed.digest
            )
            if not self._same_status(observed.status, after) or content_changed:
                mutations.append(
                    TargetMutation(
                        path=key,
                        before=observed.status,
                        after=after,
                        content_changed=content_changed,
                        before_digest=observed.digest,
                        after_digest=after_digest,
                        before_entries=observed.entries,
                        after_entries=self._directory_snapshot(after)
                        if observed.entries is not None and after.state == TargetFileState.DIRECTORY else None,
                    )
                )
        return tuple(mutations)


class ValidationContext(TargetRepositoryView):
    """Backward-compatible name for the target repository view."""

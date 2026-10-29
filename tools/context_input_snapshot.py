"""Invocation-local support reads with bounded reuse and final byte verification."""

from __future__ import annotations

import hashlib
import os
import stat
from collections import OrderedDict
from contextvars import ContextVar
from pathlib import Path


_ACTIVE: ContextVar[ContextInputSnapshot | None] = ContextVar("alatyr-context-inputs", default=None)


class ContextInputChanged(ValueError):
    def __init__(self, path: Path, message: str):
        self.path = path
        super().__init__(message)


class ContextInputLimit(ContextInputChanged):
    pass


def _limited_read(path: Path, max_bytes: int | None, *, regular_only: bool = False) -> bytes:
    if max_bytes is not None and (type(max_bytes) is not int or max_bytes < 1):
        raise ValueError("context input byte limit must be a positive integer")
    if regular_only:
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ContextInputChanged(path, "context input must be a regular file")
            raw = stream.read() if max_bytes is None else stream.read(max_bytes + 1)
    elif max_bytes is None:
        return path.read_bytes()
    else:
        with path.open("rb") as stream:
            raw = stream.read(max_bytes + 1)
    if max_bytes is not None and len(raw) > max_bytes:
        raise ContextInputLimit(path, f"context input exceeds {max_bytes} bytes")
    return raw


def read_regular_context_bytes(path: Path, *, max_bytes: int) -> bytes:
    """Read bounded regular-file evidence without blocking on a FIFO."""

    return _limited_read(path, max_bytes, regular_only=True)


class ContextInputSnapshot:
    """Cache input bytes, not decisions; every successful scope verifies disk bytes."""

    def __init__(self, root: Path, *, cache_bytes: int = 4 * 1024 * 1024,
                 regular_files_only: bool = False):
        if type(cache_bytes) is not int or cache_bytes < 0:
            raise ValueError("snapshot cache_bytes must be a non-negative integer")
        self.root = root.resolve()
        self.regular_files_only = regular_files_only
        self.limit = cache_bytes
        self.inputs: dict[Path, str] = {}
        self.read_limits: dict[Path, int] = {}
        self.cache: OrderedDict[Path, bytes] = OrderedDict()
        self.used = 0
        self.conflict: Path | None = None

    def __enter__(self):
        self.token = _ACTIVE.set(self)
        return self

    def __exit__(self, kind, value, traceback):
        try:
            if kind is None:
                self.verify()
        finally:
            _ACTIVE.reset(self.token)
            self.cache.clear()
            self.inputs.clear()
            self.read_limits.clear()
            self.used = 0
            self.conflict = None

    def read(self, path: Path, *, max_bytes: int | None = None) -> bytes:
        path = path.absolute()
        if max_bytes is not None:
            if type(max_bytes) is not int or max_bytes < 1:
                raise ValueError("context input byte limit must be a positive integer")
            self.read_limits[path] = min(max_bytes, self.read_limits.get(path, max_bytes))
        if path != self.root and self.root not in path.parents:
            raise ContextInputChanged(path, "context input escapes the target snapshot")
        cached = self.cache.get(path)
        if cached is not None:
            if max_bytes is not None and len(cached) > max_bytes:
                raise ContextInputLimit(path, f"context input exceeds {max_bytes} bytes")
            self.cache.move_to_end(path)
            return cached
        raw = self._physical(path) if max_bytes is None else self._physical(path, max_bytes=max_bytes)
        return self.observe(path, raw)

    def _physical(self, path: Path, *, max_bytes: int | None = None) -> bytes:
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError) as exc:
            self.conflict = path
            raise ContextInputChanged(path, "context input containment changed during planning") from exc
        if resolved != path:
            self.conflict = path
            raise ContextInputChanged(path, "context input changed containment during planning")
        try:
            if self.regular_files_only:
                return _limited_read(path, max_bytes, regular_only=True)
            return _limited_read(path, max_bytes)
        except OSError as exc:
            if path in self.inputs:
                self.conflict = path
                raise ContextInputChanged(path, "context input disappeared during planning") from exc
            raise

    def observe(self, path: Path, raw: bytes) -> bytes:
        path = path.absolute()
        if path != self.root and self.root not in path.parents:
            raise ContextInputChanged(path, "context input escapes the target snapshot")
        digest = hashlib.sha256(raw).hexdigest()
        previous = self.inputs.get(path)
        if previous is not None and previous != digest:
            self.conflict = path
            raise ContextInputChanged(path, "context input changed during planning")
        self.inputs[path] = digest
        if len(raw) <= self.limit:
            old = self.cache.pop(path, None)
            if old is not None:
                self.used -= len(old)
            while self.cache and self.used + len(raw) > self.limit:
                _, old = self.cache.popitem(last=False)
                self.used -= len(old)
            self.cache[path] = raw
            self.used += len(raw)
        return raw

    def verify(self) -> None:
        if self.conflict is not None:
            raise ContextInputChanged(self.conflict, "context input changed during planning")
        for path, expected in self.inputs.items():
            try:
                limit = self.read_limits.get(path)
                raw = self._physical(path) if limit is None else self._physical(path, max_bytes=limit)
                current = hashlib.sha256(raw).hexdigest()
            except OSError as exc:
                raise ContextInputChanged(path, "context input disappeared during planning") from exc
            if current != expected:
                raise ContextInputChanged(path, "context input changed during planning")


def read_context_bytes(path: Path, *, routing_input: bool = True, max_bytes: int | None = None) -> bytes:
    snapshot = _ACTIVE.get()
    if snapshot is not None and (routing_input or path.absolute() in snapshot.inputs):
        return snapshot.read(path, max_bytes=max_bytes)
    return _limited_read(path, max_bytes)


def observe_context_bytes(root: Path, path: Path, raw: bytes) -> None:
    """Include already bounded target-view reads without replacing their reader."""
    snapshot = _ACTIVE.get()
    if snapshot is not None and snapshot.root == root:
        snapshot.observe(path, raw)

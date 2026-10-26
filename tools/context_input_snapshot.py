"""Invocation-local support reads with bounded reuse and final byte verification."""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from contextvars import ContextVar
from pathlib import Path


_ACTIVE: ContextVar[ContextInputSnapshot | None] = ContextVar("alatyr-context-inputs", default=None)


class ContextInputChanged(ValueError):
    def __init__(self, path: Path, message: str):
        self.path = path
        super().__init__(message)


class ContextInputSnapshot:
    """Cache input bytes, not decisions; every successful scope verifies disk bytes."""

    def __init__(self, root: Path, *, cache_bytes: int = 4 * 1024 * 1024):
        if type(cache_bytes) is not int or cache_bytes < 0:
            raise ValueError("snapshot cache_bytes must be a non-negative integer")
        self.root = root.resolve()
        self.limit = cache_bytes
        self.inputs: dict[Path, str] = {}
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
            self.used = 0
            self.conflict = None

    def read(self, path: Path) -> bytes:
        path = path.absolute()
        if path != self.root and self.root not in path.parents:
            raise ContextInputChanged(path, "context input escapes the target snapshot")
        cached = self.cache.get(path)
        if cached is not None:
            self.cache.move_to_end(path)
            return cached
        return self.observe(path, self._physical(path))

    def _physical(self, path: Path) -> bytes:
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError) as exc:
            self.conflict = path
            raise ContextInputChanged(path, "context input containment changed during planning") from exc
        if resolved != path:
            self.conflict = path
            raise ContextInputChanged(path, "context input changed containment during planning")
        try:
            return path.read_bytes()
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
                current = hashlib.sha256(self._physical(path)).hexdigest()
            except OSError as exc:
                raise ContextInputChanged(path, "context input disappeared during planning") from exc
            if current != expected:
                raise ContextInputChanged(path, "context input changed during planning")


def read_context_bytes(path: Path, *, routing_input: bool = True) -> bytes:
    snapshot = _ACTIVE.get()
    if snapshot is not None and (routing_input or path.absolute() in snapshot.inputs):
        return snapshot.read(path)
    return path.read_bytes()


def observe_context_bytes(root: Path, path: Path, raw: bytes) -> None:
    """Include already bounded target-view reads without replacing their reader."""
    snapshot = _ACTIVE.get()
    if snapshot is not None and snapshot.root == root:
        snapshot.observe(path, raw)

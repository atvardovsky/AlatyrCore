"""Owned support-file writes and conflict-preserving rollback for local tools."""

from __future__ import annotations

import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path

from local_file_lock import file_lock, regular_file

def safe_output(target: Path, path: Path) -> Path:
    path = path.absolute()
    relative = path.relative_to(target.absolute())
    if ".." in relative.parts:
        raise ValueError("support output escapes target")
    cursor = target
    for component in relative.parts[:-1]:
        cursor = cursor / component
        if cursor.is_symlink() or (cursor.exists() and not cursor.is_dir()):
            raise ValueError("support output crosses an unsafe parent")
        if cursor.exists() and getattr(cursor.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise ValueError("support output crosses a reparse-point parent")
    path.resolve().relative_to(target.resolve())
    regular_file(path, missing_ok=True)
    return path


def read_output(target: Path, path: Path, *, max_bytes: int | None = None) -> bytes | None:
    path = safe_output(target, path)
    if not path.exists():
        return None
    if max_bytes is not None and path.stat().st_size > max_bytes:
        raise ValueError("support output exceeds bounded transaction size")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("unsafe support input file")
        content = stream.read(max_bytes + 1 if max_bytes is not None else -1)
    if max_bytes is not None and len(content) > max_bytes:
        raise ValueError("support output grew beyond bounded transaction size")
    return content


def replace_output(target: Path, path: Path, expected: bytes | None, desired: bytes | None) -> None:
    if read_output(target, path) != expected:
        raise ValueError(f"support output changed concurrently: {path.relative_to(target)}")
    if expected == desired:
        return
    path = safe_output(target, path)
    if desired is None:
        path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_output(target, path)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    descriptor, temporary = tempfile.mkstemp(prefix=".alatyr-write-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(desired)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        # Cooperative writers hold support_writer_lock throughout planning and commit.
        if read_output(target, path) != expected:
            raise ValueError(f"support output changed concurrently: {path.relative_to(target)}")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def support_writer_lock(target: Path, *, timeout: float = 5.0):
    path = target / ".ai/.runtime/support-writer/transaction.lock"
    safe_output(target, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_output(target, path)
    with file_lock(path, timeout=timeout):
        yield


class SupportTransaction:
    def __init__(self, target: Path):
        self.target = target
        self.before: dict[Path, bytes | None] = {}
        self.owned: dict[Path, bytes | None] = {}

    def apply(self, outputs: dict[Path, bytes | None], *, expected_inputs: dict[Path, bytes | None] | None = None) -> None:
        for path, postimage in self.owned.items():
            if read_output(self.target, path) != postimage:
                raise ValueError(f"previously owned support output changed concurrently: {path.relative_to(self.target)}")
        if expected_inputs is not None:
            for path, content in expected_inputs.items():
                if read_output(self.target, path) != content:
                    raise ValueError(f"support input changed while planning: {path.relative_to(self.target)}")
        preimages = {path: read_output(self.target, path) for path in outputs}
        if expected_inputs is not None and any(content != expected_inputs.get(path) for path, content in preimages.items()):
            raise ValueError("support output changed while planning")
        for path, content in outputs.items():
            self.before.setdefault(path, preimages[path])
            replace_output(self.target, path, preimages[path], content)
            self.owned[path] = content

    def rollback(self) -> list[str]:
        conflicts = []
        for path, postimage in reversed(tuple(self.owned.items())):
            try:
                replace_output(self.target, path, postimage, self.before[path])
            except (OSError, ValueError):
                conflicts.append(path.relative_to(self.target).as_posix())
        return conflicts

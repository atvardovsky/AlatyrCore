"""Bounded local storage for source-check timing and result evidence."""

from __future__ import annotations

import json
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CACHE_SCHEMA_VERSION = 1
CACHE_KIND = "alatyr-source-check-local-cache"
CHECK_RESULT_CONTRACT = "alatyr-source-check-result-cache-v1"
MAX_CACHE_RECORD_BYTES = 10 * 1024 * 1024
MAX_CHECK_CACHE_RECORDS = 512
SAFE_KEY = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]*")


@dataclass(frozen=True)
class CacheLoad:
    """Result of a fail-open local optimization cache read."""

    status: str
    value: dict[str, Any] | None = None
    detail: str | None = None


def resolve_cache_root(repository: Path) -> Path:
    """Resolve worktree-safe Git-local cache storage."""

    result = subprocess.run(
        ["git", "rev-parse", "--git-path", "alatyr-cache"],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise ValueError(result.stderr.strip() or "cannot resolve Git-local cache path")
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else (repository / path).resolve()


def cache_key(profile: str, *, include_profile: bool = True) -> str:
    """Return a portable cache partition for this runtime and optional profile."""

    runtime = f"{sys.platform}-py{sys.version_info.major}.{sys.version_info.minor}"
    return f"{profile}-{runtime}" if include_profile else runtime


def check_result_key(check_id: str, identity: dict[str, Any]) -> str:
    """Return a content-addressed key for one independently reusable check."""

    payload = json.dumps(
        identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    safe_id = re.sub(r"[^a-zA-Z0-9._-]", "-", check_id)
    return f"{safe_id}-{digest}"


class SourceCheckCache:
    """Store disposable timing hints and local result reports atomically."""

    def __init__(self, repository: Path) -> None:
        self.root = resolve_cache_root(repository)

    def _path(self, namespace: str, key: str) -> Path:
        if namespace not in {"timing", "results", "checks"}:
            raise ValueError(f"unsupported source-check cache namespace: {namespace}")
        if not SAFE_KEY.fullmatch(key):
            raise ValueError(f"unsafe source-check cache key: {key}")
        namespace_path = self.root / namespace
        if self.root.is_symlink() or namespace_path.is_symlink():
            raise ValueError("source-check cache directories must not be symlinks")
        return namespace_path / f"{key}.json"

    def load(self, namespace: str, key: str) -> CacheLoad:
        """Load one bounded record; corruption disables the optimization only."""

        path = self._path(namespace, key)
        try:
            if path.is_symlink():
                return CacheLoad("unsafe", detail="cache record is a symlink")
            size = path.stat().st_size
            if size > MAX_CACHE_RECORD_BYTES:
                return CacheLoad("oversized", detail=f"cache record is {size} bytes")
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return CacheLoad("missing")
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            return CacheLoad("corrupt", detail=str(exc))
        if (
            not isinstance(data, dict)
            or data.get("schema_version") != CACHE_SCHEMA_VERSION
            or data.get("cache_kind") != CACHE_KIND
            or data.get("namespace") != namespace
            or data.get("key") != key
            or not isinstance(data.get("payload"), dict)
        ):
            return CacheLoad("unsupported", detail="cache record contract is invalid")
        return CacheLoad("hit", value=data["payload"])

    def store(self, namespace: str, key: str, payload: dict[str, Any]) -> Path:
        """Atomically replace one cache record without touching repository files."""

        path = self._path(namespace, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "cache_kind": CACHE_KIND,
            "namespace": namespace,
            "key": key,
            "payload": payload,
        }
        rendered = json.dumps(record, indent=2, sort_keys=True) + "\n"
        if len(rendered.encode("utf-8")) > MAX_CACHE_RECORD_BYTES:
            raise ValueError("source-check cache record exceeds the size limit")
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(rendered)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_name = temporary.name
            os.replace(temporary_name, path)
        finally:
            if temporary_name is not None:
                try:
                    Path(temporary_name).unlink()
                except OSError:
                    pass
        return path

    def prune(self, namespace: str, *, max_records: int) -> tuple[Path, ...]:
        """Remove oldest disposable records after validating the cache boundary."""

        if max_records < 1:
            raise ValueError("source-check cache retention must be positive")
        directory = self._path(namespace, "retention-sentinel").parent
        try:
            candidates = [
                path
                for path in directory.iterdir()
                if path.is_file() and not path.is_symlink() and path.suffix == ".json"
            ]
        except FileNotFoundError:
            return ()
        if len(candidates) <= max_records:
            return ()
        candidates.sort(key=lambda path: (path.stat().st_mtime_ns, path.name))
        removed: list[Path] = []
        for path in candidates[: len(candidates) - max_records]:
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            removed.append(path)
        return tuple(removed)

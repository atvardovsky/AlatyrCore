#!/usr/bin/env python3
"""Store ignored process artifacts once and return compact references."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_file_lock import file_lock


STORE_REL = ".ai/.runtime/store"
BLOBS = "blobs"
INDEX = "index.json"
LOCK = "index.lock"
SCHEMA_VERSION = 1
MAX_BLOB_BYTES = 64 * 1024 * 1024
MAX_INDEX_BYTES = 4 * 1024 * 1024
MAX_ENTRIES = 4096
MAX_SUMMARY = 1000
MAX_KIND = 64
MAX_TASK = 240
MAX_MEDIA_TYPE = 120
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _target(value: str) -> Path:
    target = Path(value).expanduser().resolve()
    if not target.is_dir():
        raise ValueError(f"target is not a directory: {value}")
    return target


def _store(target: Path) -> Path:
    return target / STORE_REL


def _safe_dir(path: Path, *, create: bool) -> None:
    if path.exists() and (path.is_symlink() or not path.is_dir()):
        raise ValueError(f"runtime store directory is unsafe: {path}")
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.is_symlink() or not path.is_dir():
            raise ValueError(f"runtime store directory is unsafe: {path}")


def _safe_file(path: Path, *, missing_ok: bool = False) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        if missing_ok:
            return
        raise
    if path.is_symlink() or not path.is_file() or info.st_nlink != 1:
        raise ValueError(f"runtime store path is not a regular file: {path}")


def _read_bounded(path: Path, limit: int) -> bytes:
    _safe_file(path)
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"runtime source exceeds {limit} bytes")
    return data


def _read_stdin(limit: int) -> bytes:
    data = sys.stdin.buffer.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"runtime stdin exceeds {limit} bytes")
    return data


def _prepare_store(target: Path) -> Path:
    for relative in (".ai", ".ai/.runtime", STORE_REL):
        path = target / relative
        if path.is_symlink():
            raise ValueError(f"runtime store path must not traverse a symlink: {path}")
    store = _store(target)
    _safe_dir(store, create=True)
    _safe_dir(store / BLOBS, create=True)
    return store


def _load_index(store: Path) -> dict[str, Any]:
    path = store / INDEX
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "entries": []}
    raw = _read_bounded(path, MAX_INDEX_BYTES)
    try:
        value = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise ValueError("runtime store index is not valid JSON") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != SCHEMA_VERSION
        or not isinstance(value.get("entries"), list)
    ):
        raise ValueError("runtime store index has an invalid shape")
    if len(value["entries"]) > MAX_ENTRIES:
        raise ValueError("runtime store index exceeds its entry bound")
    return value


def _save_index(store: Path, value: dict[str, Any]) -> None:
    encoded = (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    if len(encoded) > MAX_INDEX_BYTES:
        raise ValueError("runtime store index exceeds its byte bound")
    _safe_dir(store, create=False)
    output = store / INDEX
    _safe_file(output, missing_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".index-", dir=store)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _blob_path(store: Path, digest: str) -> Path:
    return store / BLOBS / digest.removeprefix("sha256:")


def _entry(
    *, digest: str, size: int, kind: str, task: str | None, summary: str | None
) -> dict[str, Any]:
    return {
        "digest": digest,
        "bytes": size,
        "kind": kind,
        "task": task,
        "created_at": _now(),
        "summary": summary,
    }


def put(
    target: Path,
    *,
    kind: str,
    task: str | None,
    summary: str | None,
    data: bytes,
) -> dict[str, Any]:
    kind = kind.strip()
    task = task.strip() if isinstance(task, str) else None
    summary = summary.strip() if isinstance(summary, str) else None
    if not kind or len(kind) > MAX_KIND or any(ord(char) < 32 for char in kind):
        raise ValueError(f"kind must be non-empty and at most {MAX_KIND} characters")
    if task is not None and (
        not task
        or len(task) > MAX_TASK
        or any(ord(char) < 32 for char in task)
    ):
        raise ValueError(f"task must be non-empty and at most {MAX_TASK} characters")
    if summary is not None and (
        len(summary) > MAX_SUMMARY or any(ord(char) < 32 for char in summary)
    ):
        raise ValueError(f"summary must be at most {MAX_SUMMARY} characters")
    if not isinstance(data, bytes) or len(data) > MAX_BLOB_BYTES:
        raise ValueError(f"runtime artifact exceeds {MAX_BLOB_BYTES} bytes")

    store = _prepare_store(target)
    digest_hex = hashlib.sha256(data).hexdigest()
    digest = "sha256:" + digest_hex
    blob = _blob_path(store, digest)
    deduplicated = False
    if blob.exists():
        _safe_file(blob)
        if blob.stat().st_size != len(data):
            raise ValueError("runtime blob exists with a different size")
        deduplicated = True
    else:
        descriptor, temporary = tempfile.mkstemp(prefix=".blob-", dir=store / BLOBS)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, blob)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    with file_lock(store / LOCK):
        index = _load_index(store)
        existing = next(
            (
                item
                for item in index["entries"]
                if item.get("digest") == digest
                and item.get("kind") == kind
                and item.get("task") == task
            ),
            None,
        )
        if existing is None:
            if len(index["entries"]) >= MAX_ENTRIES:
                raise ValueError("runtime store index is at capacity")
            existing = _entry(
                digest=digest,
                size=len(data),
                kind=kind,
                task=task,
                summary=summary,
            )
            index["entries"].append(existing)
            _save_index(store, index)
        elif summary and existing.get("summary") != summary:
            existing["summary"] = summary
            _save_index(store, index)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "runtime-store-put",
        "deduplicated": deduplicated,
        "entry": existing,
        "path": STORE_REL + "/" + BLOBS + "/" + digest_hex,
    }


def index_entries(target: Path, *, task: str | None, kind: str | None, limit: int) -> dict[str, Any]:
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be from 1 to 1000")
    store = _store(target)
    _safe_dir(store, create=False)
    index = _load_index(store)
    entries = [
        item
        for item in index["entries"]
        if (task is None or item.get("task") == task)
        and (kind is None or item.get("kind") == kind)
    ]
    entries.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "runtime-store-index",
        "total": len(index["entries"]),
        "selected": len(entries),
        "entries": entries[:limit],
        "truncated": len(entries) > limit,
    }


def get_bytes(target: Path, digest: str, *, max_bytes: int) -> tuple[bytes, int]:
    if not DIGEST_RE.fullmatch(digest):
        raise ValueError("digest must be sha256:<64 lowercase hex characters>")
    store = _store(target)
    _safe_dir(store, create=False)
    blob = _blob_path(store, digest)
    _safe_file(blob)
    size = blob.stat().st_size
    hasher = hashlib.sha256()
    collected = bytearray()
    with blob.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
            if max_bytes < 0 or len(collected) < max_bytes:
                remaining = (max_bytes - len(collected)) if max_bytes >= 0 else len(chunk)
                collected.extend(chunk[:remaining])
    if "sha256:" + hasher.hexdigest() != digest:
        raise ValueError("runtime blob digest does not match its index identity")
    return bytes(collected), size


def _output_path(target: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError("--output must be target-relative")
    candidate = (target / path).resolve()
    try:
        candidate.relative_to(target)
    except ValueError as exc:
        raise ValueError("--output escapes the target") from exc
    if candidate.is_symlink() or (candidate.exists() and not candidate.is_file()):
        raise ValueError("--output must be a regular file")
    return candidate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", required=True, type=Path)
    actions = parser.add_subparsers(dest="action", required=True)
    put_parser = actions.add_parser("put", allow_abbrev=False)
    put_parser.add_argument("--write", action="store_true")
    put_parser.add_argument("--kind", required=True)
    put_parser.add_argument("--task")
    put_parser.add_argument("--summary")
    source = put_parser.add_mutually_exclusive_group()
    source.add_argument("--file", type=Path)
    source.add_argument("--stdin", action="store_true")
    index_parser = actions.add_parser("index", allow_abbrev=False)
    index_parser.add_argument("--task")
    index_parser.add_argument("--kind")
    index_parser.add_argument("--limit", type=int, default=50)
    get_parser = actions.add_parser("get", allow_abbrev=False)
    get_parser.add_argument("--digest", required=True)
    get_parser.add_argument("--output", type=Path)
    get_parser.add_argument("--max-bytes", type=int, default=65536)
    get_parser.add_argument("--write", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        target = _target(str(args.target))
        if args.action == "put":
            if not args.write:
                raise ValueError("put requires --write")
            if args.file is not None:
                data = _read_bounded(args.file, MAX_BLOB_BYTES)
            elif args.stdin:
                data = _read_stdin(MAX_BLOB_BYTES)
            else:
                data = _read_stdin(MAX_BLOB_BYTES)
            result = put(
                target,
                kind=args.kind,
                task=args.task,
                summary=args.summary,
                data=data,
            )
        elif args.action == "index":
            result = index_entries(
                target,
                task=args.task,
                kind=args.kind,
                limit=args.limit,
            )
        else:
            if args.max_bytes < 0 or args.max_bytes > MAX_BLOB_BYTES:
                raise ValueError(f"--max-bytes must be from 0 to {MAX_BLOB_BYTES}")
            if args.output is not None:
                if not args.write:
                    raise ValueError("get --output requires --write")
                raw, size = get_bytes(target, args.digest, max_bytes=MAX_BLOB_BYTES)
                output = _output_path(target, str(args.output))
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(raw)
                result = {
                    "schema_version": SCHEMA_VERSION,
                    "kind": "runtime-store-get",
                    "digest": args.digest,
                    "bytes": size,
                    "output": str(args.output),
                }
            else:
                raw, size = get_bytes(target, args.digest, max_bytes=args.max_bytes)
                sys.stdout.buffer.write(raw)
                result = None
                if len(raw) < size:
                    print(
                        f"\n[truncated: {len(raw)} of {size} bytes; use --output for the full artifact]",
                        file=sys.stderr,
                    )
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"FAIL: runtime store: {str(exc)[:400]}", file=sys.stderr)
        return 1
    if result is not None:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

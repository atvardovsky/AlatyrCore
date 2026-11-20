#!/usr/bin/env python3
"""Record session-scoped read receipts and answer whether content can be reused."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_file_lock import file_lock
from path_spec import logical_path


STORE_REL = ".ai/.runtime/reads"
INDEX = "index.json"
LOCK = "index.lock"
SCHEMA_VERSION = 1
KIND = "alatyr-read-ledger"
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_LEDGER_BYTES = 4 * 1024 * 1024
MAX_ENTRIES = 4096
MAX_RANGES = 256
MAX_SESSION = 256
MAX_TASK = 240
MAX_SELECTOR = 240
MAX_METADATA_BYTES = 64 * 1024
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
WORD_RE = re.compile(r"\S+")
RETENTION = {"delivered", "compacted", "evicted", "unknown"}
OBSERVATION_SOURCES = {"host-telemetry", "provider-usage", "assistant-reported", "manual"}


class LedgerError(ValueError):
    """Invalid input or unsafe path."""


class LedgerUnavailable(LedgerError):
    """The ledger cannot be read safely; reuse must fall back to delivery."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text(value: Any, label: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise LedgerError(f"{label} must be non-empty and at most {limit} characters")
    if any(ord(char) < 32 for char in value):
        raise LedgerError(f"{label} must not contain control characters")
    return value.strip()


def _target(value: str) -> Path:
    target = Path(value).expanduser().resolve()
    if not target.is_dir():
        raise LedgerError(f"target is not a directory: {value}")
    return target


def _relative_path(target: Path, value: str) -> tuple[Path, str]:
    normalized = unicodedata.normalize("NFC", value.replace("\\", "/"))
    logical = logical_path(normalized)
    path = target / logical
    if path.is_symlink():
        raise LedgerError("path must not be a symlink")
    try:
        resolved = path.resolve()
        resolved.relative_to(target)
    except (OSError, ValueError) as exc:
        raise LedgerError("path escapes the target") from exc
    try:
        info = path.lstat()
    except OSError as exc:
        raise LedgerError(f"path is unavailable: {value}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise LedgerError("path must be a regular file")
    if getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
        raise LedgerError("path must not be a reparse point")
    if info.st_nlink != 1:
        raise LedgerError("path must not be a hardlink")
    return path, logical


def _session_dir(target: Path, session_id: str) -> Path:
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:16]
    return target / STORE_REL / digest


def _safe_dir(path: Path, *, create: bool) -> None:
    if path.is_symlink():
        raise LedgerError(f"ledger directory must not be a symlink: {path}")
    if path.exists():
        info = path.lstat()
        if getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise LedgerError(f"ledger directory must not be a reparse point: {path}")
        if not path.is_dir():
            raise LedgerError(f"ledger path is not a directory: {path}")
        return
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.is_symlink() or not path.is_dir():
            raise LedgerError(f"ledger directory is unsafe: {path}")


def _store_paths(target: Path, session_id: str, *, create: bool) -> tuple[Path, Path, Path]:
    session_dir = _session_dir(target, session_id)
    for path in (target / ".ai", target / ".ai/.runtime", target / STORE_REL, session_dir):
        _safe_dir(path, create=create)
    return session_dir, session_dir / INDEX, session_dir / LOCK


def _default(session_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "session_id": session_id,
        "generation": 0,
        "entries": [],
    }


def _validate_range(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise LedgerUnavailable("ledger range must be an object")
    if set(item) != {"start_line", "end_line", "bytes_sha256", "words"}:
        raise LedgerUnavailable("ledger range has an invalid shape")
    start, end = item.get("start_line"), item.get("end_line")
    if not all(type(value) is int for value in (start, end)) or start < 1 or end < start:
        raise LedgerUnavailable("ledger range bounds are invalid")
    if not isinstance(item.get("bytes_sha256"), str) or not DIGEST_RE.fullmatch(item["bytes_sha256"]):
        raise LedgerUnavailable("ledger range digest is invalid")
    if type(item.get("words")) is not int or item["words"] < 0:
        raise LedgerUnavailable("ledger range word count is invalid")
    return item


def _validate_entry(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise LedgerUnavailable("ledger entry must be an object")
    required = {
        "path", "path_key", "file_id", "file_sha256", "size", "task_id",
        "ranges", "retention", "generation", "delivered_at", "selector", "authority",
    }
    if set(item) != required:
        raise LedgerUnavailable("ledger entry has an invalid shape")
    for field in ("path", "path_key", "task_id", "delivered_at"):
        if not isinstance(item[field], str) or not item[field]:
            raise LedgerUnavailable(f"ledger entry {field} is invalid")
    for field in ("file_id", "file_sha256"):
        if not isinstance(item[field], str) or not DIGEST_RE.fullmatch(item[field]):
            raise LedgerUnavailable(f"ledger entry {field} is invalid")
    if type(item["size"]) is not int or item["size"] < 0:
        raise LedgerUnavailable("ledger entry size is invalid")
    if item["retention"] not in RETENTION:
        raise LedgerUnavailable("ledger entry retention is invalid")
    if type(item["generation"]) is not int or item["generation"] < 0:
        raise LedgerUnavailable("ledger entry generation is invalid")
    if item["selector"] is not None and (
        not isinstance(item["selector"], str) or len(item["selector"]) > MAX_SELECTOR
    ):
        raise LedgerUnavailable("ledger entry selector is invalid")
    if item["authority"] != "none":
        raise LedgerUnavailable("ledger entry must not carry authority")
    ranges = item["ranges"]
    if not isinstance(ranges, list) or len(ranges) > MAX_RANGES:
        raise LedgerUnavailable("ledger entry ranges are invalid")
    _validate_range_set(ranges)
    return item


def _validate_range_set(ranges: list[Any]) -> None:
    previous_end = 0
    for item in ranges:
        value = _validate_range(item)
        if value["start_line"] <= previous_end:
            raise LedgerUnavailable("ledger ranges must be ordered and non-overlapping")
        previous_end = value["end_line"]


def _validate_ledger(value: Any, session_id: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LedgerUnavailable("ledger must contain an object")
    if set(value) != {"schema_version", "kind", "session_id", "generation", "entries"}:
        raise LedgerUnavailable("ledger has an invalid shape")
    if value.get("schema_version") != SCHEMA_VERSION or value.get("kind") != KIND:
        raise LedgerUnavailable("ledger schema or kind is unsupported")
    if value.get("session_id") != session_id:
        raise LedgerUnavailable("ledger session identity does not match")
    if type(value.get("generation")) is not int or value["generation"] < 0:
        raise LedgerUnavailable("ledger generation is invalid")
    entries = value.get("entries")
    if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
        raise LedgerUnavailable("ledger entries are invalid")
    for entry in entries:
        _validate_entry(entry)
    return value


def _load(session_id: str, path: Path) -> dict[str, Any]:
    if not path.exists():
        return _default(session_id)
    if path.is_symlink():
        raise LedgerUnavailable("ledger must not be a symlink")
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise LedgerUnavailable("ledger is unavailable") from exc
    if size > MAX_LEDGER_BYTES:
        raise LedgerUnavailable("ledger exceeds its byte bound")
    try:
        return _validate_ledger(json.loads(path.read_text(encoding="utf-8")), session_id)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, LedgerUnavailable):
            raise
        raise LedgerUnavailable("ledger is not valid JSON") from exc


def _write(path: Path, value: dict[str, Any]) -> None:
    encoded = (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    if len(encoded) > MAX_LEDGER_BYTES:
        raise LedgerUnavailable("ledger exceeds its byte bound")
    if path.is_symlink():
        raise LedgerUnavailable("ledger must not be a symlink")
    _safe_dir(path.parent, create=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".index-", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        for attempt in range(5):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.02)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _file_sha256(path: Path) -> tuple[str, int]:
    hasher = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise LedgerError(f"file exceeds {MAX_FILE_BYTES} bytes")
            hasher.update(chunk)
    return "sha256:" + hasher.hexdigest(), size


def _file_id(path: Path) -> str:
    info = path.stat()
    inode = getattr(info, "st_ino", 0)
    raw = f"{info.st_dev}:{inode}" if inode else os.path.normcase(str(path.resolve()))
    return _digest(raw.encode("utf-8"))


def _read_text(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise LedgerError("file is not readable UTF-8 text") from exc
    if "\x00" in text:
        raise LedgerError("file contains a null byte and is not text")
    return text


def _path_key(value: str) -> str:
    return os.path.normcase(unicodedata.normalize("NFC", value))


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _age_seconds(value: Any) -> float | None:
    stamp = _timestamp(value)
    if stamp is None:
        return None
    return max(0.0, (datetime.now(timezone.utc) - stamp).total_seconds())


def _load_metadata(
    path: Path, session_id: str, required: set[str], label: str
) -> dict[str, Any] | None:
    if not path.exists():
        return None
    if path.is_symlink():
        raise LedgerUnavailable(f"{label} must not be a symlink")
    try:
        if path.stat().st_size > MAX_METADATA_BYTES:
            raise LedgerUnavailable(f"{label} exceeds its byte bound")
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, LedgerUnavailable):
            raise
        raise LedgerUnavailable(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict) or set(value) != required:
        raise LedgerUnavailable(f"{label} has an invalid shape")
    if value.get("schema_version") != 1 or value.get("session_id") != session_id:
        raise LedgerUnavailable(f"{label} identity is invalid")
    return value


def _load_epoch(session_dir: Path, session_id: str) -> dict[str, Any] | None:
    value = _load_metadata(
        session_dir / "epoch.json",
        session_id,
        {"schema_version", "session_id", "epoch", "event", "source", "observed_at"},
        "epoch",
    )
    if value is None:
        return None
    if type(value["epoch"]) is not int or value["epoch"] < 0:
        raise LedgerUnavailable("epoch number is invalid")
    for field in ("event", "source", "observed_at"):
        if not isinstance(value[field], str) or not value[field]:
            raise LedgerUnavailable(f"epoch {field} is invalid")
    return value


def _write_epoch(
    session_dir: Path, session_id: str, epoch: int, source: str, event: str
) -> dict[str, Any]:
    value = {
        "schema_version": 1,
        "session_id": session_id,
        "epoch": epoch,
        "event": event,
        "source": source,
        "observed_at": _now(),
    }
    _write(session_dir / "epoch.json", value)
    return value


def _load_observations(session_dir: Path, session_id: str) -> dict[str, Any] | None:
    value = _load_metadata(
        session_dir / "observations.json",
        session_id,
        {
            "schema_version", "session_id", "high_water_tokens", "last_tokens",
            "window", "source", "observed_at", "suspected_compaction", "generation",
        },
        "observations",
    )
    if value is None:
        return None
    for field in ("high_water_tokens", "last_tokens", "window", "generation"):
        if type(value[field]) is not int or value[field] < 0:
            raise LedgerUnavailable(f"observations {field} is invalid")
    if type(value["suspected_compaction"]) is not bool:
        raise LedgerUnavailable("observations suspected_compaction is invalid")
    if value["source"] not in OBSERVATION_SOURCES:
        raise LedgerUnavailable("observations source is invalid")
    return value


def _write_observations(
    session_dir: Path,
    session_id: str,
    *,
    high_water: int,
    last: int,
    window: int,
    source: str,
    generation: int,
    suspected: bool,
) -> dict[str, Any]:
    value = {
        "schema_version": 1,
        "session_id": session_id,
        "high_water_tokens": high_water,
        "last_tokens": last,
        "window": window,
        "source": source,
        "observed_at": _now(),
        "suspected_compaction": suspected,
        "generation": generation,
    }
    _write(session_dir / "observations.json", value)
    return value


def _adopt_epoch(ledger: dict[str, Any], epoch: dict[str, Any] | None) -> bool:
    if epoch is None or epoch["epoch"] <= ledger["generation"]:
        return False
    ledger["generation"] = epoch["epoch"]
    for entry in ledger["entries"]:
        entry["retention"] = "compacted"
    return True


def _range(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"\s*(\d+)\s*[:\-]\s*(\d+)\s*", value)
    if not match:
        raise LedgerError("--range must be START:END with 1-based inclusive integers")
    start, end = int(match.group(1)), int(match.group(2))
    if start < 1 or end < start:
        raise LedgerError("--range requires 1 <= START <= END")
    return start, end


def _lines(text: str) -> int:
    return len(text.splitlines())


def _slice(text: str, start: int, end: int) -> str:
    lines = text.splitlines(keepends=True)
    return "".join(lines[start - 1:end])


def _words(text: str) -> int:
    return len(WORD_RE.findall(text))


def _merge(ranges: list[dict[str, Any]]) -> list[tuple[int, int]]:
    intervals: list[tuple[int, int]] = []
    for item in sorted(ranges, key=lambda row: row["start_line"]):
        start, end = item["start_line"], item["end_line"]
        if intervals and start <= intervals[-1][1] + 1:
            intervals[-1] = (intervals[-1][0], max(intervals[-1][1], end))
        else:
            intervals.append((start, end))
    return intervals


def _coverage(ranges: list[dict[str, Any]], start: int, end: int) -> tuple[list[list[int]], list[list[int]]]:
    covered: list[list[int]] = []
    missing: list[list[int]] = []
    cursor = start
    for region_start, region_end in _merge(ranges):
        if region_end < start or region_start > end:
            continue
        covered.append([max(start, region_start), min(end, region_end)])
        if region_start > cursor:
            missing.append([cursor, min(region_start - 1, end)])
        cursor = max(cursor, region_end + 1)
        if cursor > end:
            break
    if cursor <= end:
        missing.append([cursor, end])
    return covered, [item for item in missing if item[0] <= item[1]]


def _find(ledger: dict[str, Any], path_key: str, file_id: str, task_id: str) -> dict[str, Any] | None:
    for entry in ledger["entries"]:
        if entry["task_id"] == task_id and (
            entry["path_key"] == path_key or entry["file_id"] == file_id
        ):
            return entry
    return None


def _new_entry(
    *, path: str, path_key: str, file_id: str, digest: str, size: int,
    task_id: str, selector: str | None, generation: int,
) -> dict[str, Any]:
    return {
        "path": path,
        "path_key": path_key,
        "file_id": file_id,
        "file_sha256": digest,
        "size": size,
        "task_id": task_id,
        "ranges": [],
        "retention": "delivered",
        "generation": generation,
        "delivered_at": _now(),
        "selector": selector,
        "authority": "none",
    }


def _rebuild_ranges(text: str, intervals: list[tuple[int, int]]) -> list[dict[str, Any]]:
    result = []
    for start, end in intervals[:MAX_RANGES]:
        content = _slice(text, start, end)
        result.append(
            {
                "start_line": start,
                "end_line": end,
                "bytes_sha256": _digest(content.encode("utf-8")),
                "words": _words(content),
            }
        )
    return result


def _prune(ledger: dict[str, Any], max_entries: int = MAX_ENTRIES) -> int:
    removed = 0
    entries = ledger["entries"]
    if len(entries) > max_entries:
        entries.sort(key=lambda entry: (entry["retention"] != "compacted", entry["delivered_at"]))
        removed = len(entries) - max_entries
        ledger["entries"] = entries[removed:]
    for entry in ledger["entries"]:
        if len(entry["ranges"]) > MAX_RANGES:
            entry["ranges"] = entry["ranges"][-MAX_RANGES:]
    return removed


def check_delivery(
    target: Path,
    *,
    session_id: str,
    task_id: str,
    relpath: str,
    start: int | None = None,
    end: int | None = None,
    full: bool = False,
    max_age_seconds: int = 1800,
) -> dict[str, Any]:
    session_id = _text(session_id, "session", MAX_SESSION)
    task_id = _text(task_id, "task", MAX_TASK)
    if type(max_age_seconds) is not int or max_age_seconds < 0:
        raise LedgerError("--max-age-seconds must be a non-negative integer")
    path, logical = _relative_path(target, relpath)
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise LedgerError("path is unavailable") from exc
    if size > MAX_FILE_BYTES:
        return _decision("too-large", logical, task_id, reusable=False, size=size)
    text = _read_text(path)
    total = _lines(text)
    if total == 0:
        return _decision("unsafe", logical, task_id, reusable=False, total_lines=0)
    if full:
        start, end = 1, total
    if start is None or end is None:
        raise LedgerError("range or full selection is required")
    if start < 1 or end < start or end > total:
        raise LedgerError(f"range must be within 1..{total}")
    digest, size = _file_sha256(path)
    file_id = _file_id(path)
    session_dir, index, _ = _store_paths(target, session_id, create=False)
    try:
        epoch = _load_epoch(session_dir, session_id)
    except LedgerUnavailable as exc:
        return _decision(
            "redeliver", logical, task_id, reusable=False,
            reason="epoch-invalid", epoch_error=str(exc),
            file_sha256=digest, total_lines=total,
        )
    try:
        ledger = _load(session_id, index)
    except LedgerUnavailable as exc:
        return _decision(
            "unavailable", logical, task_id, reusable=False,
            reason=str(exc), file_sha256=digest, total_lines=total,
        )
    if epoch is not None and epoch["epoch"] > ledger["generation"]:
        return _decision(
            "redeliver", logical, task_id, reusable=False,
            reason="host-epoch-advanced", epoch=epoch["epoch"],
            file_sha256=digest, total_lines=total,
            generation=ledger["generation"],
        )
    entry = _find(ledger, _path_key(logical), file_id, task_id)
    if entry is None:
        return _decision(
            "miss", logical, task_id, reusable=False,
            file_sha256=digest, total_lines=total, generation=ledger["generation"],
        )
    if entry["file_sha256"] != digest:
        return _decision(
            "changed", logical, task_id, reusable=False,
            file_sha256=digest, previous_sha256=entry["file_sha256"],
            total_lines=total, generation=ledger["generation"],
        )
    if entry["retention"] != "delivered" or entry["generation"] != ledger["generation"]:
        return _decision(
            "redeliver", logical, task_id, reusable=False,
            reason="compacted-or-generation-changed",
            file_sha256=digest, retention=entry["retention"],
            total_lines=total, generation=ledger["generation"],
        )
    if max_age_seconds > 0:
        age = _age_seconds(entry["delivered_at"])
        if age is None:
            return _decision(
                "redeliver", logical, task_id, reusable=False,
                reason="receipt-timestamp-invalid",
                file_sha256=digest, total_lines=total,
                generation=ledger["generation"],
            )
        if age > max_age_seconds:
            return _decision(
                "redeliver", logical, task_id, reusable=False,
                reason="receipt-expired", age_seconds=round(age, 1),
                max_age_seconds=max_age_seconds,
                file_sha256=digest, total_lines=total,
                generation=ledger["generation"],
            )
    covered, missing = _coverage(entry["ranges"], start, end)
    state = "partial" if missing else "reused"
    return _decision(
        state, logical, task_id, reusable=not missing,
        file_sha256=digest, retention=entry["retention"],
        covered_ranges=covered, missing_ranges=missing,
        total_lines=total, generation=ledger["generation"],
        max_age_seconds=max_age_seconds,
        entry=_public_entry(entry),
    )


def _public_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "selector": entry["selector"],
        "retention": entry["retention"],
        "generation": entry["generation"],
        "ranges": entry["ranges"],
        "authority": entry["authority"],
    }


def _decision(state: str, path: str, task_id: str, *, reusable: bool, **fields: Any) -> dict[str, Any]:
    result = {
        "schema_version": SCHEMA_VERSION,
        "kind": "read-ledger-check",
        "state": state,
        "path": path,
        "task_id": task_id,
        "reusable": reusable,
        "authority": "none",
        "authority_granted": False,
    }
    result.update(fields)
    return result


def record_delivery(
    target: Path,
    *,
    session_id: str,
    task_id: str,
    relpath: str,
    start: int | None = None,
    end: int | None = None,
    full: bool = False,
    selector: str | None = None,
    words: int | None = None,
) -> dict[str, Any]:
    session_id = _text(session_id, "session", MAX_SESSION)
    task_id = _text(task_id, "task", MAX_TASK)
    if selector is not None:
        selector = _text(selector, "selector", MAX_SELECTOR)
    path, logical = _relative_path(target, relpath)
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise LedgerError("path is unavailable") from exc
    if size > MAX_FILE_BYTES:
        raise LedgerError(f"file exceeds {MAX_FILE_BYTES} bytes")
    text = _read_text(path)
    total = _lines(text)
    if total == 0:
        raise LedgerError("empty files are not recorded")
    if full:
        start, end = 1, total
    if start is None or end is None:
        raise LedgerError("range or full selection is required")
    if start < 1 or end < start or end > total:
        raise LedgerError(f"range must be within 1..{total}")
    if words is not None and (type(words) is not int or words < 0):
        raise LedgerError("words must be a non-negative integer")
    digest, size = _file_sha256(path)
    file_id = _file_id(path)
    session_dir, index, lock = _store_paths(target, session_id, create=True)
    with file_lock(lock):
        ledger = _load(session_id, index)
        _adopt_epoch(ledger, _load_epoch(session_dir, session_id))
        entry = _find(ledger, _path_key(logical), file_id, task_id)
        if entry is None:
            entry = _new_entry(
                path=logical, path_key=_path_key(logical), file_id=file_id,
                digest=digest, size=size, task_id=task_id, selector=selector,
                generation=ledger["generation"],
            )
            ledger["entries"].append(entry)
        elif entry["file_sha256"] != digest:
            entry["ranges"] = []
            entry["file_sha256"] = digest
            entry["size"] = size
        entry["path"] = logical
        entry["path_key"] = _path_key(logical)
        entry["file_id"] = file_id
        entry["selector"] = selector
        entry["retention"] = "delivered"
        entry["generation"] = ledger["generation"]
        entry["delivered_at"] = _now()
        entry["ranges"] = _rebuild_ranges(
            text, _merge([*entry["ranges"], {"start_line": start, "end_line": end}])
        )
        if words is not None and len(entry["ranges"]) == 1:
            entry["ranges"][0]["words"] = words
        _prune(ledger)
        _write(index, ledger)
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": "read-ledger-record",
            "state": "recorded",
            "path": logical,
            "task_id": task_id,
            "generation": ledger["generation"],
            "entry": _public_entry(entry),
            "authority": "none",
            "authority_granted": False,
        }


def compact_session(target: Path, *, session_id: str) -> dict[str, Any]:
    session_id = _text(session_id, "session", MAX_SESSION)
    session_dir, index, lock = _store_paths(target, session_id, create=True)
    with file_lock(lock):
        ledger = _load(session_id, index)
        try:
            epoch = _load_epoch(session_dir, session_id)
        except LedgerUnavailable:
            epoch = None
        generation = ledger["generation"] + 1
        if epoch is not None and epoch["epoch"] > generation:
            generation = epoch["epoch"]
        ledger["generation"] = generation
        for entry in ledger["entries"]:
            entry["retention"] = "compacted"
        _write(index, ledger)
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": "read-ledger-compact",
            "state": "compacted",
            "session_id": session_id,
            "generation": ledger["generation"],
            "epoch": epoch["epoch"] if epoch is not None else None,
            "entries": len(ledger["entries"]),
            "authority_granted": False,
        }


def status_session(target: Path, *, session_id: str) -> dict[str, Any]:
    session_id = _text(session_id, "session", MAX_SESSION)
    session_dir, index, _ = _store_paths(target, session_id, create=False)
    try:
        ledger = _load(session_id, index)
    except LedgerUnavailable as exc:
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": "read-ledger-status",
            "state": "unavailable",
            "session_id": session_id,
            "reason": str(exc),
            "authority_granted": False,
        }
    tasks: dict[str, int] = {}
    retention = {name: 0 for name in sorted(RETENTION)}
    delivered_words = 0
    ranges = 0
    for entry in ledger["entries"]:
        tasks[entry["task_id"]] = tasks.get(entry["task_id"], 0) + 1
        retention[entry["retention"]] = retention.get(entry["retention"], 0) + 1
        ranges += len(entry["ranges"])
        if entry["retention"] == "delivered":
            delivered_words += sum(item["words"] for item in entry["ranges"])
    try:
        epoch = _load_epoch(session_dir, session_id)
        epoch_state = "current" if epoch is not None else "absent"
    except LedgerUnavailable:
        epoch = None
        epoch_state = "invalid"
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "read-ledger-status",
        "state": "current",
        "session_id": session_id,
        "generation": ledger["generation"],
        "epoch": epoch["epoch"] if epoch is not None else None,
        "epoch_source": epoch["source"] if epoch is not None else None,
        "epoch_state": epoch_state,
        "compaction_pending": (
            epoch is not None and epoch["epoch"] > ledger["generation"]
        ),
        "entries": len(ledger["entries"]),
        "tasks": tasks,
        "ranges": ranges,
        "delivered_words": delivered_words,
        "retention": retention,
        "authority": "none",
        "authority_granted": False,
    }


def epoch_session(
    target: Path, *, session_id: str, epoch: int, source: str, event: str
) -> dict[str, Any]:
    session_id = _text(session_id, "session", MAX_SESSION)
    if type(epoch) is not int or epoch < 0:
        raise LedgerError("--epoch must be a non-negative integer")
    source = _text(source, "source", 64)
    event = _text(event, "event", 64)
    session_dir, index, lock = _store_paths(target, session_id, create=True)
    with file_lock(lock):
        ledger = _load(session_id, index)
        if epoch > ledger["generation"]:
            ledger["generation"] = epoch
            for entry in ledger["entries"]:
                entry["retention"] = "compacted"
            _write(index, ledger)
        record = _write_epoch(session_dir, session_id, epoch, source, event)
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": "read-ledger-epoch",
            "state": "recorded",
            "session_id": session_id,
            "epoch": record["epoch"],
            "source": record["source"],
            "event": record["event"],
            "generation": ledger["generation"],
            "authority_granted": False,
        }


def observe_session(
    target: Path,
    *,
    session_id: str,
    tokens_used: int,
    window: int,
    source: str,
    drop_threshold: float = 0.3,
) -> dict[str, Any]:
    session_id = _text(session_id, "session", MAX_SESSION)
    if type(tokens_used) is not int or tokens_used < 0:
        raise LedgerError("--tokens-used must be a non-negative integer")
    if type(window) is not int or window <= 0:
        raise LedgerError("--window must be a positive integer")
    if source not in OBSERVATION_SOURCES:
        raise LedgerError(f"--source must be one of {sorted(OBSERVATION_SOURCES)}")
    if (
        isinstance(drop_threshold, bool)
        or not isinstance(drop_threshold, (int, float))
        or not 0 < float(drop_threshold) < 1
    ):
        raise LedgerError("--drop-threshold must be greater than 0 and less than 1")
    threshold = float(drop_threshold)
    session_dir, index, lock = _store_paths(target, session_id, create=True)
    with file_lock(lock):
        ledger = _load(session_id, index)
        adopted = _adopt_epoch(ledger, _load_epoch(session_dir, session_id))
        observations = _load_observations(session_dir, session_id)
        if observations is None or adopted or observations["generation"] != ledger["generation"]:
            high_water = tokens_used
        else:
            high_water = max(observations["high_water_tokens"], tokens_used)
        suspected = False
        if (
            high_water > 0
            and tokens_used <= high_water * (1 - threshold)
            and source == "host-telemetry"
        ):
            ledger["generation"] += 1
            for entry in ledger["entries"]:
                entry["retention"] = "compacted"
            high_water = tokens_used
            suspected = True
            _write(index, ledger)
        elif adopted:
            _write(index, ledger)
        _write_observations(
            session_dir,
            session_id,
            high_water=high_water,
            last=tokens_used,
            window=window,
            source=source,
            generation=ledger["generation"],
            suspected=suspected,
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": "read-ledger-observe",
            "state": "suspected-compaction" if suspected else "observed",
            "session_id": session_id,
            "generation": ledger["generation"],
            "high_water_tokens": high_water,
            "last_tokens": tokens_used,
            "window": window,
            "source": source,
            "suspected_compaction": suspected,
            "authority_granted": False,
        }


def prune_session(target: Path, *, session_id: str, max_entries: int) -> dict[str, Any]:
    session_id = _text(session_id, "session", MAX_SESSION)
    if type(max_entries) is not int or max_entries < 1 or max_entries > MAX_ENTRIES:
        raise LedgerError(f"--max-entries must be from 1 to {MAX_ENTRIES}")
    session_dir, index, lock = _store_paths(target, session_id, create=True)
    with file_lock(lock):
        ledger = _load(session_id, index)
        removed = _prune(ledger, max_entries)
        _write(index, ledger)
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": "read-ledger-prune",
            "state": "pruned",
            "session_id": session_id,
            "removed": removed,
            "entries": len(ledger["entries"]),
            "authority_granted": False,
        }


def reset_session(target: Path, *, session_id: str, write: bool) -> dict[str, Any]:
    session_id = _text(session_id, "session", MAX_SESSION)
    if not write:
        raise LedgerError("reset requires --write")
    session_dir, index, lock = _store_paths(target, session_id, create=True)
    with file_lock(lock):
        existed = index.exists()
        if existed:
            index.unlink()
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": "read-ledger-reset",
            "state": "reset",
            "session_id": session_id,
            "removed": existed,
            "authority_granted": False,
        }


def _add_selection(parser: argparse.ArgumentParser) -> None:
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--range", dest="range_value")
    selection.add_argument("--full", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", required=True, type=Path)
    actions = parser.add_subparsers(dest="action", required=True)
    check = actions.add_parser("check", allow_abbrev=False)
    check.add_argument("--session", required=True)
    check.add_argument("--task", required=True)
    check.add_argument("--path", required=True)
    _add_selection(check)
    check.add_argument("--max-age-seconds", type=int, default=1800)
    record = actions.add_parser("record", allow_abbrev=False)
    record.add_argument("--session", required=True)
    record.add_argument("--task", required=True)
    record.add_argument("--path", required=True)
    _add_selection(record)
    record.add_argument("--selector")
    record.add_argument("--words", type=int)
    compact = actions.add_parser("compact", allow_abbrev=False)
    compact.add_argument("--session", required=True)
    epoch = actions.add_parser("epoch", allow_abbrev=False)
    epoch.add_argument("--session", required=True)
    epoch.add_argument("--epoch", type=int, required=True)
    epoch.add_argument("--source", default="host-hook")
    epoch.add_argument("--event", default="compaction")
    observe = actions.add_parser("observe", allow_abbrev=False)
    observe.add_argument("--session", required=True)
    observe.add_argument("--tokens-used", type=int, required=True)
    observe.add_argument("--window", type=int, required=True)
    observe.add_argument("--source", default="host-telemetry")
    observe.add_argument("--drop-threshold", type=float, default=0.3)
    status = actions.add_parser("status", allow_abbrev=False)
    status.add_argument("--session", required=True)
    prune = actions.add_parser("prune", allow_abbrev=False)
    prune.add_argument("--session", required=True)
    prune.add_argument("--max-entries", type=int, default=MAX_ENTRIES)
    reset = actions.add_parser("reset", allow_abbrev=False)
    reset.add_argument("--session", required=True)
    reset.add_argument("--write", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        target = _target(str(args.target))
        if args.action == "check":
            start = end = None
            if args.range_value is not None:
                start, end = _range(args.range_value)
            result = check_delivery(
                target, session_id=args.session, task_id=args.task,
                relpath=args.path, start=start, end=end, full=args.full,
                max_age_seconds=args.max_age_seconds,
            )
        elif args.action == "record":
            start = end = None
            if args.range_value is not None:
                start, end = _range(args.range_value)
            result = record_delivery(
                target, session_id=args.session, task_id=args.task,
                relpath=args.path, start=start, end=end, full=args.full,
                selector=args.selector, words=args.words,
            )
        elif args.action == "compact":
            result = compact_session(target, session_id=args.session)
        elif args.action == "epoch":
            result = epoch_session(
                target, session_id=args.session, epoch=args.epoch,
                source=args.source, event=args.event,
            )
        elif args.action == "observe":
            result = observe_session(
                target, session_id=args.session, tokens_used=args.tokens_used,
                window=args.window, source=args.source,
                drop_threshold=args.drop_threshold,
            )
        elif args.action == "status":
            result = status_session(target, session_id=args.session)
        elif args.action == "prune":
            result = prune_session(target, session_id=args.session, max_entries=args.max_entries)
        else:
            result = reset_session(target, session_id=args.session, write=args.write)
    except LedgerUnavailable as exc:
        print(f"FAIL: read ledger unavailable: {exc}", file=sys.stderr)
        return 1
    except (OSError, LedgerError, ValueError) as exc:
        print(f"FAIL: read ledger: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

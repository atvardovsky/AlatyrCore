"""Shared literal source bindings and review deadlines for project knowledge."""

from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import PurePosixPath, PureWindowsPath
from typing import Callable


MAX_SOURCE_BINDINGS = 32
SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")


def source_path(value: object) -> str:
    if (not isinstance(value, str) or not value or "\0" in value or "\\" in value
            or value.strip().casefold() in {"unknown", "unresolved", "pending", "not-applicable", "none"}
            or "{" in value or "}" in value
            or PureWindowsPath(value).drive or PurePosixPath(value).is_absolute()
            or PurePosixPath(value).as_posix() != value
            or any(part in {".", ".."} for part in value.split("/"))):
        raise ValueError("knowledge source must be a normalized target-relative file path")
    return value


def source_bindings(triggers: object, read: Callable[[str], bytes] | None = None,
                    *, verify: bool = True) -> dict[str, str]:
    if not isinstance(triggers, list):
        raise ValueError("knowledge freshness triggers must be an array")
    bindings: dict[str, str] = {}
    for trigger in triggers:
        if not isinstance(trigger, dict):
            raise ValueError("knowledge freshness trigger must be an object")
        if trigger.get("kind") != "source-sha256":
            continue
        path = source_path(trigger.get("subject"))
        expected = trigger.get("expected")
        if not isinstance(expected, str) or not SHA256.fullmatch(expected):
            raise ValueError(f"knowledge source {path} requires a resolved SHA-256")
        if path in bindings:
            raise ValueError(f"knowledge source binding is repeated: {path}")
        if len(bindings) >= MAX_SOURCE_BINDINGS:
            raise ValueError(f"knowledge item exceeds {MAX_SOURCE_BINDINGS} source bindings")
        bindings[path] = expected.lower()
        if read is not None:
            raw = read(path)
            if not isinstance(raw, bytes):
                raise ValueError(f"knowledge source {path} did not produce bytes")
            if verify and hashlib.sha256(raw).hexdigest() != bindings[path]:
                raise ValueError(f"knowledge source {path} changed; revalidation required")
    return bindings


def review_deadlines(triggers: object) -> list[str]:
    if not isinstance(triggers, list):
        raise ValueError("knowledge freshness triggers must be an array")
    deadlines = []
    for trigger in triggers:
        if not isinstance(trigger, dict):
            raise ValueError("knowledge freshness trigger must be an object")
        if trigger.get("kind") == "review-expiry":
            value = trigger.get("expected")
            if not isinstance(value, str):
                raise ValueError("knowledge review expiry requires an ISO date")
            try:
                parsed = date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("knowledge review expiry requires an ISO date") from exc
            if parsed.isoformat() != value:
                raise ValueError("knowledge review expiry requires YYYY-MM-DD")
            deadlines.append(value)
    return sorted(set(deadlines))

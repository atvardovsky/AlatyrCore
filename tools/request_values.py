"""Shared bounded request values; no delivery or lifecycle dependencies."""

from __future__ import annotations

import re

from inspect_session_context import relative_path

MAX_ROWS = 32
WINDOWS_DEVICES = frozenset({"con", "prn", "aux", "nul", "conin$", "conout$",
                            *[f"{prefix}{number}" for prefix in ("com", "lpt") for number in range(1, 10)]})


def text(value: object, label: str, limit: int = 1024) -> str:
    if (not isinstance(value, str) or not value.strip() or len(value) > limit
            or any(ord(char) < 32 for char in value)
            or value.casefold() in {"unknown", "none", "unresolved"}
            or re.search(r"\{[A-Z][A-Z0-9_]*\}", value)):
        raise ValueError(f"{label} requires bounded resolved text")
    return value


def strings(value: object, label: str, *, minimum: int = 0) -> list[str]:
    if not isinstance(value, list) or not minimum <= len(value) <= MAX_ROWS:
        raise ValueError(f"{label} requires {minimum}..{MAX_ROWS} entries")
    result = [text(item, label) for item in value]
    if len(set(result)) != len(result):
        raise ValueError(f"{label} cannot contain duplicates")
    return result


def fields(value: object, required: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError(f"{label} requires exact fields: {', '.join(sorted(required))}")
    return value


def request_path(value: object) -> str:
    path = relative_path(text(value, "request path"))
    for part in path.split("/"):
        device = part.split(".")[0].rstrip(" ").casefold().translate(str.maketrans({"\u00b9": "1", "\u00b2": "2", "\u00b3": "3"}))
        if (part.endswith((" ", ".")) or any(char in part for char in '*?[]:<>|"')
                or device in WINDOWS_DEVICES):
            raise ValueError("request paths must be portable literal paths without device, alias or stream names")
    return path

"""Shared value-shape helpers for target-adapter validation."""

from __future__ import annotations

from typing import Any

from target_validation_support import is_placeholder, is_unresolved_value


def is_resolved_string(value: Any, *, reject_or_marker: bool = False) -> bool:
    """Return whether a value is a non-placeholder target string claim."""

    return (
        isinstance(value, str)
        and bool(value.strip())
        and not is_placeholder(value)
        and not is_unresolved_value(value)
        and (not reject_or_marker or "_OR_" not in value)
    )


def string_list_value(
    value: Any, *, non_empty: bool = True, resolved: bool = False
) -> list[str] | None:
    """Return a valid string list or None without emitting diagnostics."""

    if not isinstance(value, list) or (non_empty and not value):
        return None
    for item in value:
        if not isinstance(item, str) or not item:
            return None
        if resolved and not is_resolved_string(item):
            return None
    return value


def is_string_list(
    value: Any, *, non_empty: bool = True, resolved: bool = False
) -> bool:
    return string_list_value(value, non_empty=non_empty, resolved=resolved) is not None

"""Resolve mode-specific architecture context without interpreting prose."""

from typing import Any


MODES = ("inventory", "explain", "discuss", "compare", "review", "document")


def architecture_context(descriptor: dict[str, Any], mode: str | None = None) -> list[str]:
    if not isinstance(descriptor, dict) or descriptor.get("intent") != "architecture-request":
        raise ValueError("architecture intent descriptor is required")
    if mode is not None and (not isinstance(mode, str) or mode not in MODES):
        raise ValueError("unknown architecture mode")
    required = descriptor.get("required_context")
    modes = descriptor.get("mode_context")
    if not isinstance(required, list) or not all(isinstance(p, str) and p for p in required):
        raise ValueError("architecture required_context must contain paths")
    shared = {".ai/framework/architecture-knowledge.md", ".ai/project/architecture/catalog.json", ".ai/assistant/flows/architecture-assistance.flow.md"}
    if not shared.issubset(required):
        raise ValueError("architecture shared owner, catalog, and flow must remain required")
    if modes is None and mode is None:
        return list(required)
    if not isinstance(modes, dict) or set(modes) != set(MODES):
        raise ValueError("architecture mode_context must define all six modes")
    if any(not isinstance(paths, list) or not all(isinstance(p, str) and p for p in paths)
           for paths in modes.values()):
        raise ValueError("architecture mode context must contain path lists")
    selected = modes[mode] if mode is not None else [p for paths in modes.values() for p in paths]
    return list(dict.fromkeys([*required, *selected]))

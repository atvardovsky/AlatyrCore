"""Resolve explicit registry paths without interpreting decision-owner names."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from path_spec import PathSpec, logical_path


@dataclass(frozen=True)
class OwnerDeclaration:
    raw: str
    line: int


def owner_declarations(block: str, first_line: int) -> tuple[OwnerDeclaration, ...]:
    result = []
    for match in re.finditer(r"^Canonical owner:[ \t]*([^\n]*)$", block, re.MULTILINE | re.IGNORECASE):
        raw = match.group(1).strip()
        following = block[match.end():].splitlines()
        if len(following) > 1 and following[1].startswith((" ", "\t")):
            raw += " [unsupported continuation]"
        result.append(OwnerDeclaration(raw, first_line + block.count("\n", 0, match.start())))
    return tuple(result)


def owner_paths(raw: str) -> tuple[str, ...]:
    """Accept explicit Markdown path tokens, or one unquoted logical path."""
    token = re.compile(r"`([^`]+)`|\[[^\]\n]*\]\(([^)\n]+)\)")
    matches = list(token.finditer(raw))
    if matches:
        rest = token.sub("", raw)
        if rest.strip(" ,;\t") or raw.endswith((",", ";")):
            raise ValueError("use individually quoted paths or Markdown links, separated by commas or semicolons")
        values = [(match.group(1) or match.group(2)).removeprefix("<").removesuffix(">") for match in matches]
    else:
        if any(c.isspace() for c in raw) or "," in raw or ";" in raw:
            raise ValueError("ambiguous owner declaration; quote each repository path separately")
        values = [raw]
    for value in values:
        path, _, section = value.partition("#")
        logical_path(path.rstrip("/"), pattern=True)
        if "#" in value and not section:
            raise ValueError("owner section must be non-empty")
        if any(c in path for c in "*?["):
            PathSpec(path)
        if section and (path.endswith("/") or any(c in path for c in "*?")):
            raise ValueError("decision sections require an exact file")
    return tuple(values)


def owner_binding_matches(owner: str, binding: Any) -> bool:
    if not isinstance(binding, dict) or binding.get("authority") != "canonical":
        return False
    path, _, section = owner.partition("#")
    if section:
        return binding.get("path") == path and binding.get("selector_kind") == "markdown-section" and binding.get("selector") == section
    if path.endswith("/"):
        return binding.get("selector_kind") == "glob" and binding.get("path") == path + "**"
    if any(c in path for c in "*?") or "[" in path and binding.get("selector_kind") == "glob":
        return binding.get("selector_kind") == "glob" and binding.get("path") == path
    if binding.get("path") != path:
        return False
    return binding.get("selector_kind") == "file" and binding.get("selector") == "whole-file"


def ownership_failures(declarations: tuple[OwnerDeclaration, ...], node: dict[str, Any]) -> list[tuple[int, str]]:
    failures = [] if declarations else [(0, "registry fact needs an explicit Canonical owner declaration; coverage is unavailable")]
    for declaration in declarations:
        try:
            paths = owner_paths(declaration.raw)
        except ValueError as exc:
            failures.append((declaration.line, str(exc)))
            continue
        bindings = node.get("bindings", [])
        if not isinstance(bindings, list):
            bindings = []
        for path in paths:
            if not any(owner_binding_matches(path, binding) for binding in bindings):
                failures.append((declaration.line, f"canonical owner {path!r} needs a declaration-equivalent canonical binding on this fact node"))
    return failures

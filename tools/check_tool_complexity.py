#!/usr/bin/env python3
"""Guard AlatyrCore source tooling against unbounded large-function growth."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "tools" / "tool_complexity_allowlist.json"


def load_allowlist() -> tuple[int, dict[tuple[str, str], dict[str, Any]]]:
    data = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("allowlist_kind") != (
        "alatyr-source-tool-complexity-allowlist"
    ):
        raise ValueError("tool complexity allowlist has invalid contract")
    threshold = data.get("max_function_lines")
    if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold <= 0:
        raise ValueError("max_function_lines must be a positive integer")
    allowlist: dict[tuple[str, str], dict[str, Any]] = {}
    entries = data.get("known_large_functions")
    if not isinstance(entries, list):
        raise ValueError("known_large_functions must be a list")
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"known_large_functions[{index}] must be an object")
        path = entry.get("path")
        qualname = entry.get("qualname")
        max_lines = entry.get("max_lines")
        reason = entry.get("reason")
        if (
            not isinstance(path, str)
            or not path.startswith("tools/")
            or not isinstance(qualname, str)
            or not qualname
            or not isinstance(max_lines, int)
            or isinstance(max_lines, bool)
            or max_lines <= threshold
            or not isinstance(reason, str)
            or not reason
        ):
            raise ValueError(f"known_large_functions[{index}] is invalid")
        key = (path, qualname)
        if key in allowlist:
            raise ValueError(f"duplicate allowlisted function: {path}:{qualname}")
        allowlist[key] = entry
    return threshold, allowlist


def iter_functions(tree: ast.AST) -> Iterable[tuple[str, ast.AST]]:
    stack: list[str] = []

    def visit(node: ast.AST) -> Iterable[tuple[str, ast.AST]]:
        if isinstance(node, ast.ClassDef):
            stack.append(node.name)
            for child in node.body:
                yield from visit(child)
            stack.pop()
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            stack.append(node.name)
            yield ".".join(stack), node
            for child in node.body:
                yield from visit(child)
            stack.pop()

    for child in getattr(tree, "body", []):
        yield from visit(child)


def python_paths() -> list[Path]:
    return sorted(
        path
        for path in (ROOT / "tools").rglob("*.py")
        if path.name != "__init__.py" and "__pycache__" not in path.parts
    )


def main() -> int:
    failures: list[str] = []
    try:
        threshold, allowlist = load_allowlist()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    observed_allowlist: set[tuple[str, str]] = set()
    largest: list[tuple[int, str, str]] = []
    for path in python_paths():
        relpath = path.relative_to(ROOT).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relpath)
        except SyntaxError as exc:
            failures.append(f"{relpath} cannot be parsed: {exc}")
            continue
        for qualname, node in iter_functions(tree):
            if not hasattr(node, "end_lineno"):
                continue
            lines = int(node.end_lineno) - int(node.lineno) + 1
            largest.append((lines, relpath, qualname))
            key = (relpath, qualname)
            allowed = allowlist.get(key)
            if lines <= threshold:
                if allowed:
                    failures.append(
                        f"{relpath}:{qualname} is allowlisted but now below threshold"
                    )
                continue
            if not allowed:
                failures.append(
                    f"{relpath}:{qualname} has {lines} lines; split it or register "
                    "a no-growth allowlist entry"
                )
                continue
            observed_allowlist.add(key)
            if lines > allowed["max_lines"]:
                failures.append(
                    f"{relpath}:{qualname} grew from allowlisted "
                    f"{allowed['max_lines']} to {lines} lines"
                )

    missing = sorted(set(allowlist) - observed_allowlist)
    for relpath, qualname in missing:
        failures.append(f"allowlisted large function no longer exists: {relpath}:{qualname}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    largest.sort(reverse=True)
    print(
        "OK: checked source tool complexity; "
        f"{len(allowlist)} known large functions are no-growth capped; "
        f"largest={largest[0][1]}:{largest[0][2]}:{largest[0][0]} lines"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

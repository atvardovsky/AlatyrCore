#!/usr/bin/env python3
"""Guard AlatyrCore source tooling against unbounded large-function growth."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "tools" / "tool_complexity_allowlist.json"
VERSION_FILE = ROOT / "VERSION"
VERSION_RE = re.compile(
    r"^(?P<major>0|[1-9][0-9]*)\.(?P<minor>0|[1-9][0-9]*)\."
    r"(?P<patch>0|[1-9][0-9]*)(?:-(?P<stage>alpha|beta|rc)\."
    r"(?P<number>0|[1-9][0-9]*))?(?:\+[0-9A-Za-z.-]+)?$"
)
STAGE_ORDER = {"alpha": 0, "beta": 1, "rc": 2, None: 3}
MAX_ALLOWLIST_SLACK_LINES = 25


def version_key(value: str) -> tuple[int, int, int, int, int]:
    match = VERSION_RE.fullmatch(value)
    if match is None:
        raise ValueError(f"unsupported source version: {value}")
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        STAGE_ORDER[match.group("stage")],
        int(match.group("number") or 0),
    )


def load_allowlist() -> tuple[int, dict[tuple[str, str], dict[str, Any]]]:
    data = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    if data.get("schema_version") != 2 or data.get("allowlist_kind") != (
        "alatyr-source-tool-complexity-allowlist"
    ):
        raise ValueError("tool complexity allowlist has invalid contract")
    expected_fields = {
        "schema_version",
        "allowlist_kind",
        "max_function_lines",
        "max_known_large_functions",
        "debt_owner",
        "review_by_version",
        "known_large_functions",
    }
    unknown = sorted(set(data) - expected_fields)
    missing = sorted(expected_fields - set(data))
    if unknown or missing:
        raise ValueError(
            f"tool complexity allowlist fields drifted: missing={missing} unknown={unknown}"
        )
    threshold = data.get("max_function_lines")
    if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold <= 0:
        raise ValueError("max_function_lines must be a positive integer")
    allowlist: dict[tuple[str, str], dict[str, Any]] = {}
    entries = data.get("known_large_functions")
    if not isinstance(entries, list):
        raise ValueError("known_large_functions must be a list")
    maximum_entries = data.get("max_known_large_functions")
    if (
        not isinstance(maximum_entries, int)
        or isinstance(maximum_entries, bool)
        or maximum_entries < 0
        or len(entries) > maximum_entries
    ):
        raise ValueError("known_large_functions exceeds its aggregate no-growth cap")
    if not isinstance(data.get("debt_owner"), str) or not data["debt_owner"].strip():
        raise ValueError("tool complexity debt_owner must be non-empty")
    review_by = data.get("review_by_version")
    if not isinstance(review_by, str):
        raise ValueError("tool complexity review_by_version is invalid")
    if version_key(VERSION_FILE.read_text(encoding="utf-8").strip()) >= version_key(
        review_by
    ):
        raise ValueError(
            "tool complexity review milestone has been reached; review or renew "
            "the allowlist before release"
        )
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


def allowlist_cap_failure(
    relpath: str, qualname: str, lines: int, allowed_max: int
) -> str | None:
    """Reject growth and stale caps without forcing exact-line churn."""

    if lines > allowed_max:
        return (
            f"{relpath}:{qualname} grew from allowlisted "
            f"{allowed_max} to {lines} lines"
        )
    if allowed_max - lines > MAX_ALLOWLIST_SLACK_LINES:
        return (
            f"{relpath}:{qualname} allowlist cap {allowed_max} is stale for "
            f"{lines} lines; ratchet it to within {MAX_ALLOWLIST_SLACK_LINES} lines"
        )
    return None


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
            cap_failure = allowlist_cap_failure(
                relpath, qualname, lines, allowed["max_lines"]
            )
            if cap_failure:
                failures.append(cap_failure)

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

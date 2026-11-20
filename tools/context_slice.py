#!/usr/bin/env python3
"""Return a bounded slice of a repository text file by heading, symbol, or lines."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import stat
import sys
from pathlib import Path
from typing import Any

from read_ledger import LedgerError, check_delivery, record_delivery


MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_WORDS = 20_000
DEFAULT_WORDS = 1_500
MAX_LIST_ENTRIES = 400
WORD_RE = re.compile(r"\S+")
HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
SLUG_RE = re.compile(r"[^a-z0-9]+")


class SliceError(ValueError):
    pass


def _target(value: str) -> Path:
    target = Path(value).expanduser().resolve()
    if not target.is_dir():
        raise SliceError(f"target is not a directory: {value}")
    return target


def _relative_path(target: Path, value: str) -> Path:
    candidate = Path(value)
    if (
        candidate.is_absolute()
        or candidate.drive
        or "\\" in value
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise SliceError("path must be a normalized target-relative path")
    path = target / candidate
    if path.is_symlink():
        raise SliceError("path must not be a symlink")
    resolved = path.resolve()
    try:
        resolved.relative_to(target)
    except ValueError as exc:
        raise SliceError("path escapes the target") from exc
    try:
        info = path.lstat()
    except OSError as exc:
        raise SliceError(f"path is unavailable: {value}") from exc
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise SliceError("path must be a regular file without hardlinks")
    if info.st_size > MAX_FILE_BYTES:
        raise SliceError(f"file exceeds {MAX_FILE_BYTES} bytes")
    return path


def _read(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SliceError(f"cannot read {path.name}: {exc}") from exc
    if len(raw) > MAX_FILE_BYTES:
        raise SliceError(f"file exceeds {MAX_FILE_BYTES} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SliceError("file is not valid UTF-8 text") from exc
    if "\x00" in text:
        raise SliceError("file contains a null byte and is not text")
    return text


def words(text: str) -> int:
    return len(WORD_RE.findall(text))


def heading_id(title: str) -> str:
    return SLUG_RE.sub("-", title.lower()).strip("-")


def markdown_sections(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines(keepends=True)
    headings: list[tuple[int, int, str, str]] = []
    fence: tuple[str, int] | None = None
    for index, line in enumerate(lines):
        marker = FENCE_RE.match(line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = (token[0], len(token))
            elif token[0] == fence[0] and len(token) >= fence[1] and not line[marker.end():].strip():
                fence = None
            continue
        match = HEADING_RE.match(line)
        if fence is None and match:
            title = match.group(2).rstrip("#").strip()
            headings.append((index, len(match.group(1)), heading_id(title), title))
    sections: list[dict[str, Any]] = []
    for position, (start, level, identifier, title) in enumerate(headings):
        end = len(lines)
        for later_start, later_level, _, _ in headings[position + 1:]:
            if later_level <= level:
                end = later_start
                break
        content = "".join(lines[start:end])
        sections.append(
            {
                "id": identifier,
                "title": title,
                "level": level,
                "start_line": start + 1,
                "end_line": end,
                "words": words(content),
                "content": content,
            }
        )
    return sections


def python_symbols(text: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise SliceError(f"file is not valid Python: {exc.msg} at line {exc.lineno}") from exc
    lines = text.splitlines(keepends=True)
    symbols: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        start = min(
            [node.lineno, *(decorator.lineno for decorator in node.decorator_list)]
        )
        end = getattr(node, "end_lineno", None)
        if not isinstance(end, int) or end < start:
            continue
        kind = (
            "class"
            if isinstance(node, ast.ClassDef)
            else "async function"
            if isinstance(node, ast.AsyncFunctionDef)
            else "function"
        )
        content = "".join(lines[start - 1:end])
        symbols.append(
            {
                "kind": kind,
                "name": node.name,
                "start_line": start,
                "end_line": end,
                "words": words(content),
                "content": content,
            }
        )
    symbols.sort(key=lambda item: (item["start_line"], item["name"]))
    return symbols


def _line_range(value: str, total: int) -> tuple[int, int]:
    match = re.fullmatch(r"\s*(\d+)\s*[:\-]\s*(\d+)\s*", value)
    if not match:
        raise SliceError("--lines must be START:END with 1-based inclusive integers")
    start, end = int(match.group(1)), int(match.group(2))
    if start < 1 or end < start:
        raise SliceError("--lines requires 1 <= START <= END")
    if end > total:
        raise SliceError(f"--lines ends at {end}, but the file has {total} lines")
    return start, end


def _select(
    text: str,
    *,
    heading: str | None,
    symbol: str | None,
    line_range: str | None,
) -> dict[str, Any]:
    lines = text.splitlines(keepends=True)
    if heading is not None:
        sections = markdown_sections(text)
        matches = [
            section
            for section in sections
            if heading.casefold() in {section["id"].casefold(), section["title"].casefold()}
        ]
        if not matches:
            raise SliceError(f"unknown heading: {heading}")
        if len(matches) > 1:
            locations = ", ".join(str(section["start_line"]) for section in matches)
            raise SliceError(f"heading is ambiguous; matching lines: {locations}")
        section = matches[0]
        return {
            "selection": f"heading {section['id']}",
            "start_line": section["start_line"],
            "end_line": section["end_line"],
            "content": section["content"],
        }
    if symbol is not None:
        matches = [item for item in python_symbols(text) if item["name"] == symbol]
        if not matches:
            raise SliceError(f"unknown Python symbol: {symbol}")
        if len(matches) > 1:
            locations = ", ".join(str(item["start_line"]) for item in matches)
            raise SliceError(f"Python symbol is ambiguous; matching lines: {locations}")
        item = matches[0]
        return {
            "selection": f"symbol {symbol}",
            "start_line": item["start_line"],
            "end_line": item["end_line"],
            "content": item["content"],
        }
    if line_range is not None:
        start, end = _line_range(line_range, len(lines))
        return {
            "selection": f"lines {start}:{end}",
            "start_line": start,
            "end_line": end,
            "content": "".join(lines[start - 1:end]),
        }
    raise SliceError("one of --heading, --symbol, or --lines is required")


def _digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _result(
    path: Path,
    text: str,
    selected: dict[str, Any],
    *,
    display_path: str,
) -> dict[str, Any]:
    content = selected["content"]
    return {
        "schema_version": 1,
        "kind": "context-slice",
        "path": display_path,
        "sha256": _digest(text.encode("utf-8")),
        "selection": selected["selection"],
        "start_line": selected["start_line"],
        "end_line": selected["end_line"],
        "words": words(content),
        "characters": len(content),
        "total_words": words(text),
        "total_characters": len(text),
        "content": content,
    }


def _print_list(path: Path, text: str, display_path: str) -> None:
    if path.suffix.lower() in {".md", ".markdown"}:
        entries = markdown_sections(text)
        rows = [
            (entry["start_line"], entry["level"], entry["id"], entry["title"], entry["words"])
            for entry in entries
        ]
        header = "line\tlevel\tid\ttitle\twords"
    elif path.suffix == ".py":
        entries = python_symbols(text)
        rows = [
            (entry["start_line"], entry["kind"], entry["name"], entry["end_line"], entry["words"])
            for entry in entries
        ]
        header = "line\tkind\tname\tend\twords"
    else:
        raise SliceError("list supports Markdown and Python files")
    print(f"path: {display_path}")
    print(f"sha256: {_digest(text.encode('utf-8'))}")
    print(f"total_words: {words(text)}")
    print(header)
    for row in rows[:MAX_LIST_ENTRIES]:
        print("\t".join(str(value) for value in row))
    if len(rows) > MAX_LIST_ENTRIES:
        print(f"[truncated: {len(rows) - MAX_LIST_ENTRIES} more entries]")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", required=True, type=Path)
    actions = parser.add_subparsers(dest="action", required=True)
    list_parser = actions.add_parser("list", allow_abbrev=False)
    list_parser.add_argument("--path", required=True)
    read_parser = actions.add_parser("read", allow_abbrev=False)
    read_parser.add_argument("--path", required=True)
    selection = read_parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--heading")
    selection.add_argument("--symbol")
    selection.add_argument("--lines")
    read_parser.add_argument("--max-words", type=int, default=DEFAULT_WORDS)
    read_parser.add_argument("--json", action="store_true")
    read_parser.add_argument("--session")
    read_parser.add_argument("--task")
    read_parser.add_argument("--reuse", action="store_true")
    return parser


def _ledger_decision(target: Path, args: argparse.Namespace, result: dict[str, Any]) -> dict[str, Any] | None:
    if not args.reuse:
        return None
    if not args.session or not args.task:
        raise SliceError("--reuse requires --session and --task")
    try:
        return check_delivery(
            target,
            session_id=args.session,
            task_id=args.task,
            relpath=args.path,
            start=result["start_line"],
            end=result["end_line"],
        )
    except LedgerError as exc:
        print(f"WARN: read ledger: {exc}", file=sys.stderr)
        return {"state": "unavailable", "reusable": False, "reason": str(exc)}


def _record_delivery(target: Path, args: argparse.Namespace, result: dict[str, Any]) -> None:
    if not args.session or not args.task:
        return
    try:
        record_delivery(
            target,
            session_id=args.session,
            task_id=args.task,
            relpath=args.path,
            start=result["start_line"],
            end=result["end_line"],
            selector=result["selection"],
            words=result["words"],
        )
    except LedgerError as exc:
        print(f"WARN: read ledger: {exc}", file=sys.stderr)


def _reuse_receipt(result: dict[str, Any], decision: dict[str, Any]) -> str:
    share = 100 * result["words"] / max(result["total_words"], 1)
    return "\n".join(
        [
            f"already-delivered: {result['path']} {result['selection']}",
            f"digest: {decision.get('file_sha256', result['sha256'])}",
            f"lines: {result['start_line']}-{result['end_line']}",
            f"words: {result['words']} of {result['total_words']} ({share:.1f}%)",
            "reuse: true",
        ]
    ) + "\n"


def _missing_content(result: dict[str, Any], decision: dict[str, Any]) -> list[dict[str, Any]]:
    lines = result["content"].splitlines(keepends=True)
    base = result["start_line"]
    output = []
    for start, end in decision.get("missing_ranges", []):
        content = "".join(lines[start - base:end - base + 1])
        output.append({"start_line": start, "end_line": end, "content": content})
    return output


def main() -> int:
    args = build_parser().parse_args()
    try:
        target = _target(str(args.target))
        if args.action == "list":
            path = _relative_path(target, args.path)
            text = _read(path)
            _print_list(path, text, args.path)
            return 0
        if args.max_words < 1 or args.max_words > MAX_WORDS:
            raise SliceError(f"--max-words must be from 1 to {MAX_WORDS}")
        path = _relative_path(target, args.path)
        text = _read(path)
        selected = _select(
            text,
            heading=args.heading,
            symbol=args.symbol,
            line_range=args.lines,
        )
        result = _result(path, text, selected, display_path=args.path)
        if result["words"] > args.max_words:
            raise SliceError(
                f"slice is {result['words']} words (limit {args.max_words}); "
                "narrow --heading, --symbol, or --lines"
            )
        decision = _ledger_decision(target, args, result)
        if decision is not None and decision["state"] == "reused":
            if args.json:
                print(
                    json.dumps(
                        {
                            "kind": "context-slice-reuse",
                            "path": result["path"],
                            "selection": result["selection"],
                            "decision": decision,
                            "content": None,
                        },
                        indent=2,
                    )
                    + "\n",
                    end="",
                )
            else:
                sys.stdout.write(_reuse_receipt(result, decision))
            return 0
        if decision is not None and decision["state"] == "partial":
            missing = _missing_content(result, decision)
            if args.json:
                print(
                    json.dumps(
                        {
                            "kind": "context-slice-reuse",
                            "path": result["path"],
                            "selection": result["selection"],
                            "decision": decision,
                            "missing": missing,
                        },
                        indent=2,
                    )
                    + "\n",
                    end="",
                )
            else:
                sys.stdout.write(_reuse_receipt(result, decision))
                print("missing: " + ", ".join(
                    f"{item['start_line']}-{item['end_line']}" for item in missing
                ))
                print("---")
                for item in missing:
                    sys.stdout.write(item["content"])
            _record_delivery(target, args, result)
            return 0
        if args.json:
            print(json.dumps(result, indent=2) + "\n", end="")
        else:
            share = 100 * result["words"] / max(result["total_words"], 1)
            print(f"path: {result['path']}")
            print(f"sha256: {result['sha256']}")
            print(f"selection: {result['selection']}")
            print(
                f"lines: {result['start_line']}-{result['end_line']} "
                f"({result['end_line'] - result['start_line'] + 1})"
            )
            print(
                f"words: {result['words']} of {result['total_words']} "
                f"({share:.1f}%)"
            )
            print("---")
            sys.stdout.write(result["content"])
            if not result["content"].endswith("\n"):
                sys.stdout.write("\n")
        if decision is not None and decision["state"] not in {"unavailable", "unsafe", "too-large"}:
            _record_delivery(target, args, result)
        return 0
    except (OSError, SliceError) as exc:
        print(f"FAIL: context slice: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

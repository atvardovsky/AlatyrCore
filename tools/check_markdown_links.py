#!/usr/bin/env python3
"""Validate local Markdown links in the AlatyrCore source repository.

This validates repository documentation and templates only. It is not a
portable framework requirement for target projects.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]

ROOT_MARKDOWN_FILES = [
    "AGENTS.md",
    "AI_ASSISTANTS.md",
    "CHANGELOG.md",
    "INSTALL.md",
    "README.md",
]
MARKDOWN_ROOTS = [
    "conformance",
    "docs",
    "framework",
    "installer",
    "templates/target",
    "tools",
]
SKIP_PARTS = {
    ".git",
    "__pycache__",
    "tmp",
}
LINK_RE = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
LINE_SUFFIX_RE = re.compile(r":\d+$")
LOCAL_SCHEMES = {"", None}
SKIP_SCHEMES = {
    "app",
    "data",
    "file",
    "http",
    "https",
    "mailto",
    "mcp",
    "skill",
    "vscode",
}


def markdown_files() -> list[Path]:
    files: list[Path] = []
    for relpath in ROOT_MARKDOWN_FILES:
        path = ROOT / relpath
        if path.is_file():
            files.append(path)
    for relroot in MARKDOWN_ROOTS:
        root = ROOT / relroot
        if not root.is_dir():
            continue
        for path in root.rglob("*.md"):
            if any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts):
                continue
            files.append(path)
    return sorted(set(files))


def destination_from_link(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<"):
        end = value.find(">")
        if end != -1:
            return value[1:end].strip()
        return value[1:].strip()
    parts = value.split()
    return parts[0] if parts else ""


def should_skip_destination(destination: str) -> bool:
    if not destination:
        return True
    if destination.startswith("#"):
        return True
    if destination.startswith("//"):
        return True
    if "{" in destination or "}" in destination:
        return True
    parsed = urlsplit(destination)
    scheme = parsed.scheme.lower()
    if scheme in SKIP_SCHEMES:
        return True
    return scheme not in LOCAL_SCHEMES


def candidate_paths(source: Path, destination: str) -> list[Path]:
    target = unquote(destination.split("#", 1)[0].split("?", 1)[0])
    if not target:
        return []

    candidates: list[Path] = []
    if target.startswith("/"):
        candidates.append((ROOT / target.lstrip("/")).resolve())
    else:
        candidates.append((source.parent / target).resolve())

    stripped = LINE_SUFFIX_RE.sub("", target)
    if stripped != target:
        if stripped.startswith("/"):
            candidates.append((ROOT / stripped.lstrip("/")).resolve())
        else:
            candidates.append((source.parent / stripped).resolve())
    return candidates


def has_existing_candidate(source: Path, destination: str) -> bool:
    for path in candidate_paths(source, destination):
        try:
            path.relative_to(ROOT)
        except ValueError:
            continue
        if path.exists():
            return True
    return False


def main() -> int:
    failures: list[str] = []
    checked_links = 0

    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in LINK_RE.finditer(line):
                destination = destination_from_link(match.group(1))
                if should_skip_destination(destination):
                    continue
                checked_links += 1
                if not has_existing_candidate(path, destination):
                    relpath = path.relative_to(ROOT)
                    failures.append(
                        f"{relpath}:{line_number} missing local link target: "
                        f"{destination}"
                    )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(f"OK: checked {checked_links} local Markdown links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

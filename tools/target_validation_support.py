#!/usr/bin/env python3
"""Reusable parsing, Git, hashing, and scope helpers for target validation."""

from __future__ import annotations

import fnmatch
import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Tuple

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode


PathKey = Tuple[str, ...]

UNRESOLVED_WORDS = {
    "",
    "not defined",
    "undefined",
    "unknown",
    "todo",
    "tbd",
    "n/a",
}

SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
UNAVAILABLE_HASH_MARKERS = {
    "not available",
    "not available with reason",
    "unavailable",
    "not recorded",
    "none",
}


@dataclass(frozen=True)
class Scalar:
    value: str
    line: int


@dataclass
class ManifestData:
    containers: set[PathKey]
    scalars: dict[PathKey, Scalar]
    lists: dict[PathKey, list[Scalar]]
    parse_failures: list[str]


def load_manifest_object(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("manifest root must be a mapping")
    return value


def parse_manifest(path: Path) -> ManifestData:
    containers: set[PathKey] = set()
    scalars: dict[PathKey, Scalar] = {}
    lists: dict[PathKey, list[Scalar]] = {}
    failures: list[str] = []
    try:
        root = yaml.compose(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        location = f"line {mark.line + 1}: " if mark is not None else ""
        return ManifestData(containers, scalars, lists, [location + str(exc)])

    def visit(node: Node, current_path: PathKey) -> None:
        if isinstance(node, MappingNode):
            if current_path:
                containers.add(current_path)
            seen: set[str] = set()
            for key_node, value_node in node.value:
                if not isinstance(key_node, ScalarNode) or not key_node.value:
                    failures.append(
                        f"line {key_node.start_mark.line + 1}: mapping key must be a string"
                    )
                    continue
                key = key_node.value
                if key in seen:
                    failures.append(
                        f"line {key_node.start_mark.line + 1}: duplicate key {key}"
                    )
                seen.add(key)
                visit(value_node, current_path + (key,))
            return
        if isinstance(node, SequenceNode):
            containers.add(current_path)
            values = lists.setdefault(current_path, [])
            for item in node.value:
                line = item.start_mark.line + 1
                if isinstance(item, ScalarNode):
                    values.append(Scalar(item.value, line))
                else:
                    values.append(Scalar("<mapping>", line))
                    visit(item, current_path + ("[]",))
            return
        if isinstance(node, ScalarNode):
            scalars[current_path] = Scalar(node.value, node.start_mark.line + 1)
            return
        failures.append(f"unsupported YAML node at {dotted(current_path)}")

    if root is None:
        failures.append("manifest is empty")
    else:
        visit(root, ())
        if not isinstance(root, MappingNode):
            failures.append("manifest root must be a mapping")

    return ManifestData(
        containers=containers,
        scalars=scalars,
        lists=lists,
        parse_failures=failures,
    )


def strip_quotes(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in "'\"":
        return stripped[1:-1]
    return stripped


def dotted(path: PathKey) -> str:
    return ".".join(path)


def is_unresolved_value(value: str) -> bool:
    normalized = value.strip().strip("\"'").lower()
    return normalized in UNRESOLVED_WORDS or is_placeholder(value)


def is_placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    return stripped.startswith("{") and stripped.endswith("}")


def expect_string_list(
    value: Any,
    validator: Any,
    code: str,
    path: str,
    *,
    label: str = "value",
) -> list[str]:
    if not isinstance(value, list) or not value:
        validator.error(code, f"{label} must be a non-empty list", path)
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            validator.error(code, f"{label}[{index}] must be a non-empty string", path)
            continue
        result.append(item)
    return result


def duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    repeated: set[str] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return sorted(repeated)


def should_skip_path(path: Path) -> bool:
    skip_parts = {".git", "node_modules", "__pycache__", "dist", "build"}
    return any(part in skip_parts for part in path.parts)


def is_target_relative_path(value: str) -> bool:
    path = Path(value)
    if path.is_absolute():
        return False
    return ".." not in path.parts


def extract_field(text: str, label: str) -> str:
    for line in text.splitlines():
        if line.startswith(label):
            return strip_backticks(line[len(label) :].strip())
    return ""


def strip_backticks(value: str) -> str:
    stripped = strip_quotes(value)
    if len(stripped) >= 2 and stripped[0] == stripped[-1] == "`":
        return stripped[1:-1]
    return stripped


def normalize_hash_field(value: str) -> str:
    normalized = strip_backticks(value).strip()
    if not normalized or is_placeholder(normalized):
        return ""
    lowered = normalized.lower()
    if any(marker in lowered for marker in UNAVAILABLE_HASH_MARKERS):
        return ""
    if SHA256_RE.match(normalized):
        return normalized.lower()
    return ""


def git_changed_files(target: Path, diff_ref: str) -> list[str] | None:
    changed: set[str] = set()
    base_result: list[str] | None = None
    for comparison in [f"{diff_ref}...HEAD", diff_ref]:
        base_result = git_name_status_paths(target, comparison)
        if base_result is not None:
            changed.update(base_result)
            break
    if base_result is None:
        return None

    for arguments in [[], ["--cached"]]:
        worktree_result = git_name_status_paths(target, *arguments)
        if worktree_result is None:
            return None
        changed.update(worktree_result)

    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=target,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if untracked.returncode != 0:
        return None
    changed.update(decode_git_path(value) for value in untracked.stdout.split(b"\0") if value)
    return sorted(changed)


def git_name_status_paths(target: Path, *comparison: str) -> list[str] | None:
    result = subprocess.run(
        ["git", "diff", "--name-status", "-z", "--find-renames", *comparison],
        cwd=target,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None
    parts = result.stdout.split(b"\0")
    paths: list[str] = []
    index = 0
    while index < len(parts) and parts[index]:
        status = parts[index].decode("ascii", errors="replace")
        index += 1
        path_count = 2 if status[:1] in {"R", "C"} else 1
        if index + path_count > len(parts):
            return None
        for value in parts[index : index + path_count]:
            if value:
                paths.append(decode_git_path(value))
        index += path_count
    return paths


def git_range_changed_files(target: Path, before: str, after: str) -> list[str] | None:
    """Return every old/new path changed between two explicit commit refs."""

    if git_resolve_ref(target, before) is None or git_resolve_ref(target, after) is None:
        return None
    paths = git_name_status_paths(target, before, after)
    return sorted(set(paths)) if paths is not None else None


def decode_git_path(value: bytes) -> str:
    return value.decode("utf-8", errors="surrogateescape").replace("\\", "/")


def git_diff_patch(target: Path, diff_ref: str) -> str | None:
    commands = [
        ["git", "diff", "--binary", diff_ref],
        ["git", "diff", "--binary", f"{diff_ref}...HEAD"],
    ]
    for command in commands:
        result = subprocess.run(
            command,
            cwd=target,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            return result.stdout
    return None


def is_protected_surface(path: str) -> bool:
    protected_prefixes = [
        ".ai/",
        ".github/copilot-instructions.md",
        ".github/prompts/",
        ".cursor/",
        ".devin/",
        ".windsurf/",
        ".agents/",
    ]
    protected_files = {
        "AGENTS.md",
        "AI_ASSISTANTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        "CODEOWNERS",
        ".cursorrules",
        ".windsurfrules",
    }
    return path in protected_files or any(path.startswith(prefix) for prefix in protected_prefixes)


def extract_list_field(text: str, label: str) -> list[str]:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != label:
            continue
        values: list[str] = []
        for candidate in lines[index + 1 :]:
            stripped = candidate.strip()
            if not stripped:
                if values:
                    break
                continue
            if not stripped.startswith("- "):
                break
            value = strip_backticks(stripped[2:].strip())
            if value.lower() not in {"none", "not applicable", "not-applicable"}:
                values.append(value)
        return values
    return []


def is_target_scope_pattern(value: str) -> bool:
    if not value or value.startswith(("/", "\\")):
        return False
    if re.match(r"^[A-Za-z]:[\\/]", value):
        return False
    normalized = value.replace("\\", "/")
    return ".." not in normalized.split("/")


def scope_entries_cover(path: str, entries: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    for entry in entries:
        if is_placeholder(entry) or not is_target_scope_pattern(entry):
            continue
        pattern = entry.replace("\\", "/")
        if normalized == pattern or fnmatch.fnmatchcase(normalized, pattern):
            return True
    return False


def nested_json_value(data: Any, path: tuple[str, ...]) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def json_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if isinstance(item, str) and item.strip()]


def git_resolve_ref(target: Path, ref: str) -> str | None:
    if not ref:
        return None
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
        cwd=target,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def refs_match(target: Path, approved: str, selected: str) -> bool:
    if not approved or not selected:
        return False
    approved_revision = git_resolve_ref(target, approved)
    selected_revision = git_resolve_ref(target, selected)
    if approved_revision and selected_revision:
        return approved_revision == selected_revision
    return approved == selected


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head_revision(target: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=target,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None
    revision = result.stdout.strip()
    return revision or None


def markdown_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            current = heading.group(1).strip()
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return sections


def section_items(lines: list[str]) -> list[str]:
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        value = stripped[2:].strip()
        if value in {"none", "`none`"}:
            continue
        items.append(value.strip("`"))
    return items

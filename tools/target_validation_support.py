#!/usr/bin/env python3
"""Reusable parsing, Git, hashing, and scope helpers for target validation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Tuple

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from path_spec import PathDialect, PathSpec
from yaml_support import safe_compose, safe_load


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
CANONICAL_CHANGE_SET_HASH_CONTRACT = "canonical-git-change-set-v1"


class GitEvidenceState(str, Enum):
    """Availability and stability of Git evidence observed during one run."""

    STABLE = "stable"
    MUTATED = "mutated"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class GitChangeSet:
    """One immutable, canonical view of changes against a resolved Git base."""

    requested_ref: str
    selected_revision: str
    base_revision: str
    head_revision: str
    changed_files: tuple[str, ...]
    canonical_payload: str
    content_sha256: str


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
    value = safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("manifest root must be a mapping")
    return value


def parse_manifest(path: Path) -> ManifestData:
    containers: set[PathKey] = set()
    scalars: dict[PathKey, Scalar] = {}
    lists: dict[PathKey, list[Scalar]] = {}
    failures: list[str] = []
    try:
        root = safe_compose(path.read_text(encoding="utf-8"))
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


def _git_bytes(target: Path, *arguments: str) -> bytes | None:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=target,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return None
    return result.stdout if result.returncode == 0 else None


def _git_merge_base(target: Path, left: str, right: str) -> str | None:
    output = _git_bytes(target, "merge-base", left, right)
    if output is None:
        return None
    revision = output.decode("ascii", errors="replace").strip()
    return revision or None


def _name_status_paths(target: Path, *comparison: str) -> list[str] | None:
    output = _git_bytes(
        target,
        "diff",
        "--relative",
        "--name-status",
        "-z",
        "--find-renames=50%",
        *comparison,
        "--",
        ".",
    )
    if output is None:
        return None
    return decode_name_status_paths(output)


def decode_name_status_paths(output: bytes) -> list[str] | None:
    """Decode old and new paths from a NUL-delimited Git name-status stream."""

    parts = output.split(b"\0")
    paths: list[str] = []
    index = 0
    while index < len(parts) and parts[index]:
        status_value = parts[index].decode("ascii", errors="replace")
        index += 1
        path_count = 2 if status_value[:1] in {"R", "C"} else 1
        if index + path_count > len(parts):
            return None
        for value in parts[index : index + path_count]:
            if value:
                paths.append(decode_git_path(value))
        index += path_count
    return paths


def _untracked_paths(target: Path) -> list[str] | None:
    output = _git_bytes(
        target, "ls-files", "--others", "--exclude-standard", "-z", "--", "."
    )
    if output is None:
        return None
    return sorted(
        decode_git_path(value) for value in output.split(b"\0") if value
    )


def _untracked_payload(target: Path, path: str) -> dict[str, Any] | None:
    candidate = target / Path(path)
    try:
        metadata = candidate.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            content = os.readlink(candidate).encode("utf-8", errors="surrogateescape")
            kind = "symlink"
            executable = False
        elif stat.S_ISREG(metadata.st_mode):
            content = candidate.read_bytes()
            kind = "file"
            executable = bool(metadata.st_mode & 0o111)
        else:
            return None
    except (OSError, UnicodeError):
        return None
    return {
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "executable": executable,
        "kind": kind,
        "path": path,
    }


def resolve_git_change_set(
    target: Path,
    diff_ref: str,
    *,
    head_revision: str | None = None,
    selected_revision: str | None = None,
) -> GitChangeSet | None:
    """Resolve one canonical committed/index/worktree change set.

    The selected ref and HEAD are reduced to an immutable merge base once. The
    path scope and digest are then derived from the same committed, staged,
    unstaged, and untracked layers, so approval scope cannot disagree with the
    content identity on diverged histories.
    """

    resolved_selected = selected_revision or git_resolve_ref(target, diff_ref)
    resolved_head = head_revision or git_head_revision(target)
    if resolved_selected is None or resolved_head is None:
        return None
    base_revision = _git_merge_base(target, resolved_selected, resolved_head)
    if base_revision is None:
        return None

    layer_arguments = (
        ("committed", (base_revision, resolved_head)),
        ("staged", ("--cached", resolved_head)),
        ("unstaged", ()),
    )
    changed: set[str] = set()
    layers: list[dict[str, str]] = []
    for layer_id, arguments in layer_arguments:
        paths = _name_status_paths(target, *arguments)
        patch = _git_bytes(
            target,
            "diff",
            "--binary",
            "--full-index",
            "--no-ext-diff",
            "--no-textconv",
            "--no-renames",
            "--diff-algorithm=myers",
            *arguments,
            "--",
            ".",
        )
        if paths is None or patch is None:
            return None
        changed.update(paths)
        layers.append(
            {
                "id": layer_id,
                "patch_sha256": hashlib.sha256(patch).hexdigest(),
            }
        )

    untracked_paths = _untracked_paths(target)
    if untracked_paths is None:
        return None
    untracked: list[dict[str, Any]] = []
    for path in untracked_paths:
        item = _untracked_payload(target, path)
        if item is None:
            return None
        changed.add(path)
        untracked.append(item)

    changed_files = tuple(sorted(changed))
    payload = json.dumps(
        {
            "base_revision": base_revision,
            "changed_files": changed_files,
            "head_revision": resolved_head,
            "layers": layers,
            "schema_version": 1,
            "untracked": untracked,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ) + "\n"
    return GitChangeSet(
        requested_ref=diff_ref,
        selected_revision=resolved_selected,
        base_revision=base_revision,
        head_revision=resolved_head,
        changed_files=changed_files,
        canonical_payload=payload,
        content_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    )


def git_changed_files(target: Path, diff_ref: str) -> list[str] | None:
    change_set = resolve_git_change_set(target, diff_ref)
    return list(change_set.changed_files) if change_set is not None else None


def git_name_status_paths(target: Path, *comparison: str) -> list[str] | None:
    return _name_status_paths(target, *comparison)


def git_range_changed_files(target: Path, before: str, after: str) -> list[str] | None:
    """Return every old/new path changed between two explicit commit refs."""

    if git_resolve_ref(target, before) is None or git_resolve_ref(target, after) is None:
        return None
    paths = git_name_status_paths(target, before, after)
    return sorted(set(paths)) if paths is not None else None


def decode_git_path(value: bytes) -> str:
    return value.decode("utf-8", errors="surrogateescape").replace("\\", "/")


def git_diff_patch(target: Path, diff_ref: str) -> str | None:
    change_set = resolve_git_change_set(target, diff_ref)
    return change_set.canonical_payload if change_set is not None else None


def is_protected_surface(path: str) -> bool:
    protected_prefixes = [
        ".ai/",
        ".github/copilot-instructions.md",
        ".github/prompts/",
        ".cursor/",
        ".devin/",
        ".windsurf/",
        ".junie/",
        ".cline/",
        ".clinerules/",
        ".roo/",
        ".kiro/",
        ".zed/",
        ".opencode/",
        ".gigacode/",
        ".agents/",
    ]
    protected_files = {
        "AGENTS.md",
        "AI_ASSISTANTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        "GIGACODE.md",
        "CODEOWNERS",
        ".cursorrules",
        ".windsurfrules",
        ".clinerules",
        ".rules",
        ".roorules",
        ".roomodes",
        "AGENT.md",
        "opencode.json",
        "opencode.jsonc",
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
        if normalized == pattern or PathSpec(
            pattern, PathDialect.APPROVAL_SCOPE_V1
        ).matches(normalized):
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


def git_resolve_object(target: Path, ref: str, object_kind: str = "commit") -> str | None:
    if not ref:
        return None
    if object_kind not in {"commit", "tree"}:
        raise ValueError(f"unsupported Git object kind: {object_kind}")
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{ref}^{{{object_kind}}}"],
        cwd=target,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def git_resolve_ref(target: Path, ref: str) -> str | None:
    return git_resolve_object(target, ref, "commit")


def git_is_ancestor(target: Path, base: str, result: str) -> bool | None:
    base_revision = git_resolve_object(target, base, "commit")
    result_revision = git_resolve_object(target, result, "commit")
    if base_revision is None or result_revision is None:
        return None
    check = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base_revision, result_revision],
        cwd=target,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if check.returncode == 0:
        return True
    if check.returncode == 1:
        return False
    return None


def git_snapshot_sha256(target: Path, revision: str, paths: list[str]) -> str | None:
    """Hash selected repository-relative file contents at an immutable revision."""
    resolved = git_resolve_object(target, revision, "commit")
    if resolved is None or not paths:
        return None
    digest = hashlib.sha256()
    for selected_path in sorted(set(paths)):
        normalized = selected_path.replace("\\", "/")
        if not is_target_scope_pattern(normalized):
            return None
        result = subprocess.run(
            ["git", "show", f"{resolved}:{normalized}"],
            cwd=target,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            return None
        digest.update(normalized.encode("utf-8"))
        digest.update(b"\0")
        digest.update(result.stdout)
        digest.update(b"\0")
    return digest.hexdigest()


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


def git_branch_name(target: Path) -> str | None:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=target,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None
    branch = result.stdout.strip()
    return branch or "detached HEAD"


class GitEvidenceView:
    """Cache immutable Git queries and detect repository-state mutation per run."""

    def __init__(self, target: Path) -> None:
        self.target = target.resolve()
        self._cache: dict[tuple[Any, ...], Any] = {}
        self.query_misses = 0
        self.cache_hits = 0
        target_is_directory = self.target.is_dir()
        self.initial_head = git_head_revision(self.target) if target_is_directory else None
        self.initial_branch = git_branch_name(self.target) if target_is_directory else None
        self.initial_status = self._status_snapshot() if target_is_directory else None
        self.initial_state = (
            GitEvidenceState.STABLE
            if self.initial_head is not None
            and self.initial_branch is not None
            and self.initial_status is not None
            else GitEvidenceState.UNAVAILABLE
        )

    def _status_snapshot(self) -> bytes | None:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
                cwd=self.target,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            return None
        return result.stdout if result.returncode == 0 else None

    def _cached(self, key: tuple[Any, ...], loader: Any) -> Any:
        if key in self._cache:
            self.cache_hits += 1
            return self._cache[key]
        self.query_misses += 1
        value = loader()
        self._cache[key] = value
        return value

    def head_revision(self) -> str | None:
        return self.initial_head

    def branch_name(self) -> str | None:
        return self.initial_branch

    def resolve_object(self, ref: str, object_kind: str = "commit") -> str | None:
        return self._cached(
            ("resolve-object", ref, object_kind),
            lambda: git_resolve_object(self.target, ref, object_kind),
        )

    def resolve_ref(self, ref: str) -> str | None:
        return self.resolve_object(ref, "commit")

    def change_set(self, diff_ref: str) -> GitChangeSet | None:
        selected_revision = self.resolve_ref(diff_ref)
        if selected_revision is None:
            return None
        return self._cached(
            ("change-set", diff_ref, selected_revision, self.initial_head),
            lambda: resolve_git_change_set(
                self.target,
                diff_ref,
                head_revision=self.initial_head,
                selected_revision=selected_revision,
            ),
        )

    def changed_files(self, diff_ref: str) -> list[str] | None:
        change_set = self.change_set(diff_ref)
        return list(change_set.changed_files) if change_set is not None else None

    def range_changed_files(self, before: str, after: str) -> list[str] | None:
        return self._cached(
            ("range-changed-files", before, after),
            lambda: git_range_changed_files(self.target, before, after),
        )

    def diff_patch(self, diff_ref: str) -> str | None:
        change_set = self.change_set(diff_ref)
        return change_set.canonical_payload if change_set is not None else None

    def is_ancestor(self, base: str, result: str) -> bool | None:
        return self._cached(
            ("is-ancestor", base, result),
            lambda: git_is_ancestor(self.target, base, result),
        )

    def snapshot_sha256(self, revision: str, paths: list[str]) -> str | None:
        normalized = tuple(sorted(set(paths)))
        return self._cached(
            ("snapshot-sha256", revision, normalized),
            lambda: git_snapshot_sha256(self.target, revision, list(normalized)),
        )

    def refs_match(self, approved: str, selected: str) -> bool:
        approved_revision = self.resolve_ref(approved)
        selected_revision = self.resolve_ref(selected)
        if approved_revision and selected_revision:
            return approved_revision == selected_revision
        return approved == selected

    def stability(self) -> GitEvidenceState:
        """Return stable, mutated, or unavailable Git evidence state."""

        if self.initial_state is GitEvidenceState.UNAVAILABLE:
            return GitEvidenceState.UNAVAILABLE
        current_head = git_head_revision(self.target)
        current_branch = git_branch_name(self.target)
        current_status = self._status_snapshot()
        if current_head is None or current_branch is None or current_status is None:
            return GitEvidenceState.MUTATED
        if (
            self.initial_head != current_head
            or self.initial_branch != current_branch
            or self.initial_status != current_status
        ):
            return GitEvidenceState.MUTATED
        return GitEvidenceState.STABLE

    def finalize(self) -> bool:
        """Compatibility facade returning true only for stable Git evidence."""

        return self.stability() is GitEvidenceState.STABLE

    def telemetry(self) -> dict[str, int | str]:
        return {
            "query_misses": self.query_misses,
            "cache_hits": self.cache_hits,
            "cached_queries": len(self._cache),
            "stability": self.stability().value,
        }


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

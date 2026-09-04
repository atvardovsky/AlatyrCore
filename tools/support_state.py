"""Deterministic target support-surface inventory and digest state."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from evidence_contract import canonical_worktree_entries, digest_entries
from path_spec import PathDialect, PathSpec
from target_tool_compat import generation_provenance


SCHEMA_VERSION = 1
POLICY_KIND = "target-support-policy"
STATE_KIND = "target-support-state"
DIGEST_CONTRACT = "alatyr-support-state-v1"
STATE_PATH = ".ai/support-state.json"
POLICY_PATH = ".ai/project/support-policy.json"
CLASSIFICATIONS = {
    "exact-contract",
    "derived",
    "append-only-evidence",
    "local-transient",
}


class SupportStateError(ValueError):
    """Raised when support policy or state cannot be resolved safely."""


@dataclass(frozen=True)
class SupportDifference:
    path: str
    change: str
    before_digest: str | None
    after_digest: str | None


def _load_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SupportStateError(f"cannot load {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SupportStateError(f"{path} must contain a JSON object")
    return data


def _normalized_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise SupportStateError(f"{label} must be a non-empty string")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise SupportStateError(f"{label} must be a normalized target-relative path")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise SupportStateError(f"{label} must be a list")
    result = [_normalized_path(item, f"{label}[]") for item in value]
    if len(result) != len(set(result)):
        raise SupportStateError(f"{label} contains duplicates")
    return result


def validate_policy(policy: dict[str, Any]) -> None:
    if policy.get("schema_version") != SCHEMA_VERSION:
        raise SupportStateError("support policy schema_version must be 1")
    if policy.get("policy_kind") != POLICY_KIND:
        raise SupportStateError(f"support policy policy_kind must be {POLICY_KIND}")
    managed_roots = _string_list(policy.get("managed_roots"), "managed_roots")
    if ".ai" not in managed_roots:
        raise SupportStateError("managed_roots must include .ai")
    _string_list(policy.get("optional_entrypoints"), "optional_entrypoints")

    exclusions = policy.get("exclusions")
    if not isinstance(exclusions, list):
        raise SupportStateError("exclusions must be a list")
    for index, exclusion in enumerate(exclusions):
        if not isinstance(exclusion, dict):
            raise SupportStateError(f"exclusions[{index}] must be an object")
        _normalized_path(exclusion.get("pattern"), f"exclusions[{index}].pattern")
        if not isinstance(exclusion.get("reason"), str) or not exclusion["reason"]:
            raise SupportStateError(f"exclusions[{index}].reason must be non-empty")

    classifications = policy.get("classifications")
    if not isinstance(classifications, list) or not classifications:
        raise SupportStateError("classifications must be a non-empty list")
    ids: set[str] = set()
    for index, classification in enumerate(classifications):
        if not isinstance(classification, dict):
            raise SupportStateError(f"classifications[{index}] must be an object")
        item_id = classification.get("id")
        if not isinstance(item_id, str) or not item_id or item_id in ids:
            raise SupportStateError(f"classifications[{index}].id is missing or repeated")
        ids.add(item_id)
        if classification.get("classification") not in CLASSIFICATIONS:
            raise SupportStateError(f"classifications[{index}].classification is invalid")
        patterns = _string_list(
            classification.get("patterns"), f"classifications[{index}].patterns"
        )
        if not patterns:
            raise SupportStateError(f"classifications[{index}].patterns must not be empty")


def load_policy(target: Path, relpath: str = POLICY_PATH) -> dict[str, Any]:
    policy = _load_object(target / relpath)
    validate_policy(policy)
    return policy


def _matches(path: str, pattern: str) -> bool:
    return PathSpec(pattern, PathDialect.SUPPORT_TREE_V1).matches(path)


def _git_revision(target: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=target,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def _enumerate_root(target: Path, relpath: str) -> Iterable[str]:
    root = target / relpath
    if not root.exists():
        return ()
    if root.is_file() or root.is_symlink():
        return (relpath,)
    return tuple(
        path.relative_to(target).as_posix()
        for path in sorted(root.rglob("*"))
        if path.is_file() or path.is_symlink()
    )


def _git_visible_paths(target: Path) -> set[str] | None:
    result = subprocess.run(
        ["git", "ls-files", "-c", "-o", "--exclude-standard", "-z"],
        cwd=target,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return {
        relpath
        for relpath in result.stdout.decode(
            "utf-8", errors="surrogateescape"
        ).split("\0")
        if relpath
    }


def _group_for(relpath: str) -> str:
    parts = PurePosixPath(relpath).parts
    if len(parts) >= 2 and parts[0] == ".ai":
        if parts[1] in {"framework", "project", "assistant"}:
            return parts[1]
        return "adapter-root"
    return "entrypoints"


def _support_content(content: bytes) -> bytes:
    if b"\0" in content[:8000]:
        return content
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return content
    return content.replace(b"\r\n", b"\n")


def select_support_paths(
    candidates: Iterable[str], policy: dict[str, Any]
) -> dict[str, tuple[str, str]]:
    """Classify candidate support paths using one validated support policy."""

    validate_policy(policy)
    casefolded: dict[str, str] = {}
    collisions: list[str] = []
    for relpath in sorted(candidates):
        folded = relpath.casefold()
        previous = casefolded.get(folded)
        if previous is not None and previous != relpath:
            collisions.extend([previous, relpath])
        else:
            casefolded[folded] = relpath
    if collisions:
        raise SupportStateError(
            "case-colliding support paths: " + ", ".join(sorted(set(collisions)))
        )

    exclusions = policy["exclusions"]
    classification_rules = policy["classifications"]
    selected: dict[str, tuple[str, str]] = {}
    unmanaged: list[str] = []
    ambiguous: list[str] = []
    for relpath in sorted(candidates):
        if relpath == STATE_PATH:
            continue
        if any(_matches(relpath, item["pattern"]) for item in exclusions):
            continue
        matches = [
            item
            for item in classification_rules
            if any(_matches(relpath, pattern) for pattern in item["patterns"])
        ]
        if not matches:
            unmanaged.append(relpath)
            continue
        classifications = {item["classification"] for item in matches}
        if len(classifications) != 1:
            ambiguous.append(relpath)
            continue
        selected[relpath] = (matches[0]["id"], next(iter(classifications)))
    if unmanaged:
        raise SupportStateError(
            "unclassified support paths: " + ", ".join(unmanaged[:20])
        )
    if ambiguous:
        raise SupportStateError(
            "conflicting support classifications: " + ", ".join(ambiguous[:20])
        )
    return selected


def build_support_state_from_bound_entries(
    *,
    policy: dict[str, Any],
    selected: dict[str, tuple[str, str]],
    bound: Iterable[tuple[str, str, bytes]],
    generated_by: dict[str, Any],
    source_revision: str,
) -> dict[str, Any]:
    """Build a support-state record from already canonical path-bound content."""

    validate_policy(policy)
    bound_entries = list(bound)
    files: list[dict[str, Any]] = []
    group_entries: dict[str, list[tuple[str, str, bytes]]] = {}
    for relpath, kind, content in bound_entries:
        if kind == "file":
            content = _support_content(content)
        rule_id, classification = selected[relpath]
        digest = hashlib.sha256(content).hexdigest()
        group = _group_for(relpath)
        files.append(
            {
                "path": relpath,
                "kind": kind,
                "classification": classification,
                "classification_id": rule_id,
                "group": group,
                "digest": f"sha256:{digest}",
                "canonical_size": len(content),
            }
        )
        group_entries.setdefault(group, []).append((relpath, kind, content))

    groups = [
        {
            "id": group,
            "file_count": len(entries),
            "digest": f"sha256:{digest_entries(entries)}",
        }
        for group, entries in sorted(group_entries.items())
    ]
    root_entries = [
        (group["id"], "group", group["digest"].encode("ascii")) for group in groups
    ]
    policy_content = None
    for relpath, kind, content in bound_entries:
        if relpath == POLICY_PATH and kind == "file":
            policy_content = _support_content(content)
            break
    if policy_content is None:
        raise SupportStateError(f"support policy is missing: {POLICY_PATH}")
    policy_digest = hashlib.sha256(policy_content).hexdigest()
    return {
        "schema_version": SCHEMA_VERSION,
        "state_kind": STATE_KIND,
        "digest_contract": DIGEST_CONTRACT,
        "generated_by": generated_by,
        "policy": POLICY_PATH,
        "policy_digest": f"sha256:{policy_digest}",
        "source_revision": source_revision,
        "groups": groups,
        "files": files,
        "root_digest": f"sha256:{digest_entries(root_entries)}",
    }


def build_support_state_from_contents(
    contents: dict[str, bytes],
    *,
    policy: dict[str, Any],
    generated_by: dict[str, Any],
    source_revision: str,
) -> dict[str, Any]:
    """Build support state from projected file contents without filesystem I/O."""

    validate_policy(policy)
    candidates = {
        relpath
        for relpath in contents
        if any(_matches(relpath, root + "/**") for root in policy["managed_roots"])
        or relpath in policy["optional_entrypoints"]
    }
    selected = select_support_paths(candidates, policy)
    bound = [(relpath, "file", contents[relpath]) for relpath in sorted(selected)]
    return build_support_state_from_bound_entries(
        policy=policy,
        selected=selected,
        bound=bound,
        generated_by=generated_by,
        source_revision=source_revision,
    )


def build_support_state(target: Path, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    target = target.resolve()
    policy = policy or load_policy(target)
    validate_policy(policy)

    visible = _git_visible_paths(target)
    if visible is None:
        candidates: set[str] = set()
        for root in policy["managed_roots"]:
            candidates.update(_enumerate_root(target, root))
        for relpath in policy["optional_entrypoints"]:
            path = target / relpath
            if path.is_file() or path.is_symlink():
                candidates.add(relpath)
    else:
        candidates = {
            relpath
            for relpath in visible
            if any(_matches(relpath, root + "/**") for root in policy["managed_roots"])
            or relpath in policy["optional_entrypoints"]
        }

    selected = select_support_paths(candidates, policy)
    bound = canonical_worktree_entries(target, list(selected))
    return build_support_state_from_bound_entries(
        policy=policy,
        selected=selected,
        bound=bound,
        generated_by=generation_provenance(
            target,
            tool_name="snapshot_target_support.py",
        ),
        source_revision=_git_revision(target),
    )


def load_state(target: Path, relpath: str = STATE_PATH) -> dict[str, Any]:
    data = _load_object(target / relpath)
    if data.get("schema_version") != SCHEMA_VERSION or data.get("state_kind") != STATE_KIND:
        raise SupportStateError("support state has an unsupported contract")
    return data


def state_differences(before: dict[str, Any], after: dict[str, Any]) -> list[SupportDifference]:
    before_files = {
        item["path"]: item.get("digest")
        for item in before.get("files", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    after_files = {
        item["path"]: item.get("digest")
        for item in after.get("files", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    differences: list[SupportDifference] = []
    for path in sorted(before_files.keys() | after_files.keys()):
        before_digest = before_files.get(path)
        after_digest = after_files.get(path)
        if before_digest == after_digest:
            continue
        change = "modified"
        if before_digest is None:
            change = "created"
        elif after_digest is None:
            change = "removed"
        differences.append(
            SupportDifference(path, change, before_digest, after_digest)
        )
    return differences


def state_is_current(recorded: dict[str, Any], current: dict[str, Any]) -> bool:
    return (
        recorded.get("digest_contract") == current.get("digest_contract")
        and recorded.get("policy_digest") == current.get("policy_digest")
        and recorded.get("root_digest") == current.get("root_digest")
        and recorded.get("groups") == current.get("groups")
        and recorded.get("files") == current.get("files")
    )


def render_state(state: dict[str, Any]) -> str:
    return json.dumps(state, indent=2, ensure_ascii=True) + "\n"

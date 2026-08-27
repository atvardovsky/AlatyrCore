"""Target support-generation registry, state index, and bounded planning."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from evidence_contract import canonical_worktree_entries, digest_entries


REGISTRY_PATH = ".ai/project/support-generation/registry.json"
INDEX_PATH = ".ai/assistant/support-generation-index.json"
MODES = {"deterministic-derived", "assistant-proposed", "owner-maintained"}


class SupportGenerationError(ValueError):
    """Raised when a support-generation contract is unsafe or inconsistent."""


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SupportGenerationError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SupportGenerationError(f"{path} must contain a JSON object")
    return value


def _safe_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise SupportGenerationError(f"{label} must be a non-empty path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise SupportGenerationError(f"{label} must be target-relative")
    return value


def load_registry(target: Path) -> dict[str, Any]:
    registry = _load(target / REGISTRY_PATH)
    if registry.get("schema_version") != 1 or registry.get("registry_kind") != "target-support-generation-registry":
        raise SupportGenerationError("support-generation registry contract is invalid")
    artifacts = registry.get("artifacts")
    if not isinstance(artifacts, list):
        raise SupportGenerationError("support-generation artifacts must be a list")
    ids: set[str] = set()
    outputs: set[str] = set()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            raise SupportGenerationError(f"artifacts[{index}] must be an object")
        artifact_id = artifact.get("id")
        if not isinstance(artifact_id, str) or not artifact_id or artifact_id in ids:
            raise SupportGenerationError(f"artifacts[{index}].id is invalid")
        ids.add(artifact_id)
        if artifact.get("mode") not in MODES and "{" not in str(artifact.get("mode")):
            raise SupportGenerationError(f"artifact {artifact_id} has invalid mode")
        if not isinstance(artifact.get("owner"), str) or not artifact["owner"]:
            raise SupportGenerationError(f"artifact {artifact_id} needs an owner")
        inputs = artifact.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            raise SupportGenerationError(f"artifact {artifact_id} needs inputs")
        for position, item in enumerate(inputs):
            if not isinstance(item, dict):
                raise SupportGenerationError(f"artifact {artifact_id} input {position} is invalid")
            _safe_path(item.get("path"), f"artifact {artifact_id} input path")
        artifact_outputs = artifact.get("outputs")
        if not isinstance(artifact_outputs, list) or not artifact_outputs:
            raise SupportGenerationError(f"artifact {artifact_id} needs outputs")
        for output in artifact_outputs:
            relpath = _safe_path(output, f"artifact {artifact_id} output")
            if relpath in outputs:
                raise SupportGenerationError(f"support output has multiple producers: {relpath}")
            outputs.add(relpath)
        dependencies = artifact.get("depends_on")
        if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
            raise SupportGenerationError(f"artifact {artifact_id} depends_on must be a string list")
    unknown = sorted(
        dependency
        for artifact in artifacts
        for dependency in artifact["depends_on"]
        if dependency not in ids
    )
    if unknown:
        raise SupportGenerationError("unknown generation dependencies: " + ", ".join(unknown))
    topological_order(registry)
    return registry


def topological_order(registry: dict[str, Any]) -> list[str]:
    artifacts = {item["id"]: item for item in registry.get("artifacts", [])}
    temporary: set[str] = set()
    permanent: set[str] = set()
    ordered: list[str] = []

    def visit(artifact_id: str) -> None:
        if artifact_id in permanent:
            return
        if artifact_id in temporary:
            raise SupportGenerationError(f"support-generation cycle reaches {artifact_id}")
        temporary.add(artifact_id)
        for dependency in artifacts[artifact_id].get("depends_on", []):
            visit(dependency)
        temporary.remove(artifact_id)
        permanent.add(artifact_id)
        ordered.append(artifact_id)

    for artifact_id in sorted(artifacts):
        visit(artifact_id)
    return ordered


def _matching_paths(target: Path, patterns: Iterable[str]) -> list[str]:
    all_files = [
        path.relative_to(target).as_posix()
        for path in target.rglob("*")
        if (path.is_file() or path.is_symlink()) and ".git" not in path.parts
    ]
    selected: set[str] = set()
    for pattern in patterns:
        if any(marker in pattern for marker in "*?["):
            selected.update(path for path in all_files if fnmatch.fnmatchcase(path, pattern))
        elif (target / pattern).is_file() or (target / pattern).is_symlink():
            selected.add(pattern)
    return sorted(selected)


def _path_digest(target: Path, relpaths: Iterable[str], prefix: bytes) -> str:
    entries = canonical_worktree_entries(target, list(relpaths))
    return f"sha256:{hashlib.sha256(prefix + digest_entries(entries).encode('ascii')).hexdigest()}"


def _registry_digest(registry: dict[str, Any]) -> str:
    content = json.dumps(registry, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    digest = hashlib.sha256(b"alatyr-support-generation-registry-v1\0" + content)
    return f"sha256:{digest.hexdigest()}"


def repository_state_digest(target: Path) -> str:
    result = subprocess.run(
        ["git", "ls-files", "-c", "-o", "--exclude-standard", "-z"],
        cwd=target,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise SupportGenerationError("cannot bind generation plan to repository state")
    relpaths = [
        item
        for item in result.stdout.decode(
            "utf-8", errors="surrogateescape"
        ).split("\0")
        if item
    ]
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=target,
        check=False,
        capture_output=True,
        text=True,
    )
    head = revision.stdout.strip() if revision.returncode == 0 else "unavailable"
    return _path_digest(
        target,
        relpaths,
        b"alatyr-support-generation-repository-v1\0" + head.encode("utf-8") + b"\0",
    )


def build_generation_index(target: Path, registry: dict[str, Any] | None = None) -> dict[str, Any]:
    target = target.resolve()
    registry = registry or load_registry(target)
    order = topological_order(registry)
    artifacts = {item["id"]: item for item in registry["artifacts"]}
    states: list[dict[str, Any]] = []
    for artifact_id in order:
        artifact = artifacts[artifact_id]
        input_paths = _matching_paths(target, [item["path"] for item in artifact["inputs"]])
        output_paths = _matching_paths(target, artifact["outputs"])
        missing_outputs = sorted(set(artifact["outputs"]) - set(output_paths))
        states.append(
            {
                "id": artifact_id,
                "mode": artifact["mode"],
                "owner": artifact["owner"],
                "input_paths": input_paths,
                "input_digest": _path_digest(target, input_paths, b"alatyr-support-inputs-v1\0"),
                "output_paths": output_paths,
                "output_digest": _path_digest(target, output_paths, b"alatyr-support-outputs-v1\0"),
                "missing_outputs": missing_outputs,
            }
        )
    return {
        "schema_version": 1,
        "index_kind": "target-support-generation-index",
        "registry": REGISTRY_PATH,
        "registry_digest": _registry_digest(registry),
        "order": order,
        "artifacts": states,
    }


def load_index(target: Path) -> dict[str, Any]:
    index = _load(target / INDEX_PATH)
    if index.get("schema_version") != 1 or index.get("index_kind") != "target-support-generation-index":
        raise SupportGenerationError("support-generation index contract is invalid")
    return index


def generation_plan(target: Path) -> dict[str, Any]:
    registry = load_registry(target)
    recorded = load_index(target)
    current = build_generation_index(target, registry)
    recorded_states = {
        item["id"]: item for item in recorded.get("artifacts", []) if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    actions: list[dict[str, Any]] = []
    artifacts = {item["id"]: item for item in registry["artifacts"]}
    for state in current["artifacts"]:
        previous = recorded_states.get(state["id"])
        stale_reasons: list[str] = []
        if previous is None:
            stale_reasons.append("missing-recorded-state")
        else:
            if previous.get("input_digest") != state["input_digest"]:
                stale_reasons.append("inputs-changed")
            if previous.get("output_digest") != state["output_digest"]:
                stale_reasons.append("outputs-changed")
        if state["missing_outputs"]:
            stale_reasons.append("outputs-missing")
        artifact = artifacts[state["id"]]
        actions.append(
            {
                "id": state["id"],
                "mode": state["mode"],
                "status": "stale" if stale_reasons else "current",
                "reasons": stale_reasons,
                "depends_on": artifact["depends_on"],
                "outputs": artifact["outputs"],
                "approval_trigger": artifact.get("approval_trigger", "none"),
            }
        )
    plan = {
        "schema_version": 1,
        "plan_kind": "target-support-generation-plan",
        "registry_digest": current["registry_digest"],
        "repository_state_digest": repository_state_digest(target),
        "order": current["order"],
        "actions": actions,
    }
    content = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    digest = hashlib.sha256(b"alatyr-support-generation-plan-v1\0" + content)
    plan["plan_digest"] = f"sha256:{digest.hexdigest()}"
    return plan


def render_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True) + "\n"

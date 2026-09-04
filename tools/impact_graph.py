"""Load sharded target consistency graphs and derive reverse impact routing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from path_spec import PathDialect, PathSpec


GRAPH_KIND = "target-consistency-map"
SHARD_KIND = "target-consistency-map-shard"
REVERSE_KIND = "target-consistency-reverse-index"
GRAPH_LEVELS = ["fact", "contract", "area", "system", "adapter", "surface"]
RELATIONSHIP_STATES = {
    "observed",
    "proposed",
    "accepted",
    "rejected",
    "stale",
    "contradicted",
    "removed",
}
ACTIVE_RELATIONSHIP_STATES = {"accepted"}
COVERAGE_STATES = {"mapped", "isolated-verified", "known-gap"}
BINDING_KINDS = {
    "file",
    "glob",
    "json-pointer",
    "yaml-path",
    "markdown-section",
    "config-key",
    "symbol",
}


class ImpactGraphError(ValueError):
    """Raised when a target impact graph is structurally unsafe."""


@dataclass(frozen=True)
class ImpactGraph:
    root: dict[str, Any]
    nodes: dict[str, dict[str, Any]]
    graph_digest: str
    source_paths: tuple[str, ...]


def _load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImpactGraphError(f"cannot load {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ImpactGraphError(f"{path} must contain a JSON object")
    return data


def _safe_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ImpactGraphError(f"{label} must be a non-empty path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ImpactGraphError(f"{label} must be target-relative")
    return value


def _digest_documents(documents: Iterable[tuple[str, dict[str, Any]]]) -> str:
    digest = hashlib.sha256(b"alatyr-impact-graph-v1\0")
    for relpath, document in sorted(documents):
        content = json.dumps(
            document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        for value in [relpath.encode("utf-8"), content]:
            digest.update(str(len(value)).encode("ascii"))
            digest.update(b":")
            digest.update(value)
            digest.update(b"\0")
    return digest.hexdigest()


def load_impact_graph(
    target: Path,
    relpath: str = ".ai/project/consistency-map.json",
) -> ImpactGraph:
    target = target.resolve()
    root = _load(target / relpath)
    if root.get("map_kind") != GRAPH_KIND:
        raise ImpactGraphError("consistency map has an invalid map_kind")
    schema_version = root.get("schema_version")
    documents: list[tuple[str, dict[str, Any]]] = [(relpath, root)]
    nodes: list[Any]
    source_paths = [relpath]
    if schema_version in {1, 2}:
        nodes = root.get("nodes", [])
    elif schema_version == 3:
        shards = root.get("node_shards")
        if not isinstance(shards, list) or not shards:
            raise ImpactGraphError("schema-3 consistency map needs node_shards")
        nodes = []
        shard_ids: set[str] = set()
        for index, descriptor in enumerate(shards):
            if not isinstance(descriptor, dict):
                raise ImpactGraphError(f"node_shards[{index}] must be an object")
            shard_id = descriptor.get("id")
            if not isinstance(shard_id, str) or not shard_id or shard_id in shard_ids:
                raise ImpactGraphError(f"node_shards[{index}].id is invalid")
            shard_ids.add(shard_id)
            shard_path = _safe_path(descriptor.get("path"), f"node_shards[{index}].path")
            shard = _load(target / shard_path)
            if shard.get("schema_version") != 1 or shard.get("shard_kind") != SHARD_KIND:
                raise ImpactGraphError(f"invalid consistency shard: {shard_path}")
            if shard.get("id") != shard_id:
                raise ImpactGraphError(f"consistency shard ID differs from index: {shard_path}")
            shard_nodes = shard.get("nodes")
            if not isinstance(shard_nodes, list):
                raise ImpactGraphError(f"consistency shard nodes must be a list: {shard_path}")
            nodes.extend(shard_nodes)
            documents.append((shard_path, shard))
            source_paths.append(shard_path)
    else:
        raise ImpactGraphError("unsupported consistency-map schema_version")

    by_id: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ImpactGraphError(f"node[{index}] must be an object")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            raise ImpactGraphError(f"node[{index}].id must be non-empty")
        if node_id in by_id:
            raise ImpactGraphError(f"duplicate consistency node: {node_id}")
        by_id[node_id] = node
    return ImpactGraph(
        root=root,
        nodes=by_id,
        graph_digest=f"sha256:{_digest_documents(documents)}",
        source_paths=tuple(source_paths),
    )


def validate_graph(graph: ImpactGraph, *, allow_placeholders: bool = False) -> list[str]:
    failures: list[str] = []
    for node_id, node in graph.nodes.items():
        if "{" in node_id and allow_placeholders:
            continue
        level = node.get("level")
        if level not in GRAPH_LEVELS and not (
            allow_placeholders and isinstance(level, str) and "{" in level
        ):
            failures.append(f"node {node_id} has invalid level {level!r}")
        coverage = node.get("coverage_state", "mapped" if graph.root.get("schema_version") < 3 else None)
        if coverage not in COVERAGE_STATES:
            failures.append(f"node {node_id} has invalid coverage_state {coverage!r}")
        bindings = node.get("bindings", [])
        if not isinstance(bindings, list):
            failures.append(f"node {node_id} bindings must be a list")
            bindings = []
        for binding in bindings:
            if not isinstance(binding, dict):
                failures.append(f"node {node_id} has a non-object binding")
                continue
            selector_kind = binding.get("selector_kind")
            if selector_kind not in BINDING_KINDS and not (
                allow_placeholders
                and isinstance(selector_kind, str)
                and "{" in selector_kind
            ):
                failures.append(f"node {node_id} has invalid selector_kind")
            try:
                _safe_path(binding.get("path"), f"node {node_id} binding path")
            except ImpactGraphError as exc:
                if not (allow_placeholders and "{" in str(binding.get("path"))):
                    failures.append(str(exc))
        relationships = node.get("relationships")
        if not isinstance(relationships, list):
            failures.append(f"node {node_id} relationships must be a list")
            continue
        if not relationships and coverage == "mapped":
            failures.append(f"mapped node {node_id} must have a relationship")
        for relationship in relationships:
            if not isinstance(relationship, dict):
                failures.append(f"node {node_id} has a non-object relationship")
                continue
            state = relationship.get("state", "accepted" if graph.root.get("schema_version") < 3 else None)
            if state not in RELATIONSHIP_STATES:
                failures.append(f"node {node_id} has invalid relationship state")
            target_id = relationship.get("target")
            if (
                state in ACTIVE_RELATIONSHIP_STATES
                and target_id not in graph.nodes
                and not (allow_placeholders and isinstance(target_id, str) and "{" in target_id)
            ):
                failures.append(
                    f"accepted relationship {relationship.get('id')} targets missing node {target_id!r}"
                )
    return failures


def build_reverse_index(graph: ImpactGraph) -> dict[str, Any]:
    exact: dict[str, list[str]] = {}
    patterns: list[dict[str, Any]] = []
    for node_id, node in sorted(graph.nodes.items()):
        for binding in node.get("bindings", []):
            if not isinstance(binding, dict):
                continue
            path = binding.get("path")
            kind = binding.get("selector_kind")
            if not isinstance(path, str) or not path or "{" in path:
                continue
            entry = {
                "node_id": node_id,
                "binding_id": binding.get("id"),
                "surface_kind": binding.get("surface_kind"),
                "context_ids": binding.get("context_ids", []),
            }
            if kind == "file" and not any(marker in path for marker in "*?["):
                exact.setdefault(path, []).append(node_id)
            else:
                patterns.append({"pattern": path, **entry})
    return {
        "schema_version": 1,
        "index_kind": REVERSE_KIND,
        "graph_digest": graph.graph_digest,
        "exact_paths": {path: sorted(set(ids)) for path, ids in sorted(exact.items())},
        "patterns": patterns,
    }


def matching_node_ids(reverse_index: dict[str, Any], relpath: str) -> set[str]:
    matches = set(reverse_index.get("exact_paths", {}).get(relpath, []))
    for item in reverse_index.get("patterns", []):
        if not isinstance(item, dict):
            continue
        pattern = item.get("pattern")
        node_id = item.get("node_id")
        if (
            isinstance(pattern, str)
            and isinstance(node_id, str)
            and PathSpec(pattern, PathDialect.PORTABLE_FNMATCH_V1).matches(relpath)
        ):
            matches.add(node_id)
    return matches


def traverse_impact(
    graph: ImpactGraph,
    start_ids: Iterable[str],
    *,
    max_depth: int = 4,
    max_nodes: int = 100,
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    selected: list[str] = []
    selected_edges: list[dict[str, Any]] = []
    skipped_edges: list[dict[str, Any]] = []
    queue = [(node_id, 0) for node_id in sorted(set(start_ids)) if node_id in graph.nodes]
    seen: set[str] = set()
    while queue:
        node_id, depth = queue.pop(0)
        if node_id in seen:
            continue
        if len(seen) >= max_nodes:
            raise ImpactGraphError(f"impact closure exceeds max_nodes={max_nodes}")
        seen.add(node_id)
        selected.append(node_id)
        node = graph.nodes[node_id]
        for relationship in node.get("relationships", []):
            if not isinstance(relationship, dict):
                continue
            state = relationship.get("state", "accepted")
            edge = {
                "source": node_id,
                "id": relationship.get("id"),
                "target": relationship.get("target"),
                "type": relationship.get("type"),
                "state": state,
            }
            if state != "accepted":
                skipped_edges.append({**edge, "reason": "relationship-not-accepted"})
                continue
            if depth >= max_depth:
                skipped_edges.append({**edge, "reason": "depth-limit"})
                continue
            target_id = relationship.get("target")
            if target_id not in graph.nodes:
                skipped_edges.append({**edge, "reason": "missing-target"})
                continue
            selected_edges.append(edge)
            queue.append((target_id, depth + 1))
    return selected, selected_edges, skipped_edges


def render_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True) + "\n"

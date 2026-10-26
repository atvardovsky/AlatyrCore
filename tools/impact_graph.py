"""Load sharded target consistency graphs and derive reverse impact routing."""

from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from path_spec import PathDialect, PathSpec, logical_path
from context_input_snapshot import ContextInputChanged, read_context_bytes


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
CHANGE_KINDS = {
    "business-rule", "api-contract", "persistence", "architecture",
    "documentation", "testing", "configuration", "ai-infrastructure",
}
ASSOCIATION_TYPES = {"implements", "verifies", "documents", "visualizes", "generates", "routes"}
SUPPORT_INFORMATION_PREFIXES = (
    ".ai/",
    ".agents/",
    ".cursor/",
    ".devin/",
    ".github/prompts/",
    ".roo/",
    ".windsurf/",
)
SUPPORT_INFORMATION_FILES = {
    "AGENT.md",
    "AGENTS.md",
    "AI_ASSISTANTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "GIGACODE.md",
    ".cursorrules",
    ".rules",
    ".windsurfrules",
    ".github/copilot-instructions.md",
}


class ImpactGraphError(ValueError):
    """Raised when a target impact graph is structurally unsafe."""


@dataclass(frozen=True)
class ImpactGraph:
    root: dict[str, Any]
    nodes: dict[str, dict[str, Any]]
    graph_digest: str
    source_paths: tuple[str, ...]
    node_sources: dict[str, str] = field(default_factory=dict)
    source_stamps: dict[str, tuple[int, ...]] = field(default_factory=dict)
    source_digests: dict[str, str] = field(default_factory=dict)


def _stamp(path: Path) -> tuple[int, ...]:
    value = path.stat()
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def _load(path: Path, stamps: dict[str, tuple[int, ...]], digests: dict[str, str], relpath: str) -> dict[str, Any]:
    try:
        before = _stamp(path)
        content = read_context_bytes(path)
        data = json.loads(content.decode("utf-8"))
        after = _stamp(path)
    except ContextInputChanged:
        raise
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise ImpactGraphError(f"cannot load {path}: {exc}") from exc
    if before != after:
        raise ImpactGraphError(f"consistency input changed during reading: {relpath}")
    stamps[relpath] = after
    digests[relpath] = hashlib.sha256(content).hexdigest()
    if not isinstance(data, dict):
        raise ImpactGraphError(f"{path} must contain a JSON object")
    return data


def _safe_path(value: Any, label: str) -> str:
    try:
        return logical_path(value, pattern=True)
    except ValueError as exc:
        raise ImpactGraphError(f"{label}: {exc}") from exc


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
    stamps: dict[str, tuple[int, ...]] = {}
    digests: dict[str, str] = {}

    def read(path: str) -> dict[str, Any]:
        _safe_path(path, "consistency source")
        candidate = target / path
        if any(parent.is_symlink() for parent in (candidate, *candidate.parents) if parent != target and target in parent.parents):
            raise ImpactGraphError(f"consistency source must not traverse a symlink: {path}")
        return _load(candidate, stamps, digests, path)

    root = read(relpath)
    if root.get("map_kind") != GRAPH_KIND:
        raise ImpactGraphError("consistency map has an invalid map_kind")
    schema_version = root.get("schema_version")
    documents: list[tuple[str, dict[str, Any]]] = [(relpath, root)]
    nodes: list[Any]
    source_paths = [relpath]
    node_sources: dict[str, str] = {}
    if type(schema_version) is not int:
        raise ImpactGraphError("consistency-map schema_version must be an integer")
    if schema_version in {1, 2}:
        nodes = root.get("nodes", [])
        if not isinstance(nodes, list):
            raise ImpactGraphError("consistency-map nodes must be a list")
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
            shard = read(shard_path)
            if type(shard.get("schema_version")) is not int or shard["schema_version"] != 1 or shard.get("shard_kind") != SHARD_KIND:
                raise ImpactGraphError(f"invalid consistency shard: {shard_path}")
            if shard.get("id") != shard_id:
                raise ImpactGraphError(f"consistency shard ID differs from index: {shard_path}")
            shard_nodes = shard.get("nodes")
            if not isinstance(shard_nodes, list):
                raise ImpactGraphError(f"consistency shard nodes must be a list: {shard_path}")
            nodes.extend(shard_nodes)
            for node in shard_nodes:
                if isinstance(node, dict) and isinstance(node.get("id"), str):
                    node_sources[node["id"]] = shard_path
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
        node_sources=node_sources,
        source_stamps=stamps,
        source_digests=digests,
    )


def validate_graph(graph: ImpactGraph, *, allow_placeholders: bool = False) -> list[str]:
    failures: list[str] = []
    policy = graph.root.get("impact_policy", {})
    if not isinstance(policy, dict):
        failures.append("impact_policy must be an object")
        policy = {}
    if "routing_semantics" in policy and (type(policy["routing_semantics"]) is not int or policy["routing_semantics"] != 1):
        failures.append("impact_policy.routing_semantics must be 1 when present")
    for name, minimum in (("max_depth", 0), ("max_nodes", 1)):
        if name in policy and (type(policy[name]) is not int or policy[name] < minimum):
            failures.append(f"impact_policy.{name} must be an integer >= {minimum}")
    for node_id, node in graph.nodes.items():
        if "{" in node_id and allow_placeholders:
            continue
        level = node.get("level")
        if level not in GRAPH_LEVELS and not (
            allow_placeholders and isinstance(level, str) and "{" in level
        ):
            failures.append(f"node {node_id} has invalid level {level!r}")
        coverage = node.get("coverage_state", "mapped" if graph.root.get("schema_version") in (1, 2) else None)
        if not isinstance(coverage, str) or coverage not in COVERAGE_STATES:
            failures.append(f"node {node_id} has invalid coverage_state {coverage!r}")
        bindings = node.get("bindings", [])
        if not isinstance(bindings, list):
            failures.append(f"node {node_id} bindings must be a list")
            bindings = []
        if coverage == "mapped" and not bindings:
            failures.append(f"mapped node {node_id} must have a binding")
        for binding in bindings:
            if not isinstance(binding, dict):
                failures.append(f"node {node_id} has a non-object binding")
                continue
            selector_kind = binding.get("selector_kind")
            if "context_ids" in binding and (not isinstance(binding["context_ids"], list)
                    or any(not isinstance(value, str) or not value for value in binding["context_ids"])):
                failures.append(f"node {node_id} context_ids must be a string list")
            if (not isinstance(selector_kind, str) or selector_kind not in BINDING_KINDS) and not (
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
            state = relationship.get("state", "accepted" if graph.root.get("schema_version") in (1, 2) else None)
            if not isinstance(state, str) or state not in RELATIONSHIP_STATES:
                failures.append(f"node {node_id} has invalid relationship state")
            if not isinstance(relationship.get("type"), str) or not relationship["type"]:
                failures.append(f"node {node_id} relationship type must be a non-empty string")
            target_id = relationship.get("target")
            if (
                state == "accepted"
                and (not isinstance(target_id, str) or target_id not in graph.nodes)
                and not (allow_placeholders and isinstance(target_id, str) and "{" in target_id)
            ):
                failures.append(
                    f"accepted relationship {relationship.get('id')} targets missing node {target_id!r}"
                )
            condition = relationship.get("applicability")
            if "applicability" in relationship and (
                policy.get("routing_semantics") != 1
                or not isinstance(condition, dict)
                or set(condition) != {"change_kinds"}
                or not isinstance(condition.get("change_kinds"), list)
                or not condition["change_kinds"]
                or any(not isinstance(value, str) or value not in CHANGE_KINDS for value in condition["change_kinds"])
                or len(set(condition["change_kinds"])) != len(condition["change_kinds"])
            ):
                failures.append(f"relationship {relationship.get('id')} applicability requires routing_semantics 1 and unique supported change_kinds")
    return failures


def build_reverse_index(graph: ImpactGraph) -> dict[str, Any]:
    exact: dict[str, list[str]] = {}
    patterns: list[dict[str, Any]] = []
    for node_id, node in sorted(graph.nodes.items()):
        owner = node.get("canonical_owner")
        if isinstance(owner, str) and owner and "{" not in owner:
            exact.setdefault(owner.partition("#")[0], []).append(node_id)
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
            if kind != "glob":
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


def _compiled_patterns(reverse_index: dict[str, Any]) -> tuple[tuple[PathSpec, str], ...]:
    patterns = []
    for item in reverse_index.get("patterns", []):
        if not isinstance(item, dict):
            continue
        pattern = item.get("pattern")
        node_id = item.get("node_id")
        if isinstance(pattern, str) and isinstance(node_id, str):
            patterns.append((PathSpec(pattern, PathDialect.PORTABLE_FNMATCH_V1), node_id))
    return tuple(patterns)


def _matching(reverse_index: dict[str, Any], patterns: tuple[tuple[PathSpec, str], ...], relpath: str) -> set[str]:
    matches = set(reverse_index.get("exact_paths", {}).get(relpath, []))
    matches.update(node_id for pattern, node_id in patterns if pattern.matches(relpath))
    return matches


def matching_node_ids(reverse_index: dict[str, Any], relpath: str) -> set[str]:
    return _matching(reverse_index, _compiled_patterns(reverse_index), relpath)


def is_support_information_path(relpath: str) -> bool:
    normalized = relpath.replace("\\", "/")
    return normalized in SUPPORT_INFORMATION_FILES or normalized.startswith(
        SUPPORT_INFORMATION_PREFIXES
    )


def map_changed_paths(
    reverse_index: dict[str, Any],
    changed_paths: Iterable[str],
) -> tuple[dict[str, list[str]], list[str]]:
    """Map project paths and return fail-closed unmapped project surfaces."""

    patterns = _compiled_patterns(reverse_index)
    matches = {
        path: sorted(_matching(reverse_index, patterns, path))
        for path in sorted(set(changed_paths))
    }
    unmapped = [
        path
        for path, node_ids in matches.items()
        if not node_ids and not is_support_information_path(path)
    ]
    return matches, unmapped


def _effective_state(graph: ImpactGraph, relation: dict[str, Any]) -> Any:
    return relation.get("state", "accepted" if graph.root.get("schema_version") in (1, 2) else None)


def _classified_changes(change_kinds: Iterable[str]) -> set[str]:
    values = list(change_kinds)
    if any(not isinstance(kind, str) or kind not in CHANGE_KINDS for kind in values):
        raise ImpactGraphError("unsupported change kind")
    return set(values)


def _edge_applies(relation: dict[str, Any], changes: set[str], typed: bool) -> bool:
    condition = relation.get("applicability")
    return not (typed and changes and condition is not None and not changes.intersection(condition["change_kinds"]))


def traverse_impact(
    graph: ImpactGraph, start_ids: Iterable[str], *, max_depth: int = 4,
    max_nodes: int = 100, change_kinds: Iterable[str] = (),
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    failures = validate_graph(graph)
    if failures:
        raise ImpactGraphError("; ".join(failures))
    return _traverse_impact(graph, start_ids, max_depth=max_depth, max_nodes=max_nodes, change_kinds=change_kinds)


def _traverse_impact(
    graph: ImpactGraph,
    start_ids: Iterable[str],
    *,
    max_depth: int = 4,
    max_nodes: int = 100,
    change_kinds: Iterable[str] = (),
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    if type(max_depth) is not int or max_depth < 0 or type(max_nodes) is not int or max_nodes < 1:
        raise ImpactGraphError("impact limits require non-negative max_depth and positive max_nodes")
    changes = _classified_changes(change_kinds)
    typed = graph.root.get("impact_policy", {}).get("routing_semantics") == 1
    incoming_dependencies: dict[str, list[dict[str, Any]]] = {}
    if typed:
        for source, node in graph.nodes.items():
            for relation in node.get("relationships", []):
                if _effective_state(graph, relation) == "accepted" and relation.get("type") == "depends-on":
                    incoming_dependencies.setdefault(relation["target"], []).append({**relation, "source": source})
    selected: list[str] = []
    selected_edges: list[dict[str, Any]] = []
    skipped_edges: list[dict[str, Any]] = []
    starts = list(start_ids)
    if any(not isinstance(node_id, str) or node_id not in graph.nodes for node_id in starts):
        raise ImpactGraphError("impact traversal requires known string node IDs")
    queue = deque((node_id, 0) for node_id in sorted(set(starts)))
    discovered = {node_id for node_id, _ in queue}
    seen: set[str] = set()
    while queue:
        node_id, depth = queue.popleft()
        if node_id in seen:
            continue
        if len(seen) >= max_nodes:
            raise ImpactGraphError(f"impact closure exceeds max_nodes={max_nodes}")
        seen.add(node_id)
        selected.append(node_id)
        node = graph.nodes[node_id]
        relations = [(relation, "outbound") for relation in node.get("relationships", [])]
        relations.extend((relation, "dependent") for relation in incoming_dependencies.get(node_id, []))
        for relationship, traversal in relations:
            if not isinstance(relationship, dict):
                continue
            state = _effective_state(graph, relationship)
            edge = {
                "source": node_id,
                "id": relationship.get("id"),
                "target": relationship.get("source") if traversal == "dependent" else relationship.get("target"),
                "type": relationship.get("type"),
                "state": state,
            }
            if traversal == "dependent":
                edge["traversal"] = "dependent"
            for name in ("validation", "approval_trigger", "conditions", "applicability"):
                if name in relationship:
                    edge[name] = relationship[name]
            if typed:
                edge["routing_role"] = ("semantic-propagation" if edge["type"] in {"depends-on", "constrains"}
                                        else "navigation" if edge["type"] == "routes" else "companion-surface")
            if state != "accepted":
                skipped_edges.append({**edge, "reason": "relationship-not-accepted"})
                continue
            if not _edge_applies(relationship, changes, typed):
                skipped_edges.append({**edge, "reason": "condition-not-applicable"})
                continue
            target_id = edge["target"]
            if depth >= max_depth and target_id not in discovered:
                skipped_edges.append({**edge, "reason": "depth-limit"})
                continue
            if target_id not in graph.nodes:
                skipped_edges.append({**edge, "reason": "missing-target"})
                continue
            selected_edges.append(edge)
            if target_id not in discovered:
                discovered.add(target_id)
                queue.append((target_id, depth + 1))
    return selected, selected_edges, skipped_edges


class ImpactLookup:
    """Invocation-scoped indexes; no persistent evidence or authorization cache."""

    def __init__(self, graph: ImpactGraph, reverse: dict[str, Any] | None = None):
        failures = validate_graph(graph)
        if failures:
            raise ImpactGraphError("; ".join(failures))
        self.graph = graph
        self.reverse = build_reverse_index(graph)
        if reverse is not None and reverse != self.reverse:
            raise ImpactGraphError("consistency reverse index differs from the active graph")
        self.patterns = _compiled_patterns(self.reverse)
        self.associations: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        self._matches: dict[str, frozenset[str]] = {}
        for source, node in graph.nodes.items():
            for relation in node["relationships"]:
                if (_effective_state(graph, relation) == "accepted"
                        and isinstance(relation.get("type"), str) and relation["type"] in ASSOCIATION_TYPES
                        and node.get("level") in {"fact", "contract"}):
                    self.associations.setdefault(relation["target"], []).append((source, relation))

    def matching(self, path: str) -> set[str]:
        if path in self._matches:
            return set(self._matches[path])
        result = _matching(self.reverse, self.patterns, path)
        self._matches[path] = frozenset(result)
        return result

    def resolve(self, paths: Iterable[str], fact_ids: Iterable[str] = (), *,
                max_depth: int = 4, max_nodes: int = 100,
                change_kinds: Iterable[str] = ()) -> dict[str, Any]:
        paths, fact_ids = list(paths), list(fact_ids)
        if any(not isinstance(value, str) or not value for value in paths + fact_ids):
            raise ImpactGraphError("changed paths and fact IDs must be non-empty strings")
        matches = {path: sorted(self.matching(path)) for path in sorted(set(paths))}
        starts = set(fact_ids)
        for ids in matches.values():
            starts.update(ids)
        unknown = sorted(starts - self.graph.nodes.keys())
        if unknown:
            raise ImpactGraphError("unknown fact IDs: " + ", ".join(unknown))
        changes = _classified_changes(change_kinds)
        typed = self.graph.root.get("impact_policy", {}).get("routing_semantics") == 1
        looked_up, lookup_skips = set(), []
        # Association lookup names candidate owning facts, never changes ownership.
        for node_id in sorted(starts):
            for owner, relation in self.associations.get(node_id, []):
                if _edge_applies(relation, changes, typed):
                    looked_up.add(owner)
                else:
                    lookup_skips.append({"source": owner, "target": node_id, "id": relation.get("id"),
                        "type": relation["type"], "state": "accepted", "traversal": "owner-lookup",
                        "reason": "condition-not-applicable", "applicability": relation["applicability"]})
        looked_up = sorted(looked_up - starts)
        nodes, edges, skipped = _traverse_impact(self.graph, starts | set(looked_up),
            max_depth=max_depth, max_nodes=max_nodes, change_kinds=changes)
        skipped.extend(lookup_skips)
        review = [{"node_id": node_id, "reason": "known-relationship-gap"} for node_id in nodes
                  if self.graph.nodes[node_id].get("coverage_state") == "known-gap"]
        review.extend({"edge_id": edge["id"], "reason": "free-text-condition-included", "condition": edge["conditions"]}
                      for edge in edges if "conditions" in edge and "applicability" not in edge)
        review.extend({"edge_id": edge["id"], "reason": "unclassified-condition-included"}
                      for edge in edges if "applicability" in edge and not changes)
        return {"path_matches": matches, "owner_lookup_node_ids": looked_up,
                "selected_node_ids": nodes, "selected_edges": edges, "skipped_edges": skipped,
                "review_required": review}


def relationship_review_paths(paths: Iterable[str]) -> list[str]:
    """Mapped files can introduce relationships too; review is not promotion."""
    suffixes = {".py", ".php", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".go", ".rs", ".cs", ".sql", ".graphql", ".proto"}
    contracts = {".json", ".yaml", ".yml", ".toml", ".avsc", ".prisma", ".thrift", ".xsd", ".wsdl"}
    return sorted({path for path in paths if PurePosixPath(path).suffix.casefold() in suffixes
                   or (not is_support_information_path(path) and PurePosixPath(path).suffix.casefold() in contracts)})


def assert_graph_current(graph: ImpactGraph, target: Path) -> None:
    """Retain whole-graph input freshness while delivering only selected shards."""
    for path, stamp in graph.source_stamps.items():
        try:
            current = _stamp(target / path)
        except OSError as exc:
            raise ImpactGraphError(f"consistency input unavailable after lookup: {path}") from exc
        if current != stamp:
            raise ImpactGraphError(f"consistency input changed during lookup: {path}")
        expected = graph.source_digests[path]
        try:
            digest = hashlib.sha256(read_context_bytes(target / path)).hexdigest()
        except OSError as exc:
            raise ImpactGraphError(f"consistency input unavailable after lookup: {path}") from exc
        if digest != expected:
            raise ImpactGraphError(f"consistency input changed during lookup: {path}")


def render_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True) + "\n"

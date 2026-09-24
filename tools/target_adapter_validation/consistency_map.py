"""Consistency-map capability validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema

from target_adapter_validation.capability import CapabilityValidationContext
from target_adapter_validation.context import TargetPathEscapeError
from target_adapter_validation.source_contracts import load_source_json_object
from target_validation_support import (
    expect_string_list,
    is_placeholder,
    is_target_relative_path,
    is_unresolved_value,
)
from impact_graph import (
    ImpactGraph,
    ImpactGraphError,
    build_reverse_index,
    load_impact_graph,
    validate_graph,
)
from path_spec import PathDialect, PathSpec
from repository_inventory import RepositoryInventory, RepositoryInventoryError


CONSISTENCY_LEVELS = ["fact", "contract", "area", "system", "adapter"]
CONSISTENCY_LEVELS_V3 = [*CONSISTENCY_LEVELS, "surface"]
CONSISTENCY_RELATIONSHIPS = {
    "implements",
    "verifies",
    "documents",
    "visualizes",
    "generates",
    "constrains",
    "depends-on",
    "routes",
}
CONSISTENCY_REGISTRY_SYNC_POLICY = {
    "coverage": "every-live-registry-fact-type",
    "node_reference": "registry-consistency-map-node-id",
    "fact_type_match": "exact",
    "extra_nodes": "allowed-for-derived-contract-area-system-and-adapter-surfaces",
}
CONSISTENCY_REGISTRY_SYNC_POLICY_V3 = {
    "coverage": "every-live-registry-fact-type",
    "node_reference": "registry-consistency-map-node-id",
    "fact_type_match": "exact",
    "extra_nodes": "allowed-for-derived-contract-area-system-adapter-and-surface-nodes",
}
REGISTRY_ENTRY_HEADING_RE = re.compile(
    r"^### Fact Type: `([^`]+)`\s*$", re.MULTILINE
)
RELATIONSHIP_CANDIDATES_SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "alatyr-relationship-candidates.schema.json"
)


@dataclass(frozen=True)
class RegistryFactEntry:
    heading_fact_type: str
    declared_fact_type: str | None
    map_node_id: str | None
    canonical_owner_values: tuple[str, ...]
    line: int


def markdown_scalar(block: str, field: str) -> str | None:
    match = re.search(
        rf"^{re.escape(field)}:\s*(.*?)\s*$",
        block,
        flags=re.MULTILINE,
    )
    if match is None:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip()
    return value or None


def compact_markdown_scalar(
    block: str, group: str, *keys: str
) -> str | None:
    line = re.search(rf"^{re.escape(group)}:\s*(.*?)\s*$", block, re.MULTILINE)
    if line is None:
        return None
    for key in keys:
        match = re.search(
            rf"(?:^|;\s*){re.escape(key)}=`([^`]*)`", line.group(1)
        )
        if match is not None:
            return match.group(1).strip()
    return None


def parse_registry_fact_entries(text: str) -> list[RegistryFactEntry]:
    matches = list(REGISTRY_ENTRY_HEADING_RE.finditer(text))
    entries: list[RegistryFactEntry] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end():end]
        owner_values = tuple(
            value.strip().strip("`")
            for _field, value in re.findall(
                r"^([^:\n]*owner):\s*(.*?)\s*$",
                block,
                flags=re.MULTILINE | re.IGNORECASE,
            )
            if value.strip()
        )
        entries.append(
            RegistryFactEntry(
                heading_fact_type=match.group(1).strip(),
                declared_fact_type=markdown_scalar(block, "Fact type"),
                map_node_id=markdown_scalar(block, "Consistency map node")
                or compact_markdown_scalar(
                    block, "Routing", "consistency_node", "cn"
                ),
                canonical_owner_values=owner_values,
                line=text.count("\n", 0, match.start()) + 1,
            )
        )
    return entries


def _manifest_schema_version(manifest: Any) -> int | None:
    if manifest is None:
        return None
    scalar = manifest.scalars.get(("schema_version",))
    if scalar is None:
        return None
    try:
        return int(scalar.value)
    except ValueError:
        return None


def _validate_map_header(
    context: CapabilityValidationContext,
    data: dict[str, Any],
    schema_version: Any,
    adapter_schema_version: int | None,
    relpath: str,
) -> list[str]:
    if (
        adapter_schema_version is not None
        and adapter_schema_version >= 31
        and schema_version != 3
    ):
        context.error(
            "CONSISTENCY_MAP_SCHEMA_MIGRATION_REQUIRED",
            "adapter schema 31 and newer require sharded consistency-map schema version 3",
            relpath,
        )
    if schema_version == 1:
        context.warn(
            "CONSISTENCY_MAP_SCHEMA_LEGACY",
            "schema_version 1 should migrate to schema 2 registry-sync policy",
            relpath,
        )
    elif schema_version not in {2, 3}:
        context.error(
            "CONSISTENCY_MAP_SCHEMA",
            "schema_version should be 1, 2, or 3",
            relpath,
        )
    if data.get("map_kind") != "target-consistency-map":
        context.error(
            "CONSISTENCY_MAP_KIND",
            "map_kind should be target-consistency-map",
            relpath,
        )
    if data.get("human_registry") != ".ai/project/source-of-truth-registry.md":
        context.error(
            "CONSISTENCY_MAP_REGISTRY",
            "human_registry should point to the target source-of-truth registry",
            relpath,
        )
    expected_sync_policy = (
        CONSISTENCY_REGISTRY_SYNC_POLICY_V3
        if schema_version == 3
        else CONSISTENCY_REGISTRY_SYNC_POLICY
    )
    if (
        schema_version in {2, 3}
        and data.get("registry_sync_policy") != expected_sync_policy
    ):
        context.error(
            "CONSISTENCY_MAP_REGISTRY_SYNC_POLICY",
            "registry_sync_policy must require exact coverage while allowing "
            "extra derived nodes",
            relpath,
        )
    expected_levels = (
        CONSISTENCY_LEVELS_V3 if schema_version == 3 else CONSISTENCY_LEVELS
    )
    if data.get("levels") != expected_levels:
        context.error(
            "CONSISTENCY_MAP_LEVELS",
            "levels must match the portable consistency level order",
            relpath,
        )
    relationships = data.get("relationship_types")
    if (
        not isinstance(relationships, list)
        or not all(isinstance(value, str) for value in relationships)
        or set(relationships) != CONSISTENCY_RELATIONSHIPS
    ):
        context.error(
            "CONSISTENCY_MAP_RELATIONSHIPS",
            "relationship_types must match the portable relationship set",
            relpath,
        )
    policy = data.get("impact_policy")
    if not isinstance(policy, dict):
        context.error(
            "CONSISTENCY_MAP_IMPACT_POLICY",
            "impact_policy must be an object",
            relpath,
        )
    else:
        for field in ["transitive_expand_when", "required_evidence"]:
            expect_string_list(
                policy.get(field),
                context,
                "CONSISTENCY_MAP_IMPACT_POLICY",
                relpath,
                label=f"impact_policy.{field}",
            )
    return expected_levels


def _validate_graph_bindings(
    context: CapabilityValidationContext,
    graph: ImpactGraph,
    relpath: str,
) -> None:
    try:
        repository_paths = RepositoryInventory.load(context.target).paths
    except RepositoryInventoryError as exc:
        context.error(
            "CONSISTENCY_MAP_BINDING_INVENTORY",
            f"cannot verify consistency-map bindings: {exc}",
            relpath,
        )
        return
    for node_id, node in graph.nodes.items():
        if node.get("coverage_state") != "mapped":
            continue
        for binding in node.get("bindings", []):
            if not isinstance(binding, dict):
                continue
            path_value = binding.get("path")
            if not isinstance(path_value, str) or is_placeholder(path_value):
                continue
            if binding.get("selector_kind") == "glob":
                path_spec = PathSpec(path_value, PathDialect.PORTABLE_FNMATCH_V1)
                matches = (
                    candidate
                    for candidate in repository_paths
                    if path_spec.matches(candidate)
                )
            else:
                matches = (path_value,) if path_value in repository_paths else ()
            try:
                matched = any(
                    context.target_exists(candidate) for candidate in matches
                )
            except TargetPathEscapeError as exc:
                context.error(
                    "CONSISTENCY_MAP_BINDING_UNSAFE",
                    f"mapped node {node_id!r} binding escapes the target: {exc}",
                    relpath,
                )
                continue
            if not matched:
                context.error(
                    "CONSISTENCY_MAP_BINDING_UNMATCHED",
                    f"mapped node {node_id!r} binding {path_value!r} "
                    "matches no current repository path",
                    relpath,
                )


def _validate_reverse_index(
    context: CapabilityValidationContext,
    data: dict[str, Any],
    graph: ImpactGraph,
) -> None:
    reverse_relpath = data.get("reverse_index")
    if not isinstance(reverse_relpath, str):
        return
    reverse = context.load_json_object(
        context.target_path(reverse_relpath), "CONSISTENCY_REVERSE_INDEX"
    )
    expected_reverse = build_reverse_index(graph)
    if reverse is None or reverse == expected_reverse:
        return
    unresolved = isinstance(reverse.get("graph_digest"), str) and is_placeholder(
        reverse.get("graph_digest")
    )
    report = (
        context.warn
        if context.allow_placeholders and unresolved
        else context.error
    )
    report(
        "CONSISTENCY_REVERSE_INDEX_STALE",
        "generated reverse index differs from consistency-map shards",
        reverse_relpath,
    )


def _validate_relationship_candidates(
    context: CapabilityValidationContext,
    data: dict[str, Any],
    graph: ImpactGraph,
) -> None:
    candidates_relpath = data.get("relationship_candidates")
    if not isinstance(candidates_relpath, str):
        return
    candidates = context.load_json_object(
        context.target_path(candidates_relpath),
        "CONSISTENCY_RELATIONSHIP_CANDIDATES",
    )
    if candidates is None:
        return
    try:
        candidates_schema = load_source_json_object(
            RELATIONSHIP_CANDIDATES_SCHEMA
        )
        candidate_errors = sorted(
            jsonschema.Draft7Validator(candidates_schema).iter_errors(candidates),
            key=lambda error: list(error.absolute_path),
        )
    except (OSError, ValueError, jsonschema.SchemaError) as exc:
        context.error(
            "CONSISTENCY_RELATIONSHIP_CANDIDATES_SCHEMA",
            f"cannot validate relationship candidates: {exc}",
            candidates_relpath,
        )
        candidate_errors = []
    for error in candidate_errors:
        location = ".".join(str(item) for item in error.absolute_path) or "root"
        context.error(
            "CONSISTENCY_RELATIONSHIP_CANDIDATES",
            f"relationship candidates {location}: {error.message}",
            candidates_relpath,
        )
    candidate_ids: set[str] = set()
    for candidate in candidates.get("records", []):
        if not isinstance(candidate, dict):
            continue
        candidate_id = candidate.get("id")
        if isinstance(candidate_id, str):
            if candidate_id in candidate_ids:
                context.error(
                    "CONSISTENCY_RELATIONSHIP_CANDIDATE_DUPLICATE",
                    f"relationship candidate id is repeated: {candidate_id}",
                    candidates_relpath,
                )
            candidate_ids.add(candidate_id)
        relationship_type = candidate.get("relationship_type")
        if relationship_type not in CONSISTENCY_RELATIONSHIPS:
            context.error(
                "CONSISTENCY_RELATIONSHIP_CANDIDATE_TYPE",
                f"relationship candidate {candidate_id!r} has unsupported type "
                f"{relationship_type!r}",
                candidates_relpath,
            )
        for endpoint in ["source_node", "target_node"]:
            node_id = candidate.get(endpoint)
            if (
                isinstance(node_id, str)
                and not is_placeholder(node_id)
                and node_id not in graph.nodes
            ):
                context.error(
                    "CONSISTENCY_RELATIONSHIP_CANDIDATE_NODE",
                    f"relationship candidate {candidate_id!r} references missing "
                    f"{endpoint} {node_id!r}",
                    candidates_relpath,
                )


def _load_v3_graph(
    context: CapabilityValidationContext,
    data: dict[str, Any],
    relpath: str,
) -> ImpactGraph | None:
    try:
        graph = load_impact_graph(context.target_path(".ai").parent, relpath)
    except ImpactGraphError as exc:
        context.error("CONSISTENCY_MAP_SHARDS", str(exc), relpath)
        return None
    for failure in validate_graph(
        graph, allow_placeholders=context.allow_placeholders
    ):
        context.error("CONSISTENCY_MAP_GRAPH", failure, relpath)
    _validate_graph_bindings(context, graph, relpath)
    _validate_reverse_index(context, data, graph)
    _validate_relationship_candidates(context, data, graph)
    return graph


def _validate_nodes(
    context: CapabilityValidationContext,
    nodes: Any,
    schema_version: Any,
    expected_levels: list[str],
    relpath: str,
) -> dict[str, dict[str, Any]] | None:
    if not isinstance(nodes, list) or not nodes:
        context.error(
            "CONSISTENCY_MAP_NODES", "nodes must be a non-empty list", relpath
        )
        return None
    node_ids: set[str] = set()
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edge_ids: set[str] = set()
    for index, node in enumerate(nodes):
        label = f"nodes[{index}]"
        if not isinstance(node, dict):
            context.error(
                "CONSISTENCY_MAP_NODE_SHAPE", f"{label} must be an object", relpath
            )
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            context.error(
                "CONSISTENCY_MAP_NODE_ID", f"{label}.id must be a string", relpath
            )
        elif not is_placeholder(node_id):
            if node_id in node_ids:
                context.error(
                    "CONSISTENCY_MAP_NODE_DUPLICATE",
                    f"duplicate node id {node_id}",
                    relpath,
                )
            node_ids.add(node_id)
            nodes_by_id[node_id] = node
        fact_type = node.get("fact_type")
        if not isinstance(fact_type, str) or not fact_type.strip():
            context.error(
                "CONSISTENCY_MAP_NODE_FACT_TYPE",
                f"{label}.fact_type must be a non-empty string",
                relpath,
            )
        elif is_placeholder(fact_type) and not context.allow_placeholders:
            context.error(
                "CONSISTENCY_MAP_NODE_FACT_TYPE",
                f"{label}.fact_type must be resolved in an accepted adapter",
                relpath,
            )
        level = node.get("level")
        if not is_placeholder(level) and level not in expected_levels:
            context.error(
                "CONSISTENCY_MAP_NODE_LEVEL",
                f"{label}.level is invalid: {level}",
                relpath,
            )
        project_area = node.get("project_area")
        if not isinstance(project_area, str) or not project_area.strip():
            context.error(
                "CONSISTENCY_MAP_NODE_AREA",
                f"{label}.project_area must be a non-empty string",
                relpath,
            )
        elif is_placeholder(project_area) and not context.allow_placeholders:
            context.error(
                "CONSISTENCY_MAP_NODE_AREA",
                f"{label}.project_area must be resolved in an accepted adapter",
                relpath,
            )
        owner = node.get("canonical_owner")
        if (
            isinstance(owner, str)
            and not is_placeholder(owner)
            and not is_unresolved_value(owner)
        ):
            if not is_target_relative_path(owner):
                context.error(
                    "CONSISTENCY_MAP_OWNER_PATH",
                    f"{label}.canonical_owner must be target-relative",
                    relpath,
                )
            elif not context.target_exists(owner):
                report = (
                    context.error
                    if node.get("coverage_state") == "mapped"
                    else context.warn
                )
                report(
                    "CONSISTENCY_MAP_OWNER_MISSING",
                    f"{label}.canonical_owner is missing: {owner}",
                    relpath,
                )
        edges = node.get("relationships")
        if not isinstance(edges, list):
            context.error(
                "CONSISTENCY_MAP_EDGES",
                f"{label}.relationships must be a list",
                relpath,
            )
            continue
        if not edges and schema_version != 3:
            context.error(
                "CONSISTENCY_MAP_EDGES",
                f"{label}.relationships must be non-empty",
                relpath,
            )
            continue
        for edge_index, edge in enumerate(edges):
            edge_label = f"{label}.relationships[{edge_index}]"
            if not isinstance(edge, dict):
                context.error(
                    "CONSISTENCY_MAP_EDGE_SHAPE",
                    f"{edge_label} must be an object",
                    relpath,
                )
                continue
            edge_id = edge.get("id")
            if not isinstance(edge_id, str) or not edge_id:
                context.error(
                    "CONSISTENCY_MAP_EDGE_ID",
                    f"{edge_label}.id must be a string",
                    relpath,
                )
            elif not is_placeholder(edge_id):
                if edge_id in edge_ids:
                    context.error(
                        "CONSISTENCY_MAP_EDGE_DUPLICATE",
                        f"duplicate relationship id {edge_id}",
                        relpath,
                    )
                edge_ids.add(edge_id)
            edge_type = edge.get("type")
            if (
                not is_placeholder(edge_type)
                and edge_type not in CONSISTENCY_RELATIONSHIPS
            ):
                context.error(
                    "CONSISTENCY_MAP_EDGE_TYPE",
                    f"{edge_label}.type is invalid: {edge_type}",
                    relpath,
                )
            target_level = edge.get("target_level")
            if (
                not is_placeholder(target_level)
                and target_level not in expected_levels
            ):
                context.error(
                    "CONSISTENCY_MAP_TARGET_LEVEL",
                    f"{edge_label}.target_level is invalid: {target_level}",
                    relpath,
                )
            if edge.get("direction") != "outbound":
                context.error(
                    "CONSISTENCY_MAP_DIRECTION",
                    f"{edge_label}.direction must be outbound",
                    relpath,
                )
            for field in ["required_when", "validation"]:
                expect_string_list(
                    edge.get(field),
                    context,
                    "CONSISTENCY_MAP_EDGE_FIELD",
                    relpath,
                    label=f"{edge_label}.{field}",
                )
    return nodes_by_id


def _validate_registry_sync(
    context: CapabilityValidationContext,
    nodes_by_id: dict[str, dict[str, Any]],
    relpath: str,
) -> None:
    registry_relpath = ".ai/project/source-of-truth-registry.md"
    registry_path = context.target_path(registry_relpath)
    if not context.is_target_file(registry_path):
        context.error(
            "CONSISTENCY_MAP_REGISTRY_MISSING",
            "enabled consistency map requires the human source-of-truth registry",
            registry_relpath,
        )
        return
    registry_entries = parse_registry_fact_entries(context.read_text(registry_path))
    if not registry_entries:
        context.error(
            "CONSISTENCY_MAP_REGISTRY_EMPTY",
            "source-of-truth registry has no Fact Type entries",
            registry_relpath,
        )
        return
    heading_counts: dict[str, int] = {}
    referenced_nodes: dict[str, str] = {}
    for entry in registry_entries:
        heading_counts[entry.heading_fact_type] = (
            heading_counts.get(entry.heading_fact_type, 0) + 1
        )
        entry_path = f"{registry_relpath}:{entry.line}"
        if entry.declared_fact_type != entry.heading_fact_type:
            context.error(
                "CONSISTENCY_REGISTRY_FACT_TYPE_DRIFT",
                "Fact type field must match its Fact Type heading exactly",
                entry_path,
            )
        node_id = entry.map_node_id
        if (
            not isinstance(node_id, str)
            or is_placeholder(node_id)
            or is_unresolved_value(node_id)
        ):
            report = context.warn if context.allow_placeholders else context.error
            report(
                "CONSISTENCY_REGISTRY_NODE_UNRESOLVED",
                f"Fact Type {entry.heading_fact_type!r} needs one resolved "
                "consistency-map node ID",
                entry_path,
            )
            continue
        previous_fact_type = referenced_nodes.get(node_id)
        if previous_fact_type is not None:
            context.error(
                "CONSISTENCY_REGISTRY_NODE_REUSED",
                f"node {node_id!r} is referenced by both "
                f"{previous_fact_type!r} and {entry.heading_fact_type!r}",
                entry_path,
            )
            continue
        referenced_nodes[node_id] = entry.heading_fact_type
        node = nodes_by_id.get(node_id)
        if node is None:
            context.error(
                "CONSISTENCY_REGISTRY_NODE_MISSING",
                f"Fact Type {entry.heading_fact_type!r} references missing node "
                f"{node_id!r}",
                entry_path,
            )
            continue
        if node.get("fact_type") != entry.heading_fact_type:
            context.error(
                "CONSISTENCY_REGISTRY_NODE_FACT_TYPE_DRIFT",
                f"node {node_id!r} fact_type must exactly match "
                f"{entry.heading_fact_type!r}",
                relpath,
            )
    for fact_type, count in sorted(heading_counts.items()):
        if count > 1:
            context.error(
                "CONSISTENCY_REGISTRY_FACT_TYPE_DUPLICATE",
                f"registry repeats Fact Type {fact_type!r}",
                registry_relpath,
            )


class ConsistencyMapModule:
    """Validate the optional consistency-map capability."""

    check_id = "check_consistency_map"

    def validate(
        self,
        context: CapabilityValidationContext,
        manifest: Any,
    ) -> None:
        relpath = ".ai/project/consistency-map.json"
        data = context.load_json_object(
            context.target_path(relpath), "CONSISTENCY_MAP"
        )
        if data is None:
            return
        schema_version = data.get("schema_version")
        expected_levels = _validate_map_header(
            context,
            data,
            schema_version,
            _manifest_schema_version(manifest),
            relpath,
        )
        graph: ImpactGraph | None = None
        if schema_version == 3:
            graph = _load_v3_graph(context, data, relpath)
        nodes = list(graph.nodes.values()) if graph is not None else data.get("nodes")
        nodes_by_id = _validate_nodes(
            context, nodes, schema_version, expected_levels, relpath
        )
        if nodes_by_id is None:
            return
        _validate_registry_sync(context, nodes_by_id, relpath)


CONSISTENCY_MAP_MODULE = ConsistencyMapModule()

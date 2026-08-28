"""Consistency-map capability validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from target_adapter_validation.capability import CapabilityValidationContext
from target_validation_support import (
    expect_string_list,
    is_placeholder,
    is_target_relative_path,
    is_unresolved_value,
)
from impact_graph import (
    ImpactGraphError,
    build_reverse_index,
    load_impact_graph,
    validate_graph,
)


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
                map_node_id=markdown_scalar(block, "Consistency map node"),
                canonical_owner_values=owner_values,
                line=text.count("\n", 0, match.start()) + 1,
            )
        )
    return entries


class ConsistencyMapModule:
    """Validate the optional consistency-map capability."""

    check_id = "check_consistency_map"

    def validate(
        self,
        context: CapabilityValidationContext,
        manifest: Any,
    ) -> None:
        relpath = ".ai/project/consistency-map.json"
        path = context.target_path(relpath)
        data = context.load_json_object(path, "CONSISTENCY_MAP")
        if data is None:
            return
        schema_version = data.get("schema_version")
        adapter_schema_version: int | None = None
        if manifest is not None:
            scalar = manifest.scalars.get(("schema_version",))
            if scalar is not None:
                try:
                    adapter_schema_version = int(scalar.value)
                except ValueError:
                    adapter_schema_version = None
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
        if schema_version in {2, 3} and data.get("registry_sync_policy") != expected_sync_policy:
            context.error(
                "CONSISTENCY_MAP_REGISTRY_SYNC_POLICY",
                "registry_sync_policy must require exact coverage while allowing "
                "extra derived nodes",
                relpath,
            )
        expected_levels = CONSISTENCY_LEVELS_V3 if schema_version == 3 else CONSISTENCY_LEVELS
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

        graph = None
        if schema_version == 3:
            try:
                graph = load_impact_graph(context.target_path(".ai").parent, relpath)
            except ImpactGraphError as exc:
                context.error("CONSISTENCY_MAP_SHARDS", str(exc), relpath)
            else:
                for failure in validate_graph(
                    graph, allow_placeholders=context.allow_placeholders
                ):
                    context.error("CONSISTENCY_MAP_GRAPH", failure, relpath)
                reverse_relpath = data.get("reverse_index")
                if isinstance(reverse_relpath, str):
                    reverse = context.load_json_object(
                        context.target_path(reverse_relpath), "CONSISTENCY_REVERSE_INDEX"
                    )
                    expected_reverse = build_reverse_index(graph)
                    if reverse is not None and reverse != expected_reverse:
                        unresolved = isinstance(reverse.get("graph_digest"), str) and is_placeholder(reverse.get("graph_digest"))
                        report = context.warn if context.allow_placeholders and unresolved else context.error
                        report(
                            "CONSISTENCY_REVERSE_INDEX_STALE",
                            "generated reverse index differs from consistency-map shards",
                            reverse_relpath,
                        )
                candidates_relpath = data.get("relationship_candidates")
                if isinstance(candidates_relpath, str):
                    candidates = context.load_json_object(
                        context.target_path(candidates_relpath),
                        "CONSISTENCY_RELATIONSHIP_CANDIDATES",
                    )
                    if candidates is not None and (
                        candidates.get("schema_version") != 1
                        or candidates.get("record_kind")
                        != "target-consistency-relationship-candidates"
                        or not isinstance(candidates.get("records"), list)
                    ):
                        context.error(
                            "CONSISTENCY_RELATIONSHIP_CANDIDATES",
                            "relationship candidates must use the non-authoritative schema-1 record",
                            candidates_relpath,
                        )
        nodes = list(graph.nodes.values()) if graph is not None else data.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            context.error(
                "CONSISTENCY_MAP_NODES", "nodes must be a non-empty list", relpath
            )
            return
        node_ids: set[str] = set()
        nodes_by_id: dict[str, dict[str, Any]] = {}
        edge_ids: set[str] = set()
        for index, node in enumerate(nodes):
            label = f"nodes[{index}]"
            if not isinstance(node, dict):
                context.error(
                    "CONSISTENCY_MAP_NODE_SHAPE",
                    f"{label} must be an object",
                    relpath,
                )
                continue
            node_id = node.get("id")
            if not isinstance(node_id, str) or not node_id:
                context.error(
                    "CONSISTENCY_MAP_NODE_ID",
                    f"{label}.id must be a string",
                    relpath,
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
                elif not context.target_path(owner).exists():
                    context.warn(
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

        registry_relpath = ".ai/project/source-of-truth-registry.md"
        registry_path = context.target_path(registry_relpath)
        if not registry_path.is_file():
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
                    f"Fact Type {entry.heading_fact_type!r} references missing node {node_id!r}",
                    entry_path,
                )
                continue
            if node.get("fact_type") != entry.heading_fact_type:
                context.error(
                    "CONSISTENCY_REGISTRY_NODE_FACT_TYPE_DRIFT",
                    f"node {node_id!r} fact_type must exactly match {entry.heading_fact_type!r}",
                    relpath,
                )

        for fact_type, count in sorted(heading_counts.items()):
            if count > 1:
                context.error(
                    "CONSISTENCY_REGISTRY_FACT_TYPE_DUPLICATE",
                    f"registry repeats Fact Type {fact_type!r}",
                    registry_relpath,
                )


CONSISTENCY_MAP_MODULE = ConsistencyMapModule()

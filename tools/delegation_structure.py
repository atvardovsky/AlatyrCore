"""Shared delegation structure; no artifact I/O or communication dispatch."""

from __future__ import annotations

from fnmatch import fnmatchcase
from typing import Any

from path_spec import logical_path


EDGE_KINDS = {"primary-approved-dispatch", "primary-envelope-dispatch"}


MAX_JSON_BYTES = 4 * 1024 * 1024


class DelegationEvidenceError(ValueError):
    """Raised when delegation evidence violates its portable contract."""


def object_value(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DelegationEvidenceError(f"{label} must be an object")
    return value


def exact_fields(value: dict[str, Any], fields: set[str], label: str) -> None:
    missing = sorted(fields - set(value))
    extra = sorted(set(value) - fields)
    if missing or extra:
        raise DelegationEvidenceError(
            f"{label} fields differ: missing={missing}, unexpected={extra}"
        )


def string_value(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DelegationEvidenceError(f"{label} must be a non-empty string")
    return value


def matches_surface(surface: str, selectors: list[str]) -> bool:
    """Match one normalized target-relative surface against envelope selectors."""
    try:
        logical_path(surface)
    except ValueError:
        return False
    return any(fnmatchcase(surface, selector) for selector in selectors)


def validate_topology(
    tree: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    budget: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    root = nodes.get(tree["root_node_id"])
    if root is None or root.get("depth") != 0:
        raise DelegationEvidenceError("execution tree root is invalid")
    children: dict[str, list[dict[str, Any]]] = {}
    for node in nodes.values():
        if node["depth"] == 0:
            continue
        parent = nodes.get(node.get("parent_node_id"))
        if parent is None or node["depth"] != parent["depth"] + 1:
            raise DelegationEvidenceError(
                f"execution node {node['node_id']} has invalid parent"
            )
        if node.get("parent_packet_id") != parent.get("packet_id"):
            raise DelegationEvidenceError(
                f"execution node {node['node_id']} packet parent is invalid"
            )
        children.setdefault(parent["node_id"], []).append(node)
    for parent_id, child_nodes in children.items():
        if len(child_nodes) > budget["max_children_per_parent"]:
            raise DelegationEvidenceError(
                f"execution node {parent_id} exceeds child budget"
            )

    branch_fields = {
        "branch_envelope", "branch_envelope_sha256",
        "branch_checkpoint", "branch_checkpoint_sha256",
    }
    for node in nodes.values():
        recursive_coordinator = node["depth"] == 1 and bool(
            children.get(node["node_id"])
        )
        populated = {field for field in branch_fields if node.get(field) is not None}
        if recursive_coordinator and populated != branch_fields:
            raise DelegationEvidenceError(
                f"recursive coordinator {node['node_id']} has incomplete branch evidence"
            )
        if not recursive_coordinator and populated:
            raise DelegationEvidenceError(
                f"execution node {node['node_id']} carries inapplicable branch evidence"
            )

    edge_rows = tree.get("edges")
    if not isinstance(edge_rows, list) or len(edge_rows) != len(nodes) - 1:
        raise DelegationEvidenceError("execution tree must contain one edge per worker")
    edge_pairs: set[tuple[str, str]] = set()
    for edge in edge_rows:
        edge = object_value(edge, "execution edge")
        exact_fields(edge, {"parent_node_id", "child_node_id", "edge_kind"}, "execution edge")
        pair = (string_value(edge.get("parent_node_id"), "execution edge.parent_node_id"),
                string_value(edge.get("child_node_id"), "execution edge.child_node_id"))
        if pair in edge_pairs or pair[1] not in nodes or pair[0] not in nodes:
            raise DelegationEvidenceError("execution edge is duplicate or unresolved")
        if nodes[pair[1]].get("parent_node_id") != pair[0] or not isinstance(edge.get("edge_kind"), str) or edge.get("edge_kind") not in EDGE_KINDS:
            raise DelegationEvidenceError("execution edge disagrees with topology")
        if nodes[pair[1]]["depth"] == 2 and edge.get("edge_kind") != "primary-envelope-dispatch":
            raise DelegationEvidenceError("depth-2 dispatch requires a branch envelope")
        if nodes[pair[1]]["depth"] == 1 and edge.get("edge_kind") != "primary-approved-dispatch":
            raise DelegationEvidenceError("depth-1 dispatch requires primary approval")
        edge_pairs.add(pair)
    expected_edge_pairs = {
        (node["parent_node_id"], node["node_id"])
        for node in nodes.values()
        if node["depth"] > 0
    }
    if edge_pairs != expected_edge_pairs:
        raise DelegationEvidenceError("execution edges do not cover the node topology")
    return root, children

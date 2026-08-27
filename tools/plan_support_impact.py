#!/usr/bin/env python3
"""Build a bounded changed-path and changed-fact support impact plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from impact_graph import (
    ImpactGraphError,
    build_reverse_index,
    load_impact_graph,
    matching_node_ids,
    traverse_impact,
)
from support_state import SupportStateError, build_support_state, load_state, state_differences
from target_validation_support import git_changed_files


RELATIONSHIP_DISCOVERY_MARKERS = {
    ".py",
    ".php",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".kt",
    ".go",
    ".rs",
    ".cs",
    ".sql",
    ".graphql",
    ".proto",
}


def _changed_paths(target: Path, diff_ref: str | None) -> list[str]:
    if diff_ref is None:
        return []
    paths = git_changed_files(target, diff_ref)
    if paths is None:
        raise ValueError(f"cannot resolve Git diff from {diff_ref}")
    return sorted(paths)


def _support_changes(target: Path) -> list[dict[str, Any]]:
    try:
        baseline = load_state(target)
        current = build_support_state(target)
    except SupportStateError:
        return []
    return [difference.__dict__ for difference in state_differences(baseline, current)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--diff-ref")
    parser.add_argument("--fact-id", action="append", default=[])
    parser.add_argument("--max-depth", type=int)
    parser.add_argument("--max-nodes", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    target = args.target.resolve()
    try:
        graph = load_impact_graph(target)
        reverse = build_reverse_index(graph)
        changed_paths = _changed_paths(target, args.diff_ref)
    except (ImpactGraphError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    support_changes = _support_changes(target)
    all_changed_paths = sorted(
        set(changed_paths)
        | {item["path"] for item in support_changes if isinstance(item.get("path"), str)}
    )
    path_matches = {
        relpath: sorted(matching_node_ids(reverse, relpath))
        for relpath in all_changed_paths
    }
    start_ids = set(args.fact_id)
    for node_ids in path_matches.values():
        start_ids.update(node_ids)
    missing_fact_ids = sorted(start_ids - graph.nodes.keys())
    if missing_fact_ids:
        print(
            "FAIL: unknown fact IDs: " + ", ".join(missing_fact_ids),
            file=sys.stderr,
        )
        return 1

    policy = graph.root.get("impact_policy", {})
    max_depth = args.max_depth or policy.get("max_depth", 4)
    max_nodes = args.max_nodes or policy.get("max_nodes", 100)
    try:
        selected, selected_edges, skipped_edges = traverse_impact(
            graph,
            start_ids,
            max_depth=max_depth,
            max_nodes=max_nodes,
        )
    except ImpactGraphError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    impacted_surfaces: list[dict[str, Any]] = []
    context_ids: set[str] = set()
    for node_id in selected:
        node = graph.nodes[node_id]
        for binding in node.get("bindings", []):
            if not isinstance(binding, dict):
                continue
            impacted_surfaces.append(
                {
                    "node_id": node_id,
                    "binding_id": binding.get("id"),
                    "surface_kind": binding.get("surface_kind"),
                    "path": binding.get("path"),
                    "selector_kind": binding.get("selector_kind"),
                    "selector": binding.get("selector"),
                    "authority": binding.get("authority"),
                }
            )
            context_ids.update(
                value
                for value in binding.get("context_ids", [])
                if isinstance(value, str) and value and "{" not in value
            )
    unmapped = [path for path, node_ids in path_matches.items() if not node_ids]
    discovery_triggers = [
        path
        for path in unmapped
        if Path(path).suffix.casefold() in RELATIONSHIP_DISCOVERY_MARKERS
    ]
    report = {
        "schema_version": 1,
        "report_kind": "target-support-impact-plan",
        "diff_ref": args.diff_ref,
        "graph_digest": graph.graph_digest,
        "changed_paths": all_changed_paths,
        "support_changes": support_changes,
        "path_matches": path_matches,
        "explicit_fact_ids": sorted(set(args.fact_id)),
        "selected_node_ids": selected,
        "selected_edges": selected_edges,
        "skipped_edges": skipped_edges,
        "impacted_surfaces": impacted_surfaces,
        "required_context_ids": sorted(context_ids),
        "unmapped_paths": unmapped,
        "relationship_candidate_triggers": discovery_triggers,
        "relationship_candidate_policy": "record evidence for owner review; never promote automatically",
        "limits": {"max_depth": max_depth, "max_nodes": max_nodes},
        "reasoning_boundary": "deterministic routing identifies candidates; the agent or reviewer re-derives semantics and invariants",
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(rendered.encode("utf-8"))
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

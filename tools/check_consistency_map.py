#!/usr/bin/env python3
"""Validate the sharded target consistency-map template contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from impact_graph import (
    GRAPH_LEVELS,
    ImpactGraphError,
    build_reverse_index,
    load_impact_graph,
    validate_graph,
)


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
MAP = TARGET / ".ai/project/consistency-map.json"
REGISTRY = TARGET / ".ai/project/source-of-truth-registry.md"
MANIFEST = TARGET / ".ai/alatyr.yaml"
ROUTER = TARGET / ".ai/assistant/context-router.json"


def main() -> int:
    failures: list[str] = []
    try:
        graph = load_impact_graph(TARGET)
    except ImpactGraphError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    data = graph.root
    if data.get("schema_version") != 3:
        failures.append("consistency-map template must use schema version 3")
    if data.get("levels") != GRAPH_LEVELS:
        failures.append("consistency-map levels must include concrete surfaces")
    if data.get("registry_sync_policy", {}).get("coverage") != "every-live-registry-fact-type":
        failures.append("consistency-map must retain exact registry coverage")
    for failure in validate_graph(graph, allow_placeholders=True):
        failures.append(failure)

    reverse_relpath = data.get("reverse_index")
    if not isinstance(reverse_relpath, str):
        failures.append("consistency-map reverse_index is missing")
    else:
        reverse = json.loads((TARGET / reverse_relpath).read_text(encoding="utf-8"))
        expected = build_reverse_index(graph)
        if reverse.get("schema_version") != 1 or reverse.get("index_kind") != expected["index_kind"]:
            failures.append("consistency reverse-index contract is invalid")
        if reverse.get("exact_paths") != expected["exact_paths"] or reverse.get("patterns") != expected["patterns"]:
            failures.append("consistency reverse-index routing differs from graph bindings")

    candidates_relpath = data.get("relationship_candidates")
    try:
        candidates = json.loads((TARGET / candidates_relpath).read_text(encoding="utf-8"))
    except (OSError, TypeError, json.JSONDecodeError) as exc:
        failures.append(f"relationship-candidate record is invalid: {exc}")
    else:
        if (
            candidates.get("schema_version") != 1
            or candidates.get("record_kind") != "target-consistency-relationship-candidates"
            or candidates.get("records") != []
        ):
            failures.append("template relationship candidates must start empty and non-authoritative")

    registry_text = REGISTRY.read_text(encoding="utf-8")
    for required in [
        "Consistency map node:",
        "Relationship coverage:",
        "every live Fact Type entry",
        "relationship candidate",
    ]:
        if required not in registry_text:
            failures.append(f"source-of-truth registry missing {required}")

    manifest_text = MANIFEST.read_text(encoding="utf-8")
    if 'consistency_map: ".ai/project/consistency-map.json"' not in manifest_text:
        failures.append("target manifest missing source_of_truth.consistency_map")

    try:
        router = json.loads(ROUTER.read_text(encoding="utf-8"))
        descriptor = router["consistency_routing"]["descriptor"]
        routing = json.loads((TARGET / descriptor).read_text(encoding="utf-8"))
        required_context = routing["required_context"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        failures.append(f"invalid consistency routing: {exc}")
    else:
        for required in [
            ".ai/project/source-of-truth-registry.md",
            ".ai/project/consistency-map.json",
            ".ai/assistant/consistency-reverse-index.json",
        ]:
            if required not in required_context:
                failures.append(f"consistency routing missing {required}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "OK: checked sharded consistency-map template with "
        f"{len(graph.nodes)} placeholder node(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

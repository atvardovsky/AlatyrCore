"""Shared candidate semantics for validators and bounded warning consumers."""

from __future__ import annotations

from typing import Any

RELATIONSHIP_TYPES = frozenset({"implements", "verifies", "documents", "visualizes", "generates", "constrains", "depends-on", "routes"})


def candidate_semantic_failures(records: list[dict[str, Any]], nodes: dict) -> list[tuple[str, str]]:
    failures, seen = [], set()
    for record in records:
        identifier = record.get("id")
        if isinstance(identifier, str):
            if identifier in seen:
                failures.append(("CONSISTENCY_RELATIONSHIP_CANDIDATE_DUPLICATE", f"relationship candidate id is repeated: {identifier}"))
            seen.add(identifier)
        kind = record.get("relationship_type")
        if not isinstance(kind, str) or kind not in RELATIONSHIP_TYPES:
            failures.append(("CONSISTENCY_RELATIONSHIP_CANDIDATE_TYPE", f"relationship candidate {identifier!r} has unsupported type {kind!r}"))
        for endpoint in ("source_node", "target_node"):
            value = record.get(endpoint)
            if not isinstance(value, str) or value not in nodes:
                failures.append(("CONSISTENCY_RELATIONSHIP_CANDIDATE_NODE", f"relationship candidate {identifier!r} references missing {endpoint} {value!r}"))
    return failures

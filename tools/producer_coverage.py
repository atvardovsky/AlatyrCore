"""Bounded producer-inventory checks for adopted repair qualification."""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable

from target_validation_support import is_target_relative_path


def policy_producer_failures(entries: list[dict], commands: dict, acceptance_ids: set[str]) -> list[str]:
    failures = []
    if len({entry["id"] for entry in entries}) != len(entries):
        failures.append("producer coverage IDs must be unique")
    for entry in entries:
        name = entry["id"]
        if not is_target_relative_path(entry["inventory_source"]["path"]) or "\\" in entry["inventory_source"]["path"]:
            failures.append(f"producer coverage {name} requires an exact contained inventory owner")
        if not set(entry["command_ids"]) <= commands.keys():
            failures.append(f"producer coverage {name} references an unknown command")
        for identity in entry["command_ids"]:
            execution = commands.get(identity, {}).get("execution", {})
            if execution.get("kind") != "automated-test" or execution.get("proof_boundary") in {"manual", "static-metadata"}:
                failures.append(f"producer coverage {name} requires a behavioral automated command")
        if entry["stage"] == "acceptance" and not set(entry["command_ids"]) <= acceptance_ids:
            failures.append(f"producer coverage {name} acceptance must select original-flow commands")
        ids = set(entry["event_ids"])
        if len(entry["event_ids"]) > entry["max_capacity"]:
            failures.append(f"producer coverage {name} capacity cannot retain the declared producer inventory")
        edges = [(row["before"], row["after"]) for row in entry["precedence"]]
        if len(edges) != len(set(edges)) or any(a not in ids or b not in ids or a == b for a, b in edges):
            failures.append(f"producer coverage {name} has duplicate, unknown or self-referential precedence")
        successors = {node: [] for node in ids}
        incoming = dict.fromkeys(ids, 0)
        for before, after in set(edges):
            if before in ids and after in ids:
                successors[before].append(after)
                incoming[after] += 1
        ready = [node for node, count in incoming.items() if count == 0]
        covered = 0
        while ready:
            covered += 1
            for node in successors[ready.pop()]:
                incoming[node] -= 1
                if incoming[node] == 0:
                    ready.append(node)
        if covered != len(ids):
            failures.append(f"producer coverage {name} precedence contains a cycle")
    return failures


def observed_coverage_failures(entry: dict, run: dict, artifact: Any,
                               pointer: Callable[[Any, str], Any]) -> list[str]:
    """Policy is schema-validated; observed JSON is untrusted and type-checked."""
    label = f"producer coverage {entry['id']}"
    failures = []
    owner = entry["inventory_source"]
    inputs = run.get("input_sha256")
    if not isinstance(inputs, dict) or inputs.get(owner["path"]) != owner["sha256"]:
        failures.append(f"{label} run does not bind its canonical producer inventory")
    events = pointer(artifact, entry["events_pointer"])
    capacity = pointer(artifact, entry["capacity_pointer"])
    truncated = pointer(artifact, entry["truncated_pointer"])
    if not isinstance(events, list) or len(events) > 256 or any(not isinstance(event, str) or not event for event in events):
        return failures + [f"{label} requires a bounded observed string event sequence"]
    if type(capacity) is not int or not len(entry["event_ids"]) <= capacity <= entry["max_capacity"]:
        failures.append(f"{label} observed capacity is missing, insufficient or exceeds the policy bound")
    if truncated is not False:
        failures.append(f"{label} cannot qualify complete coverage from missing or truncated observations")
    if Counter(events) != Counter(entry["event_ids"]):
        failures.append(f"{label} event identities or multiplicities differ from the producer inventory")
    positions: dict[str, list[int]] = {}
    for index, event in enumerate(events):
        positions.setdefault(event, []).append(index)
    for edge in entry["precedence"]:
        before, after = positions.get(edge["before"]), positions.get(edge["after"])
        if not before or not after or before[-1] >= after[0]:
            failures.append(f"{label} required precedence {edge['before']} -> {edge['after']} was not observed")
    return failures

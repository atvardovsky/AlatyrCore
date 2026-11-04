"""Source-only architectural fitness checks and review signals."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from local_python_import_graph import LocalPythonImportGraph


FOUNDATION = frozenset({"path_spec", "source_state", "parallel_execution", "sparse_overlay",
                        "yaml_support", "local_file_lock", "local_python_import_graph", "source_test_timing"})


def strongly_connected_components(edges: dict[str, set[str]]) -> list[list[str]]:
    index, low, stack, active, result = {}, {}, [], set(), []
    def visit(node):
        index[node] = low[node] = len(index)
        stack.append(node)
        active.add(node)
        for child in sorted(edges.get(node, set())):
            if child not in edges:
                continue
            if child not in index:
                visit(child)
                low[node] = min(low[node], low[child])
            elif child in active:
                low[node] = min(low[node], index[child])
        if low[node] == index[node]:
            component = []
            while True:
                child = stack.pop()
                active.remove(child)
                component.append(child)
                if child == node:
                    break
            if len(component) > 1 or node in edges.get(node, set()):
                result.append(sorted(component))
    for node in sorted(edges):
        if node not in index:
            visit(node)
    return sorted(result)


def architecture_failures(root: Path, *, graph: LocalPythonImportGraph | None = None,
                          allowed_cycles: list[dict] | None = None) -> list[str]:
    graph = graph or LocalPythonImportGraph(root)
    names = {path: name for name, path in graph.modules.items()}
    edges = {name: {names[p] for p in graph.scan(path).dependencies}
             for name, path in graph.modules.items()}
    failures = []
    for name, path in graph.modules.items():
        if not graph.scan(path).complete:
            failures.append(f"source dependency graph is incomplete: {name}")
    for name in sorted(FOUNDATION):
        path = graph.modules.get(name)
        if path is None:
            failures.append(f"source foundation module is missing: {name}")
            continue
        for dependency in sorted(edges[name] - FOUNDATION):
            failures.append(f"foundation back-import: {name} -> {dependency}")
    failures.extend(cycle_failures(edges, allowed_cycles or []))
    return failures


def cycle_failures(edges: dict[str, set[str]], allowed: list[dict]) -> list[str]:
    approved = []
    if not isinstance(allowed, list):
        return ["source dependency cycle exceptions must be a list"]
    for record in allowed:
        if (not isinstance(record, dict) or set(record) != {"members", "edges", "reason"}
                or not isinstance(record["members"], list) or not record["members"]
                or any(not isinstance(p, str) or not p for p in record["members"])
                or len(record["members"]) != len(set(record["members"]))
                or not isinstance(record["edges"], list)
                or any(not isinstance(e, list) or len(e) != 2 or any(p not in record["members"] for p in e)
                       for e in record["edges"])
                or not isinstance(record["reason"], str) or not record["reason"].strip()):
            return ["source dependency cycle exception is malformed"]
        members, bindings = set(record["members"]), {tuple(e) for e in record["edges"]}
        if any(members & existing for existing, _ in approved) or len(bindings) != len(record["edges"]):
            return ["source dependency cycle exceptions overlap or repeat edges"]
        approved.append((members, bindings))
    failures = []
    for component in strongly_connected_components(edges):
        members = set(component)
        internal = {(a, b) for a in members for b in edges[a] if b in members}
        if not any(members <= known and internal <= known_edges for known, known_edges in approved):
            failures.append("source dependency cycle requires review: " + " -> ".join(component))
    return failures


def entrypoint_failures(implementations: dict, legacy_any: list[str]) -> list[str]:
    """Signature/annotation validation only, not static type correctness."""
    from typing import Any
    from target_adapter_validation.capability import CapabilityValidationContext
    from target_adapter_validation.domain import DomainValidationHost
    failures = []
    for name, implementation in implementations.items():
        function = getattr(implementation, "validator", None) or getattr(implementation, "validate", None)
        try:
            signature = inspect.signature(function)
        except (TypeError, ValueError):
            failures.append(f"capability entrypoint has no inspectable callable: {name}")
            continue
        parameters = list(signature.parameters.values())
        if (inspect.iscoroutinefunction(function) or len(parameters) != 2
                or any(p.kind not in {p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD} for p in parameters)
                or any(p.annotation is p.empty for p in parameters)
                or not (signature.return_annotation is None or signature.return_annotation == "None")):
            failures.append(f"capability entrypoint has an invalid signature: {name}")
        elif not (parameters[0].annotation is CapabilityValidationContext
                or parameters[0].annotation is DomainValidationHost
                or isinstance(parameters[0].annotation, str) and parameters[0].annotation.strip("\"'") in {"CapabilityValidationContext", "DomainValidationHost"}
                or name in legacy_any and (parameters[0].annotation is Any
                    or isinstance(parameters[0].annotation, str) and parameters[0].annotation.strip("\"'") == "Any")):
            failures.append(f"capability entrypoint requires the narrow host contract: {name}")
    return failures


def branch_points(node: ast.AST) -> int:
    return sum(isinstance(child, (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While,
                                ast.ExceptHandler, ast.comprehension))
               or isinstance(child, ast.BoolOp) and len(child.values) - 1
               for child in ast.walk(node))

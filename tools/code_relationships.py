"""Compare selected Python syntax relationships with an existing consistency map."""

from __future__ import annotations

import ast
import json
from importlib.util import resolve_name
from pathlib import Path, PurePosixPath
from typing import Any

from impact_graph import load_impact_graph, traverse_impact, validate_graph
from path_spec import PathDialect, PathSpec, logical_path
from project_evidence import ProjectEvidence

MAX_SOURCES = 128
MAX_NODES = 512
MAX_ROWS = 4096
MAX_AST_NODES = 100000
MAX_REPORT_BYTES = 1024 * 1024


def _module(path: str, source_root: str) -> str:
    relative = PurePosixPath(path).relative_to(PurePosixPath(source_root))
    if relative.suffix != ".py":
        raise ValueError(f"Python backend requires .py source: {path}")
    parts = relative.with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts or any(not part.isidentifier() for part in parts):
        raise ValueError(f"source has no importable Python module identity: {path}")
    return ".".join(parts)


def _syntax(raw: bytes, path: str, module: str) -> tuple[dict[str, int], list[tuple[int, list[str]]]]:
    tree = ast.parse(raw, filename=path)
    symbols, imports, pending, count = {}, [], [(tree, "")], 0
    package = module if PurePosixPath(path).name == "__init__.py" else module.rpartition(".")[0]
    while pending:
        node, scope = pending.pop()
        count += 1
        if count > MAX_AST_NODES:
            raise ValueError(f"{path} exceeds {MAX_AST_NODES} AST nodes")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            scope = f"{scope}.{node.name}" if scope else node.name
            symbols[scope] = symbols.get(scope, 0) + 1
        if isinstance(node, ast.Import):
            imports.extend((node.lineno, [alias.name]) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                try:
                    base = resolve_name("." * node.level + base, package)
                except (ImportError, ValueError):
                    base = ""
            # Preserve a base module as well as a possible imported submodule.
            for alias in node.names:
                names = [f"{base}.{alias.name}", base] if base and alias.name != "*" else [base]
                imports.append((node.lineno, names))
        pending.extend((child, scope) for child in ast.iter_child_nodes(node))
    return symbols, imports


def inspect_relationships(target: Path, sources: list[str], *, source_root: str = ".",
                          map_path: str = ".ai/project/consistency-map.json") -> dict[str, Any]:
    if (not sources or len(sources) > MAX_SOURCES
            or any(not isinstance(path, str) for path in sources)
            or len(sources) != len({path.casefold() for path in sources})):
        raise ValueError(f"select 1..{MAX_SOURCES} unique exact source paths")
    if source_root != ".":
        logical_path(source_root)
    for path in sources:
        logical_path(path)
    logical_path(map_path)
    with ProjectEvidence(target) as evidence:
        graph = load_impact_graph(evidence.root, map_path)
        failures = validate_graph(graph)
        if failures:
            raise ValueError("invalid consistency map: " + "; ".join(failures))
        if len(graph.nodes) > MAX_NODES:
            raise ValueError(f"code relationship review exceeds {MAX_NODES} map nodes")
        _, edges, _ = traverse_impact(graph, graph.nodes, max_depth=0, max_nodes=MAX_NODES)
        accepted = {(edge["source"], edge["target"]) for edge in edges
                    if edge["type"] == "depends-on" and "traversal" not in edge}
        modules = {_module(path, source_root): path for path in sources}
        if len(modules) != len(sources):
            raise ValueError("selected sources have ambiguous Python module identities")
        definitions, imports = {}, {}
        for module, path in modules.items():
            definitions[path], imports[path] = _syntax(evidence.exact(path), path, module)
        findings, owners = [], {path: set() for path in sources}
        for node_id, node in sorted(graph.nodes.items()):
            for binding in node.get("bindings", []):
                if binding.get("surface_kind") != "code":
                    continue
                kind, path = binding.get("selector_kind"), binding["path"]
                matches = [source for source in sources if
                           (PathSpec(path, PathDialect.PORTABLE_FNMATCH_V1).matches(source)
                            if kind == "glob" else source == path)]
                for source in matches:
                    if kind == "symbol":
                        selector = binding.get("selector")
                        if not isinstance(selector, str) or selector not in definitions[source]:
                            findings.append({"code": "CODE_SYMBOL_MISSING", "path": source,
                                             "node_id": node_id, "selector": selector if isinstance(selector, str) else None})
                        elif definitions[source][selector] > 1:
                            findings.append({"code": "CODE_SYMBOL_AMBIGUOUS", "path": source,
                                             "node_id": node_id, "selector": selector})
                    elif kind not in {"file", "glob"}:
                        findings.append({"code": "CODE_SELECTOR_UNSUPPORTED", "path": source,
                                         "node_id": node_id})
                    owners[source].add(node_id)
                    if len(findings) > MAX_ROWS:
                        raise ValueError(f"code relationship result exceeds {MAX_ROWS} rows; decompose")
        for path, ids in owners.items():
            if len(ids) != 1:
                findings.append({"code": "CODE_OWNERSHIP_UNMAPPED" if not ids else "CODE_OWNERSHIP_AMBIGUOUS",
                                 "path": path, "node_ids": sorted(ids)})
        if len(findings) > MAX_ROWS:
            raise ValueError(f"code relationship result exceeds {MAX_ROWS} rows; decompose")
        observations, unresolved = [], []
        for path in sorted(imports):
            for line, names in imports[path]:
                resolved = {modules[name] for name in names if name in modules}
                if not resolved or (len(names) > 1 and names[0] not in modules):
                    unresolved.append({"path": path, "line": line, "modules": names,
                                       "reason": "symbol-or-submodule-unresolved" if resolved
                                       else "external-or-unselected-or-unresolved"})
                for dependency in sorted(resolved - {path}):
                    row = {"path": path, "dependency": dependency, "line": line,
                           "state": "observed", "evidence": "python-static-import"}
                    observations.append(row)
                    if len(owners[path]) == len(owners[dependency]) == 1:
                        source, destination = next(iter(owners[path])), next(iter(owners[dependency]))
                        if source != destination and (source, destination) not in accepted:
                            findings.append({"code": "CODE_DEPENDENCY_REVIEW", **row,
                                             "source_node": source, "target_node": destination,
                                             "relationship_type": "depends-on", "decision": "candidate-only",
                                             "owner_reference": graph.nodes[source].get("canonical_owner"),
                                             "promotion": "requires existing candidate provenance and target-owner review"})
                if len(observations) + len(unresolved) + len(findings) > MAX_ROWS:
                    raise ValueError(f"code relationship result exceeds {MAX_ROWS} rows; decompose")
        result = {"schema_version": 1, "report_kind": "code-relationship-review",
                  "status": "review-required" if findings else "selected-bindings-consistent",
                  "backend": "python-ast", "source_root": source_root,
                  "selected_sources": sorted(sources), "graph_digest": graph.graph_digest,
                  "observed_relationships": observations, "findings": findings,
                  "unresolved_imports": unresolved, "input_bindings": evidence.bindings(),
                  "architecture_review": "not-assessed",
                  "coverage": "selected-files-static-imports-and-function-class-definitions-only",
                  "limitations": ["Not runtime call coverage or complete repository dependency analysis.",
                                  "Dynamic imports, runtime dispatch and re-export semantics are not resolved.",
                                  "Review hints are not publishable candidate records; missing imports are not disproven dependencies.",
                                  "No architecture approval, authorization or target acceptance is granted."]}
        render_relationship_report(result)
    return result


def render_relationship_report(result: dict[str, Any]) -> str:
    """Bound the exact wire representation, including its trailing newline."""
    rendered = json.dumps(result) + "\n"
    if len(rendered.encode("utf-8")) > MAX_REPORT_BYTES:
        raise ValueError(f"code relationship report exceeds {MAX_REPORT_BYTES} bytes; decompose")
    return rendered

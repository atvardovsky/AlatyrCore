"""Typed dependency graph for deterministic Alatyr projections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ProjectionInput:
    kind: str
    value: str


@dataclass(frozen=True)
class ProjectionOutput:
    path: str
    ownership: str
    write_strategy: str
    merge_strategy: str
    preserve_on_disable: bool


@dataclass(frozen=True)
class ProjectionNode:
    node_id: str
    owner: str
    phase: str
    dependencies: tuple[str, ...]
    inputs: tuple[ProjectionInput, ...]
    outputs: tuple[ProjectionOutput, ...]
    generator_id: str
    checker_ids: tuple[str, ...]
    deterministic: bool = True


FORBIDDEN_SELF_INDEX_OUTPUTS = {
    ".ai/assistant/bootstrap-index.json",
    ".ai/framework/file-inventory.json",
}


def validate_projection_graph(nodes: Iterable[ProjectionNode]) -> tuple[str, ...]:
    by_id: dict[str, ProjectionNode] = {}
    output_owners: dict[str, str] = {}
    for node in nodes:
        if not node.node_id or node.node_id in by_id:
            raise ValueError(f"duplicate or empty projection node: {node.node_id}")
        if not node.owner or not node.generator_id or not node.checker_ids:
            raise ValueError(f"projection node {node.node_id} lacks owner, generator, or checker")
        by_id[node.node_id] = node
        for output in node.outputs:
            previous = output_owners.get(output.path)
            if previous is not None:
                raise ValueError(
                    f"projection output {output.path} has multiple owners: {previous}, {node.node_id}"
                )
            output_owners[output.path] = node.node_id

    temporary: set[str] = set()
    permanent: set[str] = set()
    ordered: list[str] = []

    def visit(node_id: str) -> None:
        if node_id in permanent:
            return
        if node_id in temporary:
            raise ValueError(f"projection dependency cycle includes {node_id}")
        node = by_id.get(node_id)
        if node is None:
            raise ValueError(f"unknown projection dependency: {node_id}")
        temporary.add(node_id)
        output_paths = {output.path for output in node.outputs}
        input_paths = {
            item.value for item in node.inputs if item.kind == "projection-output"
        }
        if output_paths & input_paths:
            raise ValueError(f"projection node {node_id} consumes its own output")
        if output_paths & FORBIDDEN_SELF_INDEX_OUTPUTS and output_paths & input_paths:
            raise ValueError(f"projection node {node_id} creates a forbidden self index")
        for dependency in node.dependencies:
            visit(dependency)
        temporary.remove(node_id)
        permanent.add(node_id)
        ordered.append(node_id)

    for node_id in sorted(by_id):
        visit(node_id)
    return tuple(ordered)


def operation_projection_nodes() -> tuple[ProjectionNode, ...]:
    shared = {
        "ownership": "framework-derived-target-projection",
        "write_strategy": "replace-generated",
        "merge_strategy": "deterministic-projection",
        "preserve_on_disable": False,
    }
    return (
        ProjectionNode(
            node_id="project.operation-catalog",
            owner="templates/target/.ai/assistant/operation-catalog.json",
            phase="target-projection",
            dependencies=(),
            inputs=(
                ProjectionInput("canonical-file", "templates/target/.ai/assistant/operation-catalog.json"),
                ProjectionInput("composition-field", "selected_target_paths"),
            ),
            outputs=(ProjectionOutput(".ai/assistant/operation-catalog.json", **shared),),
            generator_id="scaffold.project_catalog",
            checker_ids=("operation-catalog",),
        ),
        ProjectionNode(
            node_id="project.operation-index",
            owner="templates/target/.ai/assistant/operation-index.json",
            phase="target-projection",
            dependencies=("project.operation-catalog",),
            inputs=(
                ProjectionInput("projection-output", ".ai/assistant/operation-catalog.json"),
            ),
            outputs=(ProjectionOutput(".ai/assistant/operation-index.json", **shared),),
            generator_id="scaffold.build_operation_index",
            checker_ids=("operation-index",),
        ),
    )

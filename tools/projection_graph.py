"""Typed dependency graph for deterministic Alatyr projections."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from capability_catalog import load_surfaces, shared_surface_contract


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

MARKDOWN_PROJECTION_PATHS = {
    ".ai/README.md",
    "AI_ASSISTANTS.md",
    ".ai/assistant/templates/post-install-message.md",
    ".ai/assistant/templates/post-update-message.md",
}
EXACT_GENERATORS = {
    "AGENTS.md": "project-agent-rules",
    ".ai/alatyr.yaml": "project-manifest",
    ".ai/assistant/module-profile.md": "project-module-profile",
    ".ai/assistant/operation-catalog.json": "project-operation-catalog",
    ".ai/assistant/operation-index.json": "project-operation-index",
    ".ai/assistant/gates/index.json": "project-gate-index",
    ".ai/assistant/assistant-capabilities.json": "project-assistant-capabilities",
    ".ai/assistant/context-router.json": "project-context-router",
    ".ai/assistant/entry-packet.json": "project-entry-packet",
    ".ai/assistant/bootstrap-index.json": "project-bootstrap-index",
    ".ai/assistant/ai-infrastructure-router.json": "project-ai-infrastructure-router",
    ".ai/support-state.json": "project-support-state",
}
CONTEXT_DESCRIPTOR_PATHS = {
    ".ai/assistant/context/migration-routing.json",
    ".ai/assistant/context/cost-scenarios.json",
    ".ai/assistant/context/consistency-routing.json",
    ".ai/assistant/context/intents/diagram-request.json",
    ".ai/assistant/context/intents/architecture-request.json",
    ".ai/assistant/context/intents/code-documentation.json",
    ".ai/assistant/context/intents/vocabulary-request.json",
    ".ai/assistant/context/intents/test-first-request.json",
    ".ai/assistant/context/intents/extension-request.json",
    ".ai/assistant/context/task-scales/small-task.json",
    ".ai/assistant/context/task-scales/large-or-resumable.json",
    ".ai/assistant/context/task-scales/change-package.json",
}
GENERATOR_OWNERS = {
    "project-agent-rules": "tools/scaffold_projection.py",
    "project-manifest": "tools/scaffold_projection.py",
    "project-module-profile": "tools/scaffold_projection.py",
    "project-markdown-fragments": "tools/scaffold_projection.py",
    "project-context-descriptor": "tools/scaffold_projection.py",
    "project-context-catalog": "tools/render_context_catalogs.py",
    "project-operation-catalog": "tools/scaffold_projection.py",
    "project-operation-index": "tools/scaffold_projection.py",
    "project-gate-index": "tools/scaffold_projection.py",
    "project-assistant-capabilities": "tools/scaffold_projection.py",
    "project-context-router": "tools/scaffold_projection.py",
    "project-entry-packet": "tools/agent_entry_packet.py",
    "project-bootstrap-index": "tools/bootstrap_index.py",
    "project-ai-infrastructure-router": "tools/scaffold_projection.py",
    "project-support-state": "tools/support_state.py",
    "copy-framework": "tools/framework_packaging.py",
    "copy-template": "tools/scaffold_target_structure.py",
}
GENERATOR_CHECKERS = {
    "project-context-catalog": ("context-catalogs",),
    "project-operation-catalog": ("operation-catalog",),
    "project-operation-index": ("operation-index",),
    "project-gate-index": ("scaffold-profiles",),
    "project-assistant-capabilities": ("assistant-capability-index",),
    "project-context-router": ("context-router",),
    "project-entry-packet": ("agent-entry-packet",),
    "project-bootstrap-index": ("bootstrap-routing",),
    "project-support-state": ("support-information",),
}


def projection_generator_id(path: str) -> str:
    """Classify one target output without reading mutable target state."""

    if path in MARKDOWN_PROJECTION_PATHS:
        return "project-markdown-fragments"
    if path.startswith(".ai/assistant/context/profiles/") or path in CONTEXT_DESCRIPTOR_PATHS:
        return "project-context-descriptor"
    if path.endswith("/context-index.json") and path.startswith(
        (".ai/project/", ".ai/assistant/")
    ):
        return "project-context-catalog"
    if path.startswith(".ai/framework/"):
        return "copy-framework"
    return EXACT_GENERATORS.get(path, "copy-template")


def target_projection_nodes(paths: Iterable[str]) -> tuple[ProjectionNode, ...]:
    """Describe one uniquely owned projection node for every selected output."""

    selected = tuple(sorted(set(paths)))
    shared_surfaces = load_surfaces()
    node_ids = {path: f"target:{path}" for path in selected}
    dependency_paths = {
        ".ai/assistant/operation-index.json": (
            ".ai/assistant/operation-catalog.json",
        ),
        ".ai/assistant/context-router.json": (
            ".ai/assistant/operation-catalog.json",
        ),
        ".ai/assistant/entry-packet.json": (
            ".ai/alatyr.yaml",
            ".ai/assistant/context-router.json",
            ".ai/assistant/gates/index.json",
            ".ai/assistant/operation-catalog.json",
            ".ai/assistant/operation-index.json",
        ),
        ".ai/assistant/bootstrap-index.json": (
            ".ai/README.md",
            ".ai/alatyr.yaml",
            ".ai/assistant/context-router.json",
        ),
    }
    nodes: list[ProjectionNode] = []
    for path in selected:
        generator_id = projection_generator_id(path)
        dependencies = tuple(
            node_ids[dependency]
            for dependency in dependency_paths.get(path, ())
            if dependency in node_ids
        )
        if path == ".ai/support-state.json":
            dependencies = tuple(
                node_ids[candidate]
                for candidate in selected
                if candidate != path
            )
        projection_inputs = tuple(
            ProjectionInput("projection-output", dependency)
            for dependency in dependency_paths.get(path, ())
            if dependency in node_ids
        )
        source_kind = (
            "framework-file" if path.startswith(".ai/framework/") else "template-file"
        )
        template_source = (
            "framework/" + path[len(".ai/framework/") :]
            if source_kind == "framework-file"
            else "templates/target/" + path
        )
        owner = GENERATOR_OWNERS.get(generator_id, template_source)
        shared = shared_surface_contract(Path(path), shared_surfaces)
        merge_strategy = (
            str(shared["merge_strategy"])
            if shared is not None
            else "preserve-existing-unless-overwrite-approved"
        )
        preserve_on_disable = (
            bool(shared.get("preserve_on_disable")) if shared is not None else True
        )
        nodes.append(
            ProjectionNode(
                node_id=node_ids[path],
                owner=owner,
                phase="target-projection",
                dependencies=dependencies,
                inputs=(
                    ProjectionInput(source_kind, template_source),
                    ProjectionInput("composition-field", "selected_target_paths"),
                    *projection_inputs,
                ),
                outputs=(
                    ProjectionOutput(
                        path=path,
                        ownership="framework-derived-target-projection",
                        write_strategy=(
                            "replace-generated"
                            if generator_id not in {"copy-template", "copy-framework"}
                            else "copy-selected"
                        ),
                        merge_strategy=merge_strategy,
                        preserve_on_disable=preserve_on_disable,
                    ),
                ),
                generator_id=generator_id,
                checker_ids=GENERATOR_CHECKERS.get(
                    generator_id, ("scaffold-profiles",)
                ),
            )
        )
    return tuple(nodes)


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

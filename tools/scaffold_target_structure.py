#!/usr/bin/env python3
"""Scaffold Alatyr target adapter structure from source templates.

This is a source-repository helper, not the Alatyr installation mechanism.
It copies placeholder files only. It does not inspect target facts, accept an
installation, overwrite existing files by default, or make protected decisions.

The implementation uses only Python standard-library APIs so it can run on
Linux, macOS, and Windows with Python 3.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from scaffold_projection import (
    build_operation_index,
    load_object,
    project_agent_rule_ids,
    project_ai_infrastructure_router,
    project_assistant_capability_index,
    project_catalog,
    project_context_descriptor,
    project_gate_index,
    project_manifest,
    project_markdown_fragments,
    project_module_profile,
    project_router,
    portable_relative_path,
    render_json,
    SelectedPathIndex,
    selected_path_index,
)
from scaffold_state import INITIAL_INSTALLATION_STATE
from agent_entry_packet import (
    PACKET_PATH,
    build_agent_entry_packet,
    render as render_agent_entry_packet,
)
from bootstrap_index import build_bootstrap_index, render as render_bootstrap_index
from capability_catalog import (
    PACK_ORDER,
    dependency_closure,
    load_modules,
    minimum_pack,
    shared_surface_merge_requirement,
    target_files as capability_target_files,
)
from framework_packaging import (
    pack_names,
    project_registry,
    projected_framework_contents,
    resolve_framework_files,
)
from context_catalog import load_codebook
from composition_model import CompositionRequest, resolve_composition
from projection_graph import (
    MARKDOWN_PROJECTION_PATHS,
    target_projection_nodes,
    validate_projection_graph,
)
from render_context_catalogs import INDEX_NAME, build_directory_catalog_contents
from support_state import STATE_PATH, SupportStateError, build_support_state, render_state
from sparse_overlay import overlay_decision
from target_tool_compat import generation_provenance_from_manifest_text


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT / "templates" / "target"
FRAMEWORK_ROOT = ROOT / "framework"
PROFILE_MANIFEST = ROOT / "tools" / "scaffold_profiles.json"
ASSISTANT_SURFACES = ROOT / "conformance" / "runs" / "assistant-surfaces.json"
NEUTRAL_ASSISTANT_ENTRY_PATHS = {Path("AGENTS.md"), Path("AI_ASSISTANTS.md")}
PROJECTED_MARKDOWN_TARGET_PATHS = {Path(path) for path in MARKDOWN_PROJECTION_PATHS}


def load_profile_manifest() -> dict[str, Any]:
    data = json.loads(PROFILE_MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("scaffold profile manifest must be a JSON object")
    return data


def profile_names() -> list[str]:
    profiles = load_profile_manifest().get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError("scaffold profile manifest must define profiles")
    return list(profiles)


def load_assistant_surfaces() -> list[dict[str, Any]]:
    data = json.loads(ASSISTANT_SURFACES.read_text(encoding="utf-8"))
    surfaces = data.get("surfaces") if isinstance(data, dict) else None
    if not isinstance(surfaces, list) or not surfaces:
        raise ValueError("assistant surface registry must define surfaces")
    if not all(isinstance(surface, dict) for surface in surfaces):
        raise ValueError("assistant surface registry entries must be objects")
    return surfaces


def resolve_assistant_surfaces(requested: list[str] | None) -> set[str]:
    aliases: dict[str, str] = {}
    canonical_ids: set[str] = set()
    for surface in load_assistant_surfaces():
        surface_id = surface.get("id")
        surface_aliases = surface.get("aliases", [])
        if not isinstance(surface_id, str) or not surface_id:
            raise ValueError("assistant surface registry contains an invalid id")
        if not isinstance(surface_aliases, list) or not all(
            isinstance(alias, str) and alias for alias in surface_aliases
        ):
            raise ValueError(f"assistant surface {surface_id} has invalid aliases")
        canonical_ids.add(surface_id)
        for value in [surface_id, *surface_aliases]:
            previous = aliases.get(value)
            if previous is not None and previous != surface_id:
                raise ValueError(f"duplicate assistant surface name: {value}")
            aliases[value] = surface_id

    selected: set[str] = set()
    for value in requested or []:
        surface_id = aliases.get(value)
        if surface_id is None:
            allowed = ", ".join(sorted(canonical_ids))
            raise ValueError(
                f"unknown assistant surface: {value}; expected one of {allowed}"
            )
        selected.add(surface_id)
    return selected


def project_assistant_bridges(
    paths: set[Path], selected_surfaces: set[str]
) -> set[Path]:
    """Keep native bridge files only for explicitly selected assistant clients."""

    native_paths: set[Path] = set()
    selected_native_paths: set[Path] = set()
    selected_neutral_paths: set[Path] = set()
    for surface in load_assistant_surfaces():
        surface_id = surface.get("id")
        bridge_paths = surface.get("bridge_paths")
        if not isinstance(surface_id, str) or not isinstance(bridge_paths, list) or not all(
            isinstance(path, str) and path for path in bridge_paths
        ):
            raise ValueError("assistant surface registry contains invalid bridge paths")
        support_paths = surface.get("optional_support_paths", [])
        if not isinstance(support_paths, list) or not all(
            isinstance(path, str) and path for path in support_paths
        ):
            raise ValueError("assistant surface registry contains invalid support paths")
        surface_paths = {Path(path) for path in [*bridge_paths, *support_paths]}
        surface_native_paths = surface_paths - NEUTRAL_ASSISTANT_ENTRY_PATHS
        native_paths.update(surface_native_paths)
        if surface_id in selected_surfaces:
            selected_native_paths.update(surface_native_paths)
            selected_neutral_paths.update(surface_paths & NEUTRAL_ASSISTANT_ENTRY_PATHS)

    unavailable = {
        path for path in selected_native_paths if not (TEMPLATE_ROOT / path).is_file()
    }
    if unavailable:
        unavailable_text = ", ".join(path.as_posix() for path in sorted(unavailable))
        raise ValueError(
            "selected assistant bridge templates are unavailable: "
            f"{unavailable_text}"
        )
    projected = (paths - native_paths) | selected_native_paths | selected_neutral_paths
    capability_index = Path(".ai/assistant/assistant-capabilities.json")
    if capability_index in projected:
        records = {"generic", *selected_surfaces}
        projected.update(
            Path(f".ai/assistant/assistant-capabilities/{surface_id}.json")
            for surface_id in records
        )
    return projected


def resolve_profile_paths(
    profile: str, enabled_modules: set[str] | None = None
) -> set[Path]:
    manifest = load_profile_manifest()
    profiles = manifest.get("profiles")
    if not isinstance(profiles, dict) or profile not in profiles:
        raise ValueError(f"unknown scaffold profile: {profile}")

    resolving: set[str] = set()

    def resolve(name: str) -> set[Path]:
        if name in resolving:
            raise ValueError(f"cyclic scaffold profile inheritance: {name}")
        entry = profiles.get(name)
        if not isinstance(entry, dict):
            raise ValueError(f"invalid scaffold profile: {name}")
        resolving.add(name)
        paths: set[Path] = set()
        parent = entry.get("extends")
        if parent is not None:
            if not isinstance(parent, str) or parent not in profiles:
                raise ValueError(f"invalid parent for scaffold profile: {name}")
            paths.update(resolve(parent))
        items = entry.get("template_files", [])
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise ValueError(f"invalid template_files for scaffold profile: {name}")
        paths.update(Path(item) for item in items)
        if entry.get("include_remaining_template_files") is True:
            paths.update(
                path.relative_to(TEMPLATE_ROOT)
                for path in TEMPLATE_ROOT.rglob("*")
                if path.is_file()
            )
        resolving.remove(name)
        return paths

    paths = resolve(profile)
    paths.update(capability_target_files(enabled_modules or set()))
    return paths


def iter_template_files(
    profile: str = "full", enabled_modules: set[str] | None = None
) -> list[Path]:
    return sorted(
        TEMPLATE_ROOT / relpath
        for relpath in resolve_profile_paths(profile, enabled_modules)
    )


def resolved_framework_pack(
    profile: str, requested: str, enabled_modules: set[str] | None = None
) -> str:
    profile_pack = {
        "kernel": "kernel",
        "core": "core",
        "standard": "standard",
        "full": "complete",
    }[profile]
    module_pack = minimum_pack(enabled_modules or set())
    required = max([profile_pack, module_pack], key=PACK_ORDER.__getitem__)
    if requested == "matched":
        return required
    if PACK_ORDER[requested] < PACK_ORDER[required]:
        raise ValueError(
            f"framework pack {requested} is too small for support profile {profile} "
            f"and enabled capabilities {sorted(enabled_modules or set())}"
        )
    return requested


def iter_framework_files(pack: str = "complete") -> list[Path]:
    return sorted(FRAMEWORK_ROOT / name for name in resolve_framework_files(pack))


def copy_file(src: Path, dst: Path, *, write: bool, content: str | None = None) -> bool:
    """Write one projected file only when its desired bytes differ."""

    desired = src.read_bytes() if content is None else content.encode("utf-8")
    if not overlay_decision(dst, desired).changed:
        return False
    if write:
        dst.parent.mkdir(parents=True, exist_ok=True)
        # Byte writes preserve canonical LF content on Windows.
        dst.write_bytes(desired)
    return True


@dataclass(frozen=True)
class ProjectionContext:
    catalog: dict[str, Any] | None
    operation_ids: frozenset[str]
    enabled_modules: frozenset[str]
    context_catalogs: dict[Path, str]
    selected_paths: SelectedPathIndex
    generated_by: dict[str, Any] | None


def build_projection_context(
    selected: set[Path],
    enabled_modules: set[str],
    context_catalogs: dict[Path, str] | None = None,
    generated_by: dict[str, Any] | None = None,
) -> ProjectionContext:
    validate_projection_graph(
        target_projection_nodes(path.as_posix() for path in selected)
    )
    catalog_rel = Path(".ai/assistant/operation-catalog.json")
    catalog = None
    if catalog_rel in selected:
        catalog = project_catalog(load_object(TEMPLATE_ROOT / catalog_rel), selected)
    operation_ids = frozenset(
        operation["id"]
        for operation in (catalog or {}).get("operations", [])
        if isinstance(operation, dict) and isinstance(operation.get("id"), str)
    )
    return ProjectionContext(
        catalog=catalog,
        operation_ids=operation_ids,
        enabled_modules=frozenset(enabled_modules),
        context_catalogs=context_catalogs or {},
        selected_paths=selected_path_index(selected),
        generated_by=generated_by,
    )


def build_target_context_catalogs(
    selected: set[Path],
    content_overrides: dict[Path, str] | None = None,
) -> dict[Path, str]:
    """Project recursive target indexes over the selected scaffold files."""

    projected: dict[Path, str] = {}
    for prefix, contour in [
        (Path(".ai/project"), "project"),
        (Path(".ai/assistant"), "assistant"),
    ]:
        selected_files = {
            path.relative_to(prefix).as_posix()
            for path in selected
            if path != prefix
            and prefix in path.parents
            and path.name != INDEX_NAME
        }
        overrides = {
            path.relative_to(prefix).as_posix(): text
            for path, text in (content_overrides or {}).items()
            if path != prefix and prefix in path.parents and path.name != INDEX_NAME
        }
        contents = build_directory_catalog_contents(
            TEMPLATE_ROOT / prefix,
            contour,
            selected_files=selected_files,
            content_overrides=overrides,
        )
        projected.update({prefix / relpath: text for relpath, text in contents.items()})
    return projected


def projected_template_content(
    rel: Path,
    profile: str,
    framework_pack: str,
    selected: set[Path],
    context: ProjectionContext,
    target: Path,
) -> str | None:
    src = TEMPLATE_ROOT / rel
    selected_paths = context.selected_paths
    if rel in context.context_catalogs:
        return context.context_catalogs[rel]
    if rel == Path("AGENTS.md") and framework_pack != "complete":
        rule_ids = [rule["id"] for rule in project_registry(framework_pack)["rules"]]
        return project_agent_rule_ids(
            src.read_text(encoding="utf-8"),
            rule_ids,
            selected_paths,
        )
    if rel == Path(".ai/alatyr.yaml"):
        return project_manifest(
            src.read_text(encoding="utf-8"),
            profile,
            framework_pack,
            selected_paths,
            set(context.enabled_modules),
        )
    if rel == Path(".ai/assistant/module-profile.md"):
        return project_module_profile(
            src.read_text(encoding="utf-8"), set(context.enabled_modules)
        )
    if rel in PROJECTED_MARKDOWN_TARGET_PATHS:
        return project_markdown_fragments(
            src.read_text(encoding="utf-8"),
            selected_paths,
            set(context.enabled_modules),
        )

    catalog_rel = Path(".ai/assistant/operation-catalog.json")
    index_rel = Path(".ai/assistant/operation-index.json")
    router_rel = Path(".ai/assistant/context-router.json")
    gate_index_rel = Path(".ai/assistant/gates/index.json")
    catalog = context.catalog
    if rel == catalog_rel and catalog is not None:
        return render_json(catalog)
    if rel == index_rel and catalog is not None:
        return render_json(build_operation_index(catalog))
    if rel == gate_index_rel:
        return render_json(project_gate_index(load_object(src), selected_paths))
    if rel == Path(".ai/assistant/assistant-capabilities.json"):
        return render_json(
            project_assistant_capability_index(load_object(src), selected_paths)
        )
    if rel == router_rel:
        return render_json(
            project_router(load_object(src), selected_paths, set(context.operation_ids))
        )
    if rel == PACKET_PATH:
        manifest_text = project_manifest(
            (TEMPLATE_ROOT / ".ai/alatyr.yaml").read_text(encoding="utf-8"),
            profile,
            framework_pack,
            selected_paths,
            set(context.enabled_modules),
        )
        router_text = render_json(
            project_router(
                load_object(TEMPLATE_ROOT / router_rel),
                selected_paths,
                set(context.operation_ids),
            )
        )
        gate_index_text = render_json(
            project_gate_index(load_object(TEMPLATE_ROOT / gate_index_rel), selected_paths)
        )
        projected_router = load_object(TEMPLATE_ROOT / router_rel)
        projected_router = project_router(
            projected_router,
            selected_paths,
            set(context.operation_ids),
        )
        operation_index_text = (
            render_json(build_operation_index(catalog)) if catalog is not None else None
        )
        operation_catalog_text = render_json(catalog) if catalog is not None else None
        return render_agent_entry_packet(
            build_agent_entry_packet(
                manifest_text,
                router_text,
                gate_index_text,
                (TEMPLATE_ROOT / ".ai/assistant/policies/action-authorization.json").read_text(
                    encoding="utf-8"
                ),
                (TEMPLATE_ROOT / ".ai/project/support-policy.json").read_text(
                    encoding="utf-8"
                ),
                (TEMPLATE_ROOT / ".ai/assistant/task-decomposition.json").read_text(
                    encoding="utf-8"
                ),
                operation_index_text=operation_index_text,
                operation_catalog_text=operation_catalog_text,
                generated_by=context.generated_by
                or generation_provenance_from_manifest_text(
                    target,
                    tool_name="scaffold_target_structure.py",
                    manifest_text=manifest_text,
                ),
            )
        )
    if rel == Path(".ai/assistant/bootstrap-index.json"):
        manifest_text = project_manifest(
            (TEMPLATE_ROOT / ".ai/alatyr.yaml").read_text(encoding="utf-8"),
            profile,
            framework_pack,
            selected_paths,
            set(context.enabled_modules),
        )
        router_text = render_json(
            project_router(
                load_object(TEMPLATE_ROOT / router_rel),
                selected_paths,
                set(context.operation_ids),
            )
        )
        project_map_text = project_markdown_fragments(
            (TEMPLATE_ROOT / ".ai/README.md").read_text(encoding="utf-8"),
            selected_paths,
            set(context.enabled_modules),
        )
        semantic_index = FRAMEWORK_ROOT / "semantics" / "index.json"
        projected_semantic_index = projected_framework_contents(framework_pack).get(
            "semantics/index.json"
        )
        semantic_index_text = (
            semantic_index.read_text(encoding="utf-8")
            if projected_semantic_index is None
            else projected_semantic_index
        )
        semantic_terms = load_codebook(semantic_index, root=semantic_index.parent)
        projected_registry_text = projected_framework_contents(framework_pack).get(
            "rule-registry.json"
        )
        rule_registry_text = (
            (FRAMEWORK_ROOT / "rule-registry.json").read_text(encoding="utf-8")
            if projected_registry_text is None
            else projected_registry_text
        )
        return render_bootstrap_index(
            build_bootstrap_index(
                manifest_text,
                project_map_text,
                router_text,
                rule_registry_text=rule_registry_text,
                semantic_index_text=semantic_index_text,
                semantic_terms=semantic_terms,
                generated_by=context.generated_by
                or generation_provenance_from_manifest_text(
                    target,
                    tool_name="scaffold_target_structure.py",
                    manifest_text=manifest_text,
                ),
            )
        )
    if rel == Path(".ai/assistant/ai-infrastructure-router.json"):
        return render_json(project_ai_infrastructure_router(load_object(src), selected_paths))
    if rel.parts[:4] == (".ai", "assistant", "context", "profiles") or rel in {
        Path(".ai/assistant/context/migration-routing.json"),
        Path(".ai/assistant/context/cost-scenarios.json"),
        Path(".ai/assistant/context/consistency-routing.json"),
        Path(".ai/assistant/context/intents/diagram-request.json"),
        Path(".ai/assistant/context/intents/architecture-request.json"),
        Path(".ai/assistant/context/intents/code-documentation.json"),
        Path(".ai/assistant/context/intents/vocabulary-request.json"),
        Path(".ai/assistant/context/intents/test-first-request.json"),
        Path(".ai/assistant/context/intents/extension-request.json"),
        Path(".ai/assistant/context/task-scales/small-task.json"),
        Path(".ai/assistant/context/task-scales/large-or-resumable.json"),
        Path(".ai/assistant/context/task-scales/change-package.json"),
    }:
        return render_json(
            project_context_descriptor(
                load_object(src), selected_paths, set(context.operation_ids)
            )
        )
    return None


def plan(args: argparse.Namespace) -> tuple[list[str], list[str]]:
    target = args.target.resolve()
    profile = getattr(args, "profile", "kernel")
    requested_pack = getattr(args, "framework_pack", "matched")
    requested_modules = set(getattr(args, "enable_module", []) or [])
    requested_assistant_surfaces = tuple(
        getattr(args, "assistant_surface", []) or []
    )
    projection_purpose = getattr(args, "projection_purpose", "target")
    if requested_assistant_surfaces:
        requested_modules.add("multi-assistant-bridges")
    composition = resolve_composition(
        CompositionRequest(
            support_profile=profile,
            framework_pack_request=requested_pack,
            requested_capabilities=tuple(sorted(requested_modules)),
            requested_assistant_surfaces=requested_assistant_surfaces,
            projection_purpose=projection_purpose,
        )
    )
    enabled_modules = set(composition.enabled_capabilities)
    framework_pack = composition.framework_pack
    selected_templates = {Path(path) for path in composition.selected_target_paths}
    # Discover the recursive index paths before projecting the router. Its
    # contour entries must describe the exact support profile being installed.
    context_catalogs = build_target_context_catalogs(selected_templates)
    selected_templates.update(context_catalogs)
    framework_files = composition.framework_paths
    selected = selected_templates | {
        Path(".ai") / "framework" / name for name in framework_files
    }
    projected_manifest_text = project_manifest(
        (TEMPLATE_ROOT / ".ai/alatyr.yaml").read_text(encoding="utf-8"),
        profile,
        framework_pack,
        selected_path_index(selected),
        enabled_modules,
    )
    projection_provenance = generation_provenance_from_manifest_text(
        target,
        tool_name="scaffold_target_structure.py",
        manifest_text=projected_manifest_text,
    )
    initial_context = build_projection_context(
        selected, enabled_modules, generated_by=projection_provenance
    )
    projected_target_contents: dict[Path, str] = {}
    for rel in selected_templates:
        if rel.name == INDEX_NAME:
            continue
        content = projected_template_content(
            rel,
            profile,
            framework_pack,
            selected,
            initial_context,
            target,
        )
        if content is not None:
            projected_target_contents[rel] = content
    context_catalogs = build_target_context_catalogs(
        selected_templates, projected_target_contents
    )
    projection_context = build_projection_context(
        selected,
        enabled_modules,
        context_catalogs,
        generated_by=projection_provenance,
    )
    framework_contents = projected_framework_contents(framework_pack)
    actions: list[str] = []
    blocked: list[str] = []

    if not target.exists():
        blocked.append(f"target does not exist: {target}")
        return actions, blocked
    if not target.is_dir():
        blocked.append(f"target is not a directory: {target}")
        return actions, blocked

    support_state_rel = Path(STATE_PATH)
    for rel in sorted(selected_templates):
        if rel == support_state_rel:
            continue
        src = TEMPLATE_ROOT / rel
        dst = target / rel
        merge_strategy = shared_surface_merge_requirement(rel)
        if dst.exists() and merge_strategy is not None:
            blocked.append(
                "shared surface requires adapter-aware merge "
                f"({merge_strategy}); preserved existing file: {dst}"
            )
            continue
        if dst.exists() and not args.overwrite_existing:
            blocked.append(f"exists, would not overwrite: {dst}")
            continue
        copy_file(
            src,
            dst,
            write=args.write,
            content=projected_template_content(
                rel,
                profile,
                framework_pack,
                selected,
                projection_context,
                target,
            ),
        )
        actions.append(
            f"template: {portable_relative_path(rel).as_posix()} -> {dst}"
        )

    for src in iter_framework_files(framework_pack):
        framework_rel = src.relative_to(FRAMEWORK_ROOT)
        key = framework_rel.as_posix()
        rel = Path(".ai") / "framework" / framework_rel
        dst = target / rel
        if dst.exists() and not args.overwrite_existing:
            blocked.append(f"exists, would not overwrite: {dst}")
            continue
        copy_file(src, dst, write=args.write, content=framework_contents[key])
        actions.append(f"framework: {key} -> {dst}")

    if support_state_rel in selected_templates:
        dst = target / support_state_rel
        if dst.exists() and not args.overwrite_existing:
            blocked.append(f"exists, would not overwrite: {dst}")
        else:
            if args.write:
                try:
                    current = build_support_state(target)
                except SupportStateError as exc:
                    blocked.append(f"support state generation failed: {exc}")
                else:
                    copy_file(
                        TEMPLATE_ROOT / support_state_rel,
                        dst,
                        write=True,
                        content=render_state(current),
                    )
            actions.append(f"generated: {STATE_PATH} -> {dst}")

    return actions, blocked


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scaffold placeholder Alatyr adapter files. Default mode is dry-run."
        ),
        epilog=(
            "Examples:\n"
            "  Linux/macOS: python3 tools/scaffold_target_structure.py "
            "--target /path/to/repo\n"
            "  Windows: py -3 tools\\scaffold_target_structure.py "
            "--target C:\\path\\repo\n"
            "  Windows cmd wrapper: tools\\scaffold_target_structure.cmd "
            "--target C:\\path\\repo"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target",
        required=True,
        type=Path,
        help="Existing target repository directory.",
    )
    parser.add_argument(
        "--enable-module",
        action="append",
        default=[],
        choices=sorted(load_modules()),
        help=(
            "Add one optional capability and its dependency closure. Repeat for "
            "multiple capabilities."
        ),
    )
    parser.add_argument(
        "--framework-pack",
        choices=["matched", *pack_names()],
        default="matched",
        help=(
            "Portable framework pack. matched selects kernel, core, standard, "
            "or complete from the target support profile; a broader pack is "
            "allowed."
        ),
    )
    parser.add_argument(
        "--assistant-surface",
        action="append",
        default=[],
        help=(
            "Add native bridge files for one canonical or aliased assistant "
            "surface. Repeat for multiple clients. Native bridges are omitted "
            "by default and currently require --profile full."
        ),
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write files. Without this flag the helper prints the plan only.",
    )
    parser.add_argument(
        "--profile",
        choices=profile_names(),
        default="kernel",
        help=(
            "Target adapter support profile. kernel installs minimal adapter "
            "surfaces, core adds durable evidence and project knowledge, "
            "standard adds common lifecycle/product operations, and full "
            "preserves the historical all-template behavior."
        ),
    )
    parser.add_argument(
        "--projection-purpose",
        choices=["target", "conformance"],
        default="target",
        help=(
            "Materialize selected target support by default. conformance is "
            "source-maintainer-only and includes the complete template corpus."
        ),
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help=(
            "Overwrite existing non-shared files. Use only after explicit human "
            "approval for the exact target path and protected surfaces. Existing "
            "catalog-managed shared surfaces are always preserved for an "
            "adapter-aware merge."
        ),
    )
    args = parser.parse_args()

    try:
        actions, blocked = plan(args)
        composition = resolve_composition(
            CompositionRequest(
                support_profile=args.profile,
                framework_pack_request=args.framework_pack,
                requested_capabilities=tuple(sorted(set(args.enable_module))),
                requested_assistant_surfaces=tuple(args.assistant_surface),
                projection_purpose=args.projection_purpose,
            )
        )
        enabled_modules = set(composition.enabled_capabilities)
        selected_assistant_surfaces = set(composition.assistant_surfaces)
        framework_pack = composition.framework_pack
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    mode = "WRITE" if args.write else "DRY-RUN"
    print(f"Alatyr scaffold mode: {mode}")
    print(f"Alatyr scaffold profile: {args.profile}")
    print(f"Alatyr framework pack: {framework_pack}")
    print(f"Alatyr adapter installation state: {INITIAL_INSTALLATION_STATE}")
    print(
        "Enabled optional capabilities: "
        + (", ".join(sorted(enabled_modules)) if enabled_modules else "none")
    )
    print(
        "Selected assistant surfaces: "
        + (
            ", ".join(sorted(selected_assistant_surfaces))
            if selected_assistant_surfaces
            else "none; native bridges omitted"
        )
    )
    print("This helper does not complete installation or fill target facts.")
    print("Supported platforms: Linux, macOS, Windows.")

    if actions:
        print("\nActions:")
        for action in actions:
            print(f"- {action}")

    if blocked:
        print("\nBlocked or skipped:")
        for item in blocked:
            print(f"- {item}")

    if args.write and blocked and not args.overwrite_existing:
        print(
            "\nSome files were skipped because they already exist. "
            "Review target facts and approvals before overwriting.",
            file=sys.stderr,
        )

    return 1 if blocked and not actions else 0


if __name__ == "__main__":
    raise SystemExit(main())

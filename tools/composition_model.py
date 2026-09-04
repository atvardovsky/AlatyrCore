"""Normalize Alatyr profile, pack, capability, and assistant selection."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from capability_catalog import PACK_ORDER, dependency_closure, load_modules, minimum_pack
from framework_packaging import project_registry, resolve_framework_files


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT / "templates" / "target"
PROFILE_MANIFEST = ROOT / "tools" / "scaffold_profiles.json"
ASSISTANT_SURFACES = ROOT / "conformance" / "runs" / "assistant-surfaces.json"
PROFILE_PACKS = {
    "kernel": "kernel",
    "core": "core",
    "standard": "standard",
    "full": "complete",
}
NEUTRAL_ASSISTANT_PATHS = {"AGENTS.md", "AI_ASSISTANTS.md"}


@dataclass(frozen=True)
class CompositionRequest:
    support_profile: str
    framework_pack_request: str = "matched"
    requested_capabilities: tuple[str, ...] = ()
    requested_assistant_surfaces: tuple[str, ...] = ()


@dataclass(frozen=True)
class PathOrigin:
    path: str
    origins: tuple[str, ...]


@dataclass(frozen=True)
class ResolvedComposition:
    contract_version: int
    support_profile: str
    support_profile_chain: tuple[str, ...]
    framework_pack_request: str
    framework_pack: str
    framework_pack_chain: tuple[str, ...]
    requested_capabilities: tuple[str, ...]
    enabled_capabilities: tuple[str, ...]
    capability_edges: tuple[tuple[str, str], ...]
    requested_assistant_surfaces: tuple[str, ...]
    assistant_surfaces: tuple[str, ...]
    alias_resolutions: tuple[tuple[str, str], ...]
    profile_template_paths: tuple[str, ...]
    capability_target_paths: tuple[str, ...]
    assistant_bridge_paths: tuple[str, ...]
    selected_target_paths: tuple[str, ...]
    target_path_origins: tuple[PathOrigin, ...]
    framework_paths: tuple[str, ...]
    installed_rule_ids: tuple[str, ...]
    required_check_ids: tuple[str, ...]
    source_digests: tuple[tuple[str, str], ...]


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _inheritance_chain(
    entries: dict[str, Any], selected: str, *, label: str
) -> tuple[str, ...]:
    if selected not in entries:
        raise ValueError(f"unknown {label}: {selected}")
    visiting: set[str] = set()
    chain: list[str] = []

    def visit(name: str) -> None:
        if name in visiting:
            raise ValueError(f"cyclic {label} inheritance: {name}")
        entry = entries.get(name)
        if not isinstance(entry, dict):
            raise ValueError(f"invalid {label}: {name}")
        visiting.add(name)
        parent = entry.get("extends")
        if parent is not None:
            if not isinstance(parent, str) or parent not in entries:
                raise ValueError(f"invalid parent for {label}: {name}")
            visit(parent)
        visiting.remove(name)
        if name not in chain:
            chain.append(name)

    visit(selected)
    return tuple(chain)


def _profile_paths(profile: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    profiles = _object(PROFILE_MANIFEST).get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError("scaffold profile manifest must define profiles")
    chain = _inheritance_chain(profiles, profile, label="scaffold profile")
    paths: set[str] = set()
    for name in chain:
        entry = profiles[name]
        values = entry.get("template_files", [])
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            raise ValueError(f"invalid template_files for scaffold profile: {name}")
        paths.update(values)
        if entry.get("include_remaining_template_files") is True:
            paths.update(
                path.relative_to(TEMPLATE_ROOT).as_posix()
                for path in TEMPLATE_ROOT.rglob("*")
                if path.is_file()
            )
    return chain, tuple(sorted(paths))


def _assistant_selection(
    requested: Iterable[str], selected_paths: set[str]
) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...], tuple[str, ...], set[str]]:
    data = _object(ASSISTANT_SURFACES)
    records = data.get("surfaces")
    if not isinstance(records, list) or not records:
        raise ValueError("assistant surface registry must define surfaces")
    aliases: dict[str, str] = {}
    paths_by_surface: dict[str, set[str]] = {}
    all_native: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            raise ValueError("assistant surface registry contains an invalid entry")
        surface_id = record["id"]
        names = [surface_id, *record.get("aliases", [])]
        surface_paths = set(record.get("bridge_paths", [])) | set(
            record.get("optional_support_paths", [])
        )
        if not all(isinstance(value, str) and value for value in [*names, *surface_paths]):
            raise ValueError(f"assistant surface {surface_id} is invalid")
        paths_by_surface[surface_id] = surface_paths
        all_native.update(surface_paths - NEUTRAL_ASSISTANT_PATHS)
        for name in names:
            previous = aliases.get(name)
            if previous is not None and previous != surface_id:
                raise ValueError(f"duplicate assistant surface name: {name}")
            aliases[name] = surface_id

    resolutions: list[tuple[str, str]] = []
    selected: set[str] = set()
    for name in requested:
        surface_id = aliases.get(name)
        if surface_id is None:
            raise ValueError(f"unknown assistant surface: {name}")
        selected.add(surface_id)
        resolutions.append((name, surface_id))

    bridges: set[str] = set()
    neutral: set[str] = set()
    for surface_id in selected:
        surface_paths = paths_by_surface[surface_id]
        bridges.update(surface_paths - NEUTRAL_ASSISTANT_PATHS)
        neutral.update(surface_paths & NEUTRAL_ASSISTANT_PATHS)
    selected_paths.difference_update(all_native)
    selected_paths.update(bridges)
    selected_paths.update(neutral)
    capability_index = ".ai/assistant/assistant-capabilities.json"
    if capability_index in selected_paths:
        selected_paths.add(".ai/assistant/assistant-capabilities/generic.json")
        selected_paths.update(
            f".ai/assistant/assistant-capabilities/{surface_id}.json"
            for surface_id in selected
        )
    return (
        tuple(sorted(selected)),
        tuple(sorted(resolutions)),
        tuple(sorted(bridges)),
        selected_paths,
    )


def _resolved_pack(profile: str, requested: str, capabilities: tuple[str, ...]) -> str:
    if requested not in {*PACK_ORDER, "matched"}:
        raise ValueError(f"unknown framework pack: {requested}")
    required = max(
        [PROFILE_PACKS[profile], minimum_pack(capabilities)],
        key=PACK_ORDER.__getitem__,
    )
    if requested == "matched":
        return required
    if PACK_ORDER[requested] < PACK_ORDER[required]:
        raise ValueError(
            f"framework pack {requested} is too small for support profile {profile} "
            f"and enabled capabilities {list(capabilities)}"
        )
    return requested


def resolve_composition(request: CompositionRequest) -> ResolvedComposition:
    profile_chain, profile_paths = _profile_paths(request.support_profile)
    modules = load_modules()
    enabled = tuple(sorted(dependency_closure(request.requested_capabilities, modules)))
    capability_paths = tuple(
        sorted(
            {
                path
                for module_id in enabled
                for path in modules[module_id].get("target_files", [])
            }
        )
    )
    selected_paths = set(profile_paths) | set(capability_paths)
    surfaces, aliases, bridges, selected_paths = _assistant_selection(
        request.requested_assistant_surfaces, selected_paths
    )
    pack = _resolved_pack(request.support_profile, request.framework_pack_request, enabled)
    pack_catalog = _object(ROOT / "framework" / "framework-packs.json").get("packs")
    if not isinstance(pack_catalog, dict):
        raise ValueError("framework pack catalog must define packs")
    pack_chain = _inheritance_chain(pack_catalog, pack, label="framework pack")
    framework_paths = tuple(sorted(resolve_framework_files(pack)))
    installed_rule_ids = tuple(
        sorted(
            rule["id"]
            for rule in project_registry(pack).get("rules", [])
            if isinstance(rule, dict) and isinstance(rule.get("id"), str)
        )
    )
    required_checks = tuple(
        sorted(
            {
                check_id
                for module_id in enabled
                for check_id in modules[module_id].get("check_ids", [])
                if isinstance(check_id, str)
            }
        )
    )
    edges = tuple(
        sorted(
            (module_id, dependency)
            for module_id in enabled
            for dependency in modules[module_id].get("requires", [])
        )
    )
    origins: dict[str, set[str]] = {}
    for path in profile_paths:
        origins.setdefault(path, set()).add("profile")
    for path in capability_paths:
        origins.setdefault(path, set()).add("capability")
    for path in bridges:
        origins.setdefault(path, set()).add("assistant-surface")
    for path in selected_paths:
        origins.setdefault(path, set()).add("resolved")
    source_paths = [
        PROFILE_MANIFEST,
        ROOT / "framework" / "capabilities.json",
        ROOT / "framework" / "framework-packs.json",
        ROOT / "framework" / "rule-registry.json",
        ASSISTANT_SURFACES,
    ]
    return ResolvedComposition(
        contract_version=1,
        support_profile=request.support_profile,
        support_profile_chain=profile_chain,
        framework_pack_request=request.framework_pack_request,
        framework_pack=pack,
        framework_pack_chain=pack_chain,
        requested_capabilities=tuple(sorted(set(request.requested_capabilities))),
        enabled_capabilities=enabled,
        capability_edges=edges,
        requested_assistant_surfaces=tuple(sorted(set(request.requested_assistant_surfaces))),
        assistant_surfaces=surfaces,
        alias_resolutions=aliases,
        profile_template_paths=profile_paths,
        capability_target_paths=capability_paths,
        assistant_bridge_paths=bridges,
        selected_target_paths=tuple(sorted(selected_paths)),
        target_path_origins=tuple(
            PathOrigin(path, tuple(sorted(values)))
            for path, values in sorted(origins.items())
        ),
        framework_paths=framework_paths,
        installed_rule_ids=installed_rule_ids,
        required_check_ids=required_checks,
        source_digests=tuple(
            (
                path.relative_to(ROOT).as_posix(),
                "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
            )
            for path in source_paths
        ),
    )
